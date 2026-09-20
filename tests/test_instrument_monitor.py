from array import array
from copy import deepcopy
import time

import pygame as pg
import pytest

from sidpulse.app import App
from sidpulse.audio.engine import AudioEngine
from sidpulse.audio.monitor import InstrumentMonitor
from sidpulse.export.psid import RecordingSID
from sidpulse.playback.sequencer import Sequencer
from sidpulse.playback.voices import VoicePrograms
from sidpulse.sid.backend_residfp import ReSIDfpBackend, set_filter
from sidpulse.song.model import Cell, Instrument, Pattern, Song


class MonitorSID(RecordingSID):
    def __init__(self):
        super().__init__()
        self.masks = []

    def set_muted(self, mask):
        self.masks.append(mask)


def rig():
    sid = MonitorSID()
    monitor = InstrumentMonitor(sid)
    return sid, monitor, VoicePrograms(sid, monitor=monitor.note_on)


def test_instrument_mute_follows_actual_voice_ownership_and_combines_channel_masks():
    sid, monitor, programs = rig()
    for voice, number in enumerate((24, 2, 24)):
        programs.trigger(voice, 48, Instrument(), number)
    assert not sid.masks  # default monitoring adds no native writes
    monitor.set_instruments({24})
    assert monitor.mask == (True, False, True)
    programs.trigger(0, 52, Instrument(), 2)
    assert monitor.mask == (False, False, True)
    monitor.set_instruments({24}, 24)
    assert monitor.mask == (True, True, False)  # solo temporarily overrides instrument mutes
    monitor.set_voices((False, False, True))
    assert monitor.mask == (True, True, True)
    monitor.set_instruments({24})
    assert monitor.mask == (False, False, True)


def test_delays_memory_portamento_retrigger_and_release_keep_correct_identity():
    sid, monitor, p = rig()
    monitor.set_instruments({24})
    p.trigger(0, 48, Instrument(), 1)
    p.row(0, Cell(instrument=24), Instrument(), 24)
    p.row(0, Cell(60, 24, 'G', 3), Instrument(), 24)
    assert monitor.mask == (False, False, False)
    p.row(0, Cell(48, 24, 'S', 0xD2), Instrument(), 24)
    p.tick(0); p.tick(1)
    assert monitor.instruments[0] == 1
    p.tick(2)
    assert monitor.mask == (True, False, False)
    p.row(0, Cell(effect='Q', parameter=2), Instrument(), 24)
    p.tick(0); p.tick(1); p.tick(2)
    assert monitor.instruments[0] == 24
    p.release(0)
    monitor.set_instruments(set())
    assert monitor.mask == (False, False, False)  # release tail remains controllable


def test_restart_lookahead_never_changes_live_monitor_even_across_loop():
    sid, monitor, _ = rig()
    song = Song(speed=2, tempo=125)
    song.patterns = {0: Pattern(rows=[[Cell(48, 1), Cell(), Cell()]])}
    song.orders = [0]
    calls = []
    def note_on(voice, number):
        calls.append((voice, number))
        monitor.note_on(voice, number)
    seq = Sequencer(sid, monitor=note_on)
    seq.start(song)
    seq._boundary()
    assert calls == [(0, 1)]
    seq.frames = int(seq.next_tick); seq._boundary()
    assert calls == [(0, 1)]
    seq.frames = int(seq.next_tick); seq._boundary()
    assert calls == [(0, 1), (0, 1)] and seq.loops == 1


def test_monitoring_preserves_all_song_register_writes():
    song = Song(speed=3)
    song.instruments[24] = Instrument()
    song.orders = [0]
    song.patterns = {0: Pattern(rows=[
        [Cell(48, 24, 'S', 0xD1), Cell(52, 1), Cell()],
        [Cell(55, 1), Cell(60, 24), Cell()],
        [Cell(effect='Q', parameter=1), Cell(), Cell()]])}
    traces = []
    for enabled in (False, True):
        sid, monitor, _ = rig()
        monitor.set_instruments({24})
        seq = Sequencer(sid, monitor=monitor.note_on if enabled else None)
        seq.start(deepcopy(song), loop=False)
        while seq.status == 'playing':
            seq._boundary(); seq.frames = int(seq.next_tick)
        traces.append(sid.events)
    assert traces[0] == traces[1]


@pytest.mark.parametrize('model', ['6581', '8580'])
def test_native_instrument_mute_unmute_held_note_without_retrigger(model):
    sid = ReSIDfpBackend(model)
    set_filter(sid, Song().filter)
    monitor = InstrumentMonitor(sid)
    p = VoicePrograms(sid, monitor=monitor.note_on)
    p.trigger(2, 48, Instrument(), 24)
    sid.render(4800)
    before = bytes(sid.registers)
    monitor.set_instruments({24})
    sid.render(48000)
    quiet = array('h', sid.render(4800))
    assert max(quiet) - min(quiet) < 50
    monitor.set_instruments(set())
    audible = array('h', sid.render(4800))
    assert max(audible) - min(audible) > 500
    assert bytes(sid.registers) == before and p.voices[2].instrument_id == 24


