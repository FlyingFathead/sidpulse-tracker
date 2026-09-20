from copy import deepcopy
import time

import numpy as np
import pygame as pg
import pytest

from sidpulse.audio.media import make_sample
from sidpulse.audio.synthesize import synthesize_sample
from sidpulse.song.model import Instrument


def tone():
    t = np.arange(1600) / 8000
    values = np.rint(24000 * np.sin(2*np.pi*220*t) * np.exp(-t*12)).astype('<i2')
    return make_sample('A3 decay', values.tobytes(), 8000)


@pytest.fixture(scope='module')
def proposal():
    return synthesize_sample(tone())


def test_fit_follows_pitch_and_remains_a_standalone_sid_instrument(proposal, tmp_path):
    from sidpulse.project.format import load, save, validate
    from test_pcm_media import pcm_song
    from sidpulse.export.psid import compile_song
    sample = tone(); before = deepcopy(sample)
    result = proposal['instrument']
    assert not result.sample_override and result.sample_slot == 0
    assert result.waveform in (16, 32, 64)
    assert abs(result.pitch_sequence[0] - (-3)) <= 2  # 220 Hz relative to C4
    assert proposal['details']['candidates'] < 160 and proposal['details']['score'] < .2
    song = pcm_song(); song.samples = {}; song.instruments = {1: deepcopy(result)}
    for pattern in song.patterns.values():
        for row in pattern.rows:
            for cell in row:
                if cell.instrument: cell.instrument = 1
    validate(song)
    target = tmp_path / 'synth.sidpulse'; save(target, song)
    loaded = load(target)[0]
    assert loaded.instruments[1]._extra_fields == result._extra_fields
    assert loaded.samples == {}
    assert compile_song(loaded).data[:4] == b'PSID'
    assert sample == before


@pytest.mark.parametrize('frames, value, match', [(40, 0, '12 ms'), (200, 0, 'silent'), (16001, 1, '2 seconds')])
def test_invalid_or_unbounded_ranges_fail_without_modifying_source(frames, value, match):
    sample = make_sample('test', np.full(frames, value, '<i2').tobytes(), 8000)
    before = deepcopy(sample)
    with pytest.raises(ValueError, match=match): synthesize_sample(sample)
    assert sample == before


def test_noise_fit_and_selected_range_are_independent_of_unselected_audio():
    rng = np.random.default_rng(17); t = np.arange(1200)/8000
    values = np.rint(rng.uniform(-1,1,len(t))*20000*np.exp(-t*25)).astype('<i2')
    a = make_sample('noise', values.tobytes(), 8000)
    b = make_sample('noise', np.concatenate((np.full(100,30000,'<i2'),values,np.full(100,-30000,'<i2'))).tobytes(),8000)
    b.update(start=100, end=1300); before = deepcopy(b)
    first = synthesize_sample(a); second = synthesize_sample(b)
    assert b == before
    assert first['details']['source_sha256'] == second['details']['source_sha256']
    # Native SID output has dither; scores need not be bit-identical.
    assert first['details']['score'] == pytest.approx(second['details']['score'], abs=.001)
    x,y = deepcopy(first['instrument']),deepcopy(second['instrument'])
    x._extra_fields.clear();y._extra_fields.clear()
    assert x == y
    assert first['instrument'].waveform == 128 and first['details']['kind'] == 'noise'


def test_low_decaying_kick_produces_tonal_candidates_and_valid_tables():
    from sidpulse.audio.synthesize import _pitch_track
    t=np.arange(2400)/12000
    values=np.sin(2*np.pi*(48*t + 25*(1-np.exp(-t*30))/30))*np.exp(-t*15)
    offsets,confidence=_pitch_track(values,.02,48)
    assert (confidence>=.25).any()
    # Impulses can have exclusively negative local autocorrelation peaks.
    impulse=np.zeros(1500);impulse[400]=1
    assert len(_pitch_track(impulse,.02,48)[0]) > 0


def test_waveform_search_can_generate_a_multistep_sid_table():
    from sidpulse.audio.synthesize import render_instrument
    source=Instrument(waveform=16,attack=0,decay=9,sustain=0,release=2,
                      gate_ticks=12,wave_sequence=[128,128,64,64,16],
                      pitch_sequence=[36,30,0,-4,-9,-12])
    pcm=render_instrument(source,48,.3).astype('<i2').tobytes()
    result=synthesize_sample(make_sample('table test',pcm,12000))
    assert len(set(result['instrument'].wave_sequence)) >= 2
    assert len(result['instrument'].wave_sequence)<=64
    assert all(w in (16,32,64,128) for w in result['instrument'].wave_sequence)
    assert result['details']['candidates'] < 200


