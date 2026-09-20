from copy import deepcopy
from fractions import Fraction
import json
import shutil
import struct
import wave

import numpy as np
import pygame as pg
import pytest

from sidpulse.audio.media import make_sample, import_sample, sample_data, sample_bounds, squeeze_sample
from sidpulse.audio.samples import SamplePrograms
from sidpulse.export.audio import duration_frames, save_audio
from sidpulse.export.psid import RecordingSID
from sidpulse.project.format import encode, decode, load, save
from sidpulse.song.model import Song, Instrument, Pattern, Cell, CUT


class SilentSID(RecordingSID):
    muted = (False, False, False)
    def render(self, frames):
        return bytes(frames*2)


def pcm_song(rate=48000):
    song = Song(speed=2, tempo=127)
    pcm = (np.sin(np.arange(1200)*.08)*20000).astype('<i2').tobytes()
    song.samples = {'1': make_sample('Algorithmic test', pcm, rate)}
    song.instruments[1] = Instrument(sample_override=True, sample_slot=1, sample_gain=100)
    song.patterns = {0: Pattern(rows=[[Cell(), Cell(), Cell(48, 1)], [Cell(), Cell(), Cell(CUT)]])}
    song.orders = [0]
    return song


def test_pcm_wav_import_downmix_and_roundtrip_preserve_source(tmp_path):
    path = tmp_path/'stereo.wav'
    values = np.array([[100, 300], [-1000, 2000], [-32768, 32766]], dtype='<i2')
    with wave.open(str(path), 'wb') as output:
        output.setparams((2, 2, 22050, len(values), 'NONE', 'none'))
        output.writeframes(values.tobytes())
    original = path.read_bytes()
    sample = import_sample(path)
    assert np.frombuffer(sample_data(sample), '<i2').tolist() == [200, 500, -1]
    assert sample['sample_rate'] == 22050 and path.read_bytes() == original
    song = pcm_song(); song.samples['1'] = sample
    assert encode(song)['format_version'] == 8
    target = save(tmp_path/'pcm.sidpulse', song)
    assert load(target)[0] == song
    assert decode(encode(song))[0] == song


@pytest.mark.parametrize('start,end', [(-1, 3), (0, 1201), (9, 9), (10, 1)])
def test_invalid_trim_rejected(start, end):
    sample = pcm_song().samples['1'];sample.update(start=start,end=end)
    with pytest.raises(ValueError, match='range'):
        sample_data(sample)


@pytest.mark.parametrize('bits', [4, 8, 16])
def test_squeeze_bakes_selected_range_and_retains_one_original(bits):
    sample = pcm_song().samples['1'];sample.update(start=10,end=1011)
    original = deepcopy(sample)
    squeezed = squeeze_sample(sample, 48000, bits)
    assert squeezed['frames'] == 1001
    assert sample_bounds(squeezed) == (0, 1001)
    assert squeezed['original'] == original and sample == original
    a = np.frombuffer(sample_data(sample), '<i2')[10:1011].astype(int)
    b = np.frombuffer(sample_data(squeezed), '<i2').astype(int)
    assert max(abs(a-b)) <= {4:2048,8:255,16:0}[bits]
    again = squeeze_sample(squeezed, 48000, bits)
    assert again['original'] == original and 'original' not in again['original']


def test_pcm_trigger_pitch_trim_mutes_gain_and_cut():
    song = pcm_song();sample = song.samples['1'];sample.update(start=100,end=900)
    sid = SilentSID();sid.registers[24] = 15
    programs = SamplePrograms(sid, samples=song.samples)
    programs.trigger(2,48,song.instruments[1],1)
    raw = np.frombuffer(programs.render(100),np.int16)
    assert np.array_equal(raw, np.frombuffer(sample_data(sample),'<i2')[100:200])
    assert sid.registers[18] & 0xf0 == 0
    programs.trigger(2,60,song.instruments[1],1)
    assert programs.pcm[2]['step'] == pytest.approx(2.,abs=.001)
    programs.render(401)
    assert programs.pcm[2] is None
    programs.trigger(2,48,song.instruments[1],1)
    sid.muted=(False,False,True)
    assert programs.render(40)==bytes(80)
    sid.muted=(False,False,False)
    programs.release(2,cut=True)
    assert programs.render(40)==bytes(80)