def wait_for(engine, condition):
    deadline = time.monotonic() + 3
    while not condition() and not engine.error and time.monotonic() < deadline:
        time.sleep(.01)
    assert engine.error is None and condition()


def test_worker_applies_instrument_monitor_to_audition_play_pause_and_reset():
    song = Song()
    song.instruments[24] = Instrument()
    song.patterns[0].rows[0][0] = Cell(48, 24)
    song.patterns[0].rows[0][1] = Cell(52, 1)
    engine = AudioEngine(song)
    try:
        wait_for(engine, lambda: engine.ready)
        engine.send('on', 1, 48, Instrument(), 0, 24)
        wait_for(engine, lambda: 24 in engine.activity.active)
        engine.send('instrument_monitor', (24,), None)
        wait_for(engine, lambda: engine.muted == (True, False, False) and 24 not in engine.activity.active)
        engine.send('on', 2, 52, Instrument(), 1, 24)
        wait_for(engine, lambda: engine.muted == (True, True, False))
        engine.send('on', 3, 60, Instrument(), 0, 1)
        wait_for(engine, lambda: engine.muted == (False, True, False))
        engine.send('play', song, 'pattern', 0, 0, 0)
        wait_for(engine, lambda: engine.playback.status == 'playing' and engine.muted == (True, False, False))
        engine.send('pause')
        wait_for(engine, lambda: engine.playback.status == 'paused')
        engine.send('instrument_monitor', (24,), 24)
        wait_for(engine, lambda: engine.muted == (False, True, True))
        assert engine.playback.status == 'paused'
        engine.send('panic')
        wait_for(engine, lambda: engine.playback.status == 'stopped' and engine.muted == (True, True, True))
        engine.send('instrument_monitor', (), None)
        wait_for(engine, lambda: engine.muted == (False, False, False))
    finally:
        engine.close()


def click(app, action, value):
    app.renderer.render(app)
    rect = next(r for r, a, v in app.renderer.hits if (a, v) == (action, value))
    app.handle(pg.event.Event(pg.MOUSEBUTTONDOWN, button=1, pos=rect.center))
    app.handle(pg.event.Event(pg.MOUSEBUTTONUP, button=1, pos=rect.center))


@pytest.mark.parametrize('size', [(1920, 1080), (960, 540), (480, 360)])
def test_bank_buttons_pressed_active_no_selection_change_and_no_song_edit(size):
    app = App(audio=False, size=size)
    try:
        app.change_page('instrument')
        app.editor.song.instruments[2] = Instrument(name='Second')
        app.editor.song.instruments.pop(3, None)
        app.select_instrument_slot(number=2)
        before = deepcopy(app.editor.song)
        revision = app.editor.history.revision
        app.renderer.render(app)
        rect = next(r for r, a, v in app.renderer.hits if (a, v) == ('instrument_mute', 2))
        assert app.screen.get_rect().contains(rect)
        raised = pg.image.tobytes(app.screen.subsurface(rect), 'RGB')
        app.handle(pg.event.Event(pg.MOUSEBUTTONDOWN, button=1, pos=rect.center))
        assert not app.muted_instruments
        app.renderer.render(app)
        assert pg.image.tobytes(app.screen.subsurface(rect), 'RGB') != raised
        app.handle(pg.event.Event(pg.MOUSEBUTTONUP, button=1, pos=rect.center))
        assert app.muted_instruments == {2}
        click(app, 'instrument_solo', 2)
        assert app.solo_instrument == 2
        click(app, 'instrument_solo', 2)
        assert app.solo_instrument is None and app.muted_instruments == {2}
        assert app.editor.song == before and app.editor.history.revision == revision
        assert app.instrument_slot == 2
        if size[0] == 1920:
            click(app, 'instrument_mute', 1)
            assert app.instrument_slot == 2 and app.muted_instruments == {1, 2}
            click(app, 'bank_monitor_disabled', ('instrument', 3))
            assert 'Empty instrument' in app.editor.status and app.instrument_slot == 2
        app.change_page('samples')
        click(app, 'bank_monitor_disabled', ('sample', 1))
        assert 'assigned instrument M/S' in app.editor.status
        assert app.editor.song == before
    finally:
        app.close()


def test_new_load_and_deleted_slots_clear_instrument_monitors(tmp_path):
    from sidpulse.project.format import save
    app = App(audio=False)
    try:
        app.editor.song.instruments[24] = Instrument()
        app.toggle_instrument_monitor('instrument_mute', 24)
        app.toggle_instrument_monitor('instrument_solo', 24)
        app.editor.edit('Remove slot', [(('instruments',), {1: Instrument()})])
        app.sync_audio()
        assert not app.muted_instruments and app.solo_instrument is None
        app.toggle_instrument_monitor('instrument_mute', 1)
        app.new_project()
        assert not app.muted_instruments
        path = tmp_path / 'monitor.sidpulse'
        save(path, app.editor.song)
        app.toggle_instrument_monitor('instrument_solo', 1)
        app.open_project(path)
        assert not app.muted_instruments and app.solo_instrument is None
    finally:
        app.close()