@pytest.mark.parametrize('size', [(640,480), (960,1080), (1280,900)])
def test_slot_browser_audition_cancel_overwrite_undo_and_save(size, proposal, monkeypatch, tmp_path):
    from sidpulse.app import App
    from sidpulse.ui.sample_synthesis import show_result
    from sidpulse.ui.dialogs import choices, focus
    from sidpulse.project.format import save, load
    from test_pcm_media import pcm_song
    app = App(pcm_song(), audio=False, size=size)
    try:
        app.page='samples'; app.sample_index=1; before=deepcopy(app.editor.song)
        messages=[]; monkeypatch.setattr(app.audio,'send',lambda *args:messages.append(args))
        def show():
            show_result(app,deepcopy(proposal),dict(slot=1,source=app.selected_sample()))
            app.renderer.render(app)
            assert all(app.screen.get_rect().contains(r) for r,a,v in app.renderer.hits)
        def click(action, value):
            r=next(r for r,a,v in app.renderer.hits if a==action and v==value)
            app.handle(pg.event.Event(pg.MOUSEBUTTONDOWN,button=1,pos=r.center))
            app.handle(pg.event.Event(pg.MOUSEBUTTONUP,button=1,pos=r.center))
        show(); empty=app.dialog['selected']; assert empty not in before.instruments
        click('synthesis_action','sample'); assert messages[-1][0]=='sample_on'
        click('synthesis_action','instrument'); assert messages[-1][0]=='on'
        app.handle(pg.event.Event(pg.KEYDOWN,key=pg.K_END,mod=0)); app.renderer.render(app)
        assert app.dialog['selected']==99
        click('synthesis_action','cancel'); assert app.dialog is None and app.editor.song==before
        show(); click('synthesis_slot',1); click('synthesis_action','use')
        assert app.dialog['title']=='Replace instrument?'
        assert [v[0] for v in choices(app.dialog)]==['OK','Cancel'] and focus(app.dialog)==1
        app.handle(pg.event.Event(pg.KEYDOWN,key=pg.K_RETURN,mod=0))
        assert app.dialog['kind']=='sample_synthesis' and app.editor.song==before
        app.renderer.render(app); click('synthesis_action','use')
        app.handle(pg.event.Event(pg.KEYDOWN,key=pg.K_y,mod=0))
        assert app.dialog is None and app.page=='instrument' and app.editor.instrument==1
        assert app.editor.song.samples==before.samples
        target=tmp_path/'slot.sidpulse';save(target,app.editor.song)
        assert load(target)[0].instruments[1]._extra_fields['sample_synthesis']['sample_slot']==1
        app.editor.history.undo(app.editor.song); assert app.editor.song==before
        show(); click('synthesis_action','use')
        assert app.editor.instrument==empty and not app.editor.song.instruments[empty].sample_override
        app.editor.history.undo(app.editor.song); assert app.editor.song==before
    finally: app.close()


def test_background_worker_returns_proposal_without_applying_and_can_cancel():
    from sidpulse.export.analysis_job import AnalysisJob
    from sidpulse.export.audio import media_worker
    source=tone(); before=deepcopy(source)
    options=dict(operation='synthesize',model='8580',clock='PAL',tempo=125)
    job=AnalysisJob(source,options,'sid',worker=media_worker)
    try:
        job.start(); deadline=time.monotonic()+20
        while not job.poll().done and time.monotonic()<deadline:time.sleep(.02)
        result=job.poll()
        assert result.done and not result.error and result.result['instrument'].sample_slot==0
        assert source==before
    finally: assert job.close()
    job=AnalysisJob(source,options,'sid',worker=media_worker)
    job.start(); job.cancel()
    assert job.close() and job.poll().cancelled and job.poll().result is None


@pytest.mark.parametrize('size', [(640,480),(960,1080),(1280,900)])
def test_instrument_freeze_blocks_edits_unfreezes_and_keeps_provenance(size, proposal, tmp_path):
    from sidpulse.app import App
    from sidpulse.project.format import save,load
    from test_pcm_media import pcm_song
    song=pcm_song();song.instruments[1]=deepcopy(proposal['instrument'])
    song.instruments[1]._extra_fields['sample_synthesis']['sample_slot']=1
    app=App(song,audio=False,size=size)
    try:
        app.change_page('instrument');app.editor.instrument=app.instrument_slot=1
        original=deepcopy(app.editor.song.instruments[1]);source=deepcopy(app.synthesis_info())
        app.renderer.render(app)
        assert all(app.screen.get_rect().contains(r) for r,a,v in app.renderer.hits if a=='instrument_freeze')
        assert not any(a in ('graph_drag','toggle_program','waveform','pcm_setting') for r,a,v in app.renderer.hits)
        app.property_index=2;app.change_property(direct='F')
        app.toggle_instrument_program('pitch_sequence')
        app.graph_edit_sequence([12],'test frozen graph')
        app.pcm_instrument_setting('sample_override')
        assert app.editor.song.instruments[1]==original
        app.toggle_instrument_freeze();assert not app.instrument_frozen()
        app.change_property(direct='F');assert app.editor.song.instruments[1].attack==15
        assert app.synthesis_info()==source
        app.renderer.render(app)
        app.toggle_instrument_freeze();assert app.instrument_frozen()
        target=tmp_path/'frozen.sidpulse';save(target,app.editor.song)
        loaded=load(target)[0];assert loaded.instruments[1]._extra_fields['editor_frozen'] is True
        assert loaded.instruments[1]._extra_fields['sample_synthesis']==source
        for _ in range(3):app.editor.history.undo(app.editor.song)
        assert app.editor.song.instruments[1]==original
        # The same protection is available to ordinary, non-synthesized presets.
        app.editor.song.instruments[1]=Instrument('ordinary')
        app.toggle_instrument_freeze();assert app.instrument_frozen()
        app.toggle_instrument_freeze();assert not app.instrument_frozen()
        app.toggle_instrument_freeze();app.select_instrument_slot(number=99)
        assert ('instrument_freeze',None) not in app.instrument_buttons()
        app.toggle_instrument_freeze();assert app.instrument_frozen(1)
    finally:app.close()