def test_missing_sample_override_is_silent():
    sid=SilentSID();sid.registers[24]=15
    programs=SamplePrograms(sid,samples={})
    programs.trigger(0,48,Instrument(sample_override=True,sample_slot=7),1)
    assert programs.render(100)==bytes(200)


def test_sample_keyboard_preview_and_editor_shortcut():
    from sidpulse.ui.keyboard import dispatch
    note=dispatch(pg.event.Event(pg.KEYDOWN,key=pg.K_z,scancode=29,mod=0),'samples')
    assert note.name=='piano' and note.value==(29,0,True)
    editor=dispatch(pg.event.Event(pg.KEYDOWN,key=pg.K_F3,scancode=60,mod=pg.KMOD_CTRL),'pattern')
    assert (editor.name,editor.value)==('page','samples')


@pytest.mark.parametrize('auto_squeeze', [None, False])
def test_background_sample_import_returns_a_complete_snapshot(tmp_path, auto_squeeze):
    from sidpulse.export.analysis_job import AnalysisJob
    from sidpulse.export.audio import media_worker
    import time
    path=tmp_path/'input.wav'
    with wave.open(str(path),'wb') as output:
        output.setparams((1,2,48000,1200,'NONE','none'))
        output.writeframes(sample_data(pcm_song().samples['1']))
    options={'operation':'import'}
    if auto_squeeze is not None:
        options['auto_squeeze']=auto_squeeze
    job=AnalysisJob(str(path),options,'sid',worker=media_worker)
    try:
        job.start();deadline=time.monotonic()+8
        while not job.poll().done and time.monotonic()<deadline:time.sleep(.01)
        update=job.poll()
        assert update.done and not update.error and not update.cancelled
        assert update.source==str(path)
        if auto_squeeze is False:
            assert update.result['frames']==1200 and 'original' not in update.result
        else:
            assert update.result['frames']==100 and update.result['sample_rate']==4000
            assert update.result['encoding']=='pcm_u4le_mono'
            assert sample_data(update.result['original'])==sample_data(pcm_song().samples['1'])
    finally:assert job.close()


@pytest.mark.parametrize('loops',[0,1,3])
def test_audio_export_exact_fractional_duration_and_loops(tmp_path,loops):
    song=pcm_song();before=deepcopy(song)
    frames=Fraction(48000*5*4,127*2)
    assert duration_frames(song)==frames
    target=tmp_path/'test.wav'
    result=save_audio(song,target,loops=loops)
    with wave.open(str(target),'rb') as wav:
        assert wav.getnframes()==int(frames*(loops+1))==result['frames']
        assert (wav.getnchannels(),wav.getframerate(),wav.getsampwidth())==(1,48000,2)
        raw=np.frombuffer(wav.readframes(wav.getnframes()),'<i2').astype(int)
    assert np.ptp(raw)>1000 and song==before
    # Every requested pass contains a fresh kick; no trailing silence-only pass.
    for n in range(loops+1):
        start=int(frames*n)
        assert np.ptp(raw[start:start+800])>1000


def test_audio_failure_preserves_existing_destination(tmp_path,monkeypatch):
    path=tmp_path/'test.mp3';path.write_bytes(b'existing audio')
    def missing(*args,**kw): raise ValueError('FFmpeg unavailable')
    monkeypatch.setattr('sidpulse.export.audio.ffmpeg_path',missing)
    with pytest.raises(ValueError,match='FFmpeg'):
        save_audio(pcm_song(),path)
    assert path.read_bytes()==b'existing audio'
    assert list(tmp_path.iterdir())==[path]


@pytest.mark.skipif(not shutil.which('ffmpeg'),reason='optional FFmpeg encoder')
def test_mp3_is_decodable_and_backup_is_atomic(tmp_path):
    import subprocess
    path=tmp_path/'test.mp3';path.write_bytes(b'old')
    result=save_audio(pcm_song(),path,loops=1)
    assert path.with_suffix('.mp3.bak').read_bytes()==b'old'
    raw=subprocess.run(['ffmpeg','-v','error','-i',str(path),'-f','s16le','-'],capture_output=True,check=True).stdout
    assert len(raw)==result['frames']*2
    assert np.ptp(np.frombuffer(raw,'<i2').astype(int))>1000


