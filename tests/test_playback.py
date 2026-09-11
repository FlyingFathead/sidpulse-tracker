from array import array
from copy import deepcopy
from fractions import Fraction
import time
import pygame as pg
import pytest

from sidpulse.app import App
from sidpulse.audio.engine import AudioEngine
from sidpulse.audio.output import OutputConditioner
from sidpulse.playback.sequencer import Sequencer
from sidpulse.project.format import encode, decode
from sidpulse.song.model import Song, Pattern, Cell, OFF, CUT, example_song
from sidpulse.sid.backend_residfp import ReSIDfpBackend, set_filter


class TraceSID:
    sample_rate = 48000
    def __init__(self):
        self.registers = bytearray(25)
        self.frames = 0
        self.events = []
    def write(self, register, value):
        self.registers[register] = value
        self.events.append((self.frames, register, value))
    def clock(self, cycles):
        pass  # native gate gap is covered by backend tests
    def render(self, frames):
        self.frames += frames
        return bytes(frames * 2)


def wait_until(test, timeout=2):
    limit = time.monotonic() + timeout
    while not test() and time.monotonic() < limit:
        time.sleep(.005)
    assert test()


def test_first_light_exact_duration_and_all_voice_note_events():
    sid = TraceSID()
    seq = Sequencer(sid)
    seq.start(example_song(),loop=False)
    seq.render(2211840)  # 12 orders * 32 rows * 6 ticks * 960 frames
    assert seq.state.status == 'stopped'
    assert seq.frames == 2211840
    for register in (4, 11, 18):
        assert any(r == register and v & 1 for _, r, v in sid.events)
    onsets = [frame for frame, reg, value in sid.events if reg == 4 and value & 1]
    assert onsets[0] == 0 and onsets[-1] >= 42*48000
    assert len(set(onsets)) > 80


def test_tick_trace_does_not_depend_on_audio_buffer_partition():
    song = example_song(); song.tempo = 137
    traces=[]
    for chunks in ([100000], [1, 511, 4096, 95000, 392]):
        sid=TraceSID();seq=Sequencer(sid);seq.start(song)
        for frames in chunks:seq.render(frames)
        traces.append((sid.events, seq.state))
    assert traces[0] == traces[1]
    assert any(f == int(Fraction(24 * 120000, 137)) and r == 4 and v & 1 for f,r,v in traces[0][0])


def test_order_transition_instrument_memory_off_cut_and_stop():
    song=Song(speed=1)
    song.patterns={0:Pattern(rows=[[Cell(48,2),Cell(),Cell()], [Cell(50),Cell(),Cell()]]),
                   1:Pattern(rows=[[Cell(OFF),Cell(),Cell()], [Cell(CUT),Cell(),Cell()]])}
    song.orders=[0,1]
    sid=TraceSID();seq=Sequencer(sid);seq.start(song,loop=False)
    seq.render(960)
    assert seq.row==1 and seq.instruments[0]==2
    assert sid.registers[4] & 0xF0 == 0x20
    seq.render(960)
    assert seq.order==1 and seq.row==0 and sid.registers[4] & 1 == 0
    seq.render(960)
    assert sid.registers[4] == 0
    seq.render(960)
    assert seq.status=='stopped'


def test_loop_pause_and_live_update_at_next_row():
    song=Song(speed=1);song.patterns[0].rows=[[Cell(48,1),Cell(),Cell()],[Cell(50,1),Cell(),Cell()]]
    sid=TraceSID();seq=Sequencer(sid);seq.start(song,'pattern')
    seq.render(400);seq.pause();before=(seq.state,sid.frames)
    assert seq.render(400)==bytes(800)
    assert (seq.state,sid.frames)==before
    seq.pause()
    edited=deepcopy(song);edited.patterns[0].rows[1][0].note=60
    seq.update_song(edited);seq.render(560)
    assert seq.row==1 and seq.notes[0]==60
    seq.render(960)
    assert seq.row==0 and seq.loops==1 and seq.status=='playing'