def test_backward_jump_requires_finite_order_traversal():
    song=pcm_song();song.patterns[0].rows[1][0]=Cell(effect='B',parameter=0)
    with pytest.raises(ValueError,match='revisits'):
        duration_frames(song)


@pytest.mark.parametrize('size',[(640,480),(960,1080),(1280,900)])
def test_sample_markers_mouse_numeric_undo_and_save(tmp_path,size):
    from sidpulse.app import App
    app=App(pcm_song(),audio=False,size=size)
    try:
        app.change_page('samples');app.sample_index=1
        app.renderer.render(app)
        toggle=next(r for r,a,v in app.renderer.hits if a=='sample_auto_squeeze')
        assert app.screen.get_rect().contains(toggle) and app.sample_auto_squeeze
        assert not any(toggle.colliderect(r) for r,a,v in app.renderer.hits if a!='sample_auto_squeeze')
        app.handle(pg.event.Event(pg.MOUSEBUTTONDOWN,button=1,pos=toggle.center))
        from sidpulse.preferences import load_sample_auto_squeeze
        assert not app.sample_auto_squeeze and not load_sample_auto_squeeze()
        hit,data=next((r,v) for r,a,v in app.renderer.hits if a=='sample_marker' and v['field']=='start')
        assert app.screen.get_rect().contains(hit)
        before=deepcopy(app.editor.song)
        app.handle(pg.event.Event(pg.MOUSEBUTTONDOWN,button=1,pos=hit.center))
        end=(hit.centerx+20,hit.centery)
        app.handle(pg.event.Event(pg.MOUSEMOTION,pos=end,rel=(20,0),buttons=(1,0,0)))
        assert app.editor.song==before  # only a draft while dragging
        app.handle(pg.event.Event(pg.MOUSEBUTTONUP,button=1,pos=end))
        assert app.selected_sample()['start']>0
        app.editor.history.undo(app.editor.song)
        assert app.editor.song==before
        app.set_sample_range(1,'end',1100)
        assert app.selected_sample()['end']==1100
        path=save(tmp_path/'edited.sidpulse',app.editor.song)
        assert load(path)[0]==app.editor.song
    finally:
        app.close()


def test_auto_squeezed_import_assignment_restore_undo_and_embedded_save(tmp_path):
    from sidpulse.app import App
    app=App(pcm_song(),audio=False)
    try:
        before=deepcopy(app.editor.song)
        squeezed=squeeze_sample(before.samples['1'])
        app.accept_sample(squeezed, {'slot':2,'instrument':1})
        assert app.editor.song.instruments[1].sample_slot==2
        assert load(save(tmp_path/'squeezed.sidpulse',app.editor.song))[0]==app.editor.song
        app.restore_sample()
        assert app.selected_sample()==before.samples['1']
        app.editor.history.undo(app.editor.song)
        assert app.selected_sample()==squeezed
        app.editor.history.undo(app.editor.song)
        assert app.editor.song==before
        captured=[]
        app._start_media_job=lambda source, options, **kw:captured.append((options,kw))
        app.sample_index=3
        app.start_sample_import(tmp_path/'source.wav')
        assert captured[-1][0]['auto_squeeze'] is True
        app.toggle_sample_auto_squeeze()
        app.start_sample_import(tmp_path/'source.wav')
        assert captured[-1][0]['auto_squeeze'] is False
    finally:app.close()


def test_orphan_audio_job_is_cancelled_without_publishing(tmp_path):
    from sidpulse.app import App
    from sidpulse.export.analysis_job import AnalysisUpdate
    class Job:
        cancelled=False
        def poll(self):return AnalysisUpdate(done=True,result={'path':'should never be used'})
        def cancel(self):self.cancelled=True
    app=App(audio=False)
    try:
        job=Job()
        app.media_jobs=[dict(job=job,folder=None,target=tmp_path/'out.wav',assignment=None,cancelled=False)]
        app.dialog={'title':'Quit?'}
        app.poll_media_jobs()
        assert job.cancelled and not app.media_jobs
        assert app.dialog['title']=='Quit?' and not list(tmp_path.glob('*.wav'))
    finally:app.close()