def test_supported_effects_and_unsupported_effect_warning():
    song=Song(speed=6)
    song.patterns={0:Pattern(rows=[[Cell(effect='A',parameter=1),Cell(effect='T',parameter=150),Cell()]]),
                   1:Pattern(rows=[[Cell(effect='B',parameter=2),Cell(effect='C',parameter=1),Cell()]]),
                   2:Pattern(rows=[[Cell(),Cell(),Cell()], [Cell(effect='P',parameter=0x24),Cell(),Cell()]])}
    song.orders=[0,1,2]
    seq=Sequencer(TraceSID());seq.start(song,loop=False)
    seq.render(800)
    assert seq.speed==1 and seq.tempo==150 and seq.order==1
    seq.render(800)
    assert seq.order==2 and seq.row==1
    assert 'P24' in seq.warning
    seq.render(800)
    assert seq.status=='stopped'


@pytest.mark.parametrize('model',['6581','8580'])
def test_native_first_light_has_sustained_audio_across_the_whole_song(model):
    song=example_song();song.sid_model=model
    sid=ReSIDfpBackend(model);set_filter(sid,song.filter);sid.render(48000)
    seq=Sequencer(sid);seq.start(song)
    conditioner=OutputConditioner();conditioner.target=1
    # Check every musical second, not only a startup click.
    for _ in range(7):
        samples=array('h',conditioner.process(seq.render(48000)))
        assert max(samples)-min(samples)>2000
        assert sum(x*x for x in samples)/len(samples)>100000
    assert seq.status=='playing' and seq.order==1 and seq.row>20


def test_idle_startup_is_silent_and_buffer_can_reopen_during_playback():
    engine=AudioEngine(example_song(),buffer_frames=512)
    try:
        wait_until(lambda: engine.ready or engine.error)
        assert not engine.error
        time.sleep(.04)
        assert engine.rms == 0
        engine.send('play', example_song(),'song',0,0,None)
        wait_until(lambda: engine.playback.frames > 5000)
        assert engine.peak>.01
        engine.send('buffer',2048)
        wait_until(lambda: engine.buffer_frames==2048)
        before=engine.playback.frames
        wait_until(lambda: engine.playback.frames > before+2048)
        assert engine.playback.status=='playing' and not engine.error
        engine.send('pause')
        wait_until(lambda: engine.playback.status=='paused')
        before=engine.playback.frames;time.sleep(.05)
        assert engine.playback.frames==before
        engine.send('pause')
        wait_until(lambda: engine.playback.frames>before)
        engine.send('panic')
        wait_until(lambda: engine.playback.status=='stopped' and not engine.active)
    finally:engine.close()


def test_f5_f6_f7_mark_and_nonblocking_pages_through_real_app():
    app=App(example_song(),audio=True)
    def press(key, mod=0):
        app.handle(pg.event.Event(pg.KEYDOWN,key=key,scancode=0,mod=mod,unicode=''))
    try:
        wait_until(lambda: app.audio.ready or app.audio.error)
        press(pg.K_F5)
        wait_until(lambda: app.audio.playback.status=='playing')
        assert app.page=='info'
        before=app.audio.playback.frames
        press(pg.K_F2);press(pg.K_F1)
        app.handle(pg.event.Event(pg.VIDEORESIZE,w=900,h=700))
        app.handle(pg.event.Event(pg.WINDOWFOCUSLOST))
        wait_until(lambda: app.audio.playback.frames>before+4096)
        assert app.page=='help' and app.audio.playback.status=='playing'
        press(pg.K_F8);wait_until(lambda: app.audio.playback.status=='stopped')
        press(pg.K_F2);app.editor.row=16;press(pg.K_F7,pg.KMOD_CTRL)
        app.editor.row=0;press(pg.K_F7)
        wait_until(lambda: app.audio.playback.row>=16 and app.audio.playback.status=='playing')
        assert app.playback_mark==(0,16)
        press(pg.K_F6);wait_until(lambda: app.audio.playback.mode=='pattern')
        assert app.audio.playback.row<16
    finally:app.close()


def test_v1_project_loads_and_new_tempo_roundtrips():
    raw=encode(example_song());raw['format_version']=1;raw['song'].pop('tempo')
    song,_=decode(raw)
    assert song.tempo==125
    song.tempo=143
    assert encode(song)['format_version']==6
    restored,_=decode(encode(song))
    assert restored==song


def test_buffer_preference_is_machine_state_not_song(tmp_path):
    app=App(audio=False)
    try:
        before=deepcopy(app.editor.song)
        app.change_page('settings');app.property_index=13
        app.change_property(direct='4096')
        assert app.audio_buffer==4096 and app.editor.song==before
        from sidpulse.preferences import load_preferences
        assert load_preferences()==4096
    finally:app.close()
