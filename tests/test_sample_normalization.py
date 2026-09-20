from copy import deepcopy

import numpy as np
import pygame as pg
import pytest

from sidpulse.audio.media import make_sample, normalize_sample, sample_data, squeeze_sample


@pytest.mark.parametrize('bits', [4, 8, 16])
def test_normalize_preserves_storage_trim_outside_audio_and_restore(bits):
    source = make_sample('quiet', np.array([1000, -1000, 6000, -6000, 3000, -3000, 1000], '<i2').tobytes(), 4000)
    sample = squeeze_sample(source, 4000, bits)
    sample.update(start=2, end=6)
    before = deepcopy(sample)
    result = normalize_sample(sample)
    old = np.frombuffer(sample_data(sample), '<i2')
    new = np.frombuffer(sample_data(result), '<i2')
    assert sample == before
    assert result['encoding'] == sample['encoding']
    assert (result['start'], result['end'], result['frames'], result['sample_rate']) == (2, 6, 7, 4000)
    assert np.array_equal(old[:2], new[:2]) and old[-1] == new[-1]
    assert max(abs(new[2:6].astype(int))) >= 30000
    assert result['original'] == source
    assert normalize_sample(result)['original'] == source


@pytest.mark.parametrize('bits', [4, 8, 16])
def test_constant_samples_are_never_amplified(bits):
    sample = squeeze_sample(make_sample('silence', bytes(128), 4000), 4000, bits)
    assert normalize_sample(sample)['data'] == sample['data']


def test_normalization_before_quantization_retains_quiet_waveform_detail():
    values = np.rint(np.sin(np.arange(400) * 2 * np.pi / 40) * 1000).astype('<i2')
    sample = make_sample('quiet sine', values.tobytes(), 4000)
    old = squeeze_sample(sample, 4000, 4)
    new = squeeze_sample(sample, 4000, 4, normalize_before=True)
    assert len(np.unique(np.frombuffer(sample_data(old), '<i2'))) == 2
    assert len(np.unique(np.frombuffer(sample_data(new), '<i2'))) >= 14
    assert old == squeeze_sample(sample, 4000, 4, normalize_before=False, normalize_after=False)
    assert new['original'] == sample


def test_after_normalization_restores_peak_lost_in_resampling():
    import shutil
    if not shutil.which('ffmpeg'): pytest.skip('needs resampling')
    t = np.arange(4800) / 48000
    values = np.rint(16000 * np.sin(t*2*np.pi*6000) + 1500*np.sin(t*2*np.pi*200)).astype('<i2')
    sample = make_sample('filtered peak', values.tobytes())
    first = squeeze_sample(sample, 4000, 4, normalize_before=True)
    both = squeeze_sample(sample, 4000, 4, normalize_before=True, normalize_after=True)
    assert max(abs(np.frombuffer(sample_data(first), '<i2').astype(int))) < 12000
    assert max(abs(np.frombuffer(sample_data(both), '<i2').astype(int))) >= 30000
    assert both['encoding'] == 'pcm_u4le_mono' and both['original'] == sample


@pytest.mark.parametrize('size', [(640,480),(960,1080),(1280,900)])
def test_normalize_controls_confirmation_and_import_snapshot(size, monkeypatch):
    from sidpulse.app import App
    from sidpulse.preferences import load_sample_normalization
    from test_pcm_media import pcm_song
    from sidpulse.ui.dialogs import choices, focus
    app = App(pcm_song(), audio=False, size=size)
    try:
        app.page='samples';app.sample_index=1
        before=deepcopy(app.editor.song)
        app.renderer.render(app)
        flags=[(r,v) for r,a,v in app.renderer.hits if a=='sample_normalization']
        assert len(flags)==2 and all(app.screen.get_rect().contains(r) for r,v in flags)
        assert not flags[0][0].colliderect(flags[1][0])
        assert app.sample_normalize_before and not app.sample_normalize_after
        app.toggle_sample_normalization('after')
        assert load_sample_normalization()==(True,True)
        app.normalize_sample();app.renderer.render(app)
        assert app.dialog['title']=='Normalize audio?'
        assert [x[0] for x in choices(app.dialog)]==['OK','Cancel'] and focus(app.dialog)==1
        app.handle(pg.event.Event(pg.KEYDOWN,key=pg.K_RETURN,mod=0))
        assert app.dialog is None and app.editor.song==before
        jobs=[]
        monkeypatch.setattr(app,'_start_media_job',lambda source,options,**kw:jobs.append((source,options,kw)))
        app.normalize_sample();app.handle(pg.event.Event(pg.KEYDOWN,key=pg.K_y,mod=0))
        assert jobs[-1][1]=={'operation':'normalize'}
        source,_,kw=jobs[-1]
        app.accept_sample(normalize_sample(source),kw['assignment'])
        assert app.editor.song.samples['1']['original']==source
        app.editor.history.undo(app.editor.song);assert app.editor.song==before
        app.open_sample_squeeze();app.renderer.render(app)
        assert all(app.screen.get_rect().contains(r) for r,a,v in app.renderer.hits)
        app.dialog['focus']=2
        app.handle(pg.event.Event(pg.KEYDOWN,key=pg.K_SPACE,mod=0))
        assert not app.dialog['normalize_before']
        app.apply_sample_squeeze()
        assert jobs[-1][1]['normalize_before'] is False and jobs[-1][1]['normalize_after'] is True
    finally:app.close()


@pytest.mark.parametrize('bits', [4, 8, 16])
def test_adjust_volume_preserves_markers_original_and_saturates(bits):
    from sidpulse.audio.media import adjust_sample_volume
    source = make_sample('volume', np.array([1000, 24000, -24000, 6000, -6000, 7000, 2000], '<i2').tobytes(), 4000)
    sample = squeeze_sample(source, 4000, bits)
    sample.update(start=1, end=5)
    before = deepcopy(sample)
    assert adjust_sample_volume(sample, 100) == sample
    louder = adjust_sample_volume(sample, 200)
    a = np.frombuffer(sample_data(sample), '<i2').astype(int)
    b = np.frombuffer(sample_data(louder), '<i2').astype(int)
    assert np.array_equal(a[[0, 5, 6]], b[[0, 5, 6]])
    assert b[1] >= 30000 and b[2] <= -30000  # clip without wraparound
    assert b[3] > a[3] and b[4] < a[4]
    assert louder['original'] == source and sample == before
    for field in ('start','end','root_note','frames','sample_rate','encoding'):
        assert louder[field] == sample[field]
    muted = np.frombuffer(sample_data(adjust_sample_volume(sample, 0)), '<i2')
    assert len(set(muted[1:5])) == 1
    with pytest.raises(ValueError): adjust_sample_volume(sample, 201)
    with pytest.raises(ValueError): adjust_sample_volume(sample, -1)


@pytest.mark.parametrize('size', [(640,480),(960,1080),(1280,900)])
def test_volume_dialog_mouse_numeric_cancel_apply_undo_save(size, monkeypatch, tmp_path):
    from sidpulse.app import App
    from sidpulse.audio.media import adjust_sample_volume
    from sidpulse.project.format import save, load
    from test_pcm_media import pcm_song
    app = App(pcm_song(), audio=False, size=size)
    try:
        app.page='samples';app.sample_index=1
        before=deepcopy(app.editor.song)
        app.renderer.render(app)
        assert all(app.screen.get_rect().contains(r) for r,a,v in app.renderer.hits
                   if a in ('sample_volume','sample_normalization','sample_range','sample_root'))
        assert all(r.bottom <= (app.renderer.lines-app.renderer.footer_rows)*app.renderer.rh
                   for r,a,v in app.renderer.hits if a in ('sample_volume','sample_normalization','sample_range','sample_root'))
        app.media_action('sample_volume');app.renderer.render(app)
        assert app.dialog['value']==100
        app.handle(pg.event.Event(pg.KEYDOWN,key=pg.K_RETURN,mod=0))
        assert app.dialog is None and app.editor.song==before
        app.media_action('sample_volume');app.renderer.render(app)
        track=next(r for r,a,v in app.renderer.hits if a=='volume_slider')
        app.handle(pg.event.Event(pg.MOUSEBUTTONDOWN,button=1,pos=(track.right-1,track.centery)))
        app.handle(pg.event.Event(pg.MOUSEBUTTONUP,button=1,pos=(track.right-1,track.centery)))
        assert app.dialog['value']==200
        app.handle(pg.event.Event(pg.KEYDOWN,key=pg.K_ESCAPE,mod=0))
        assert app.editor.song==before
        app.media_action('sample_volume');app.renderer.render(app)
        field=next(r for r,a,v in app.renderer.hits if a=='volume_value')
        app.handle(pg.event.Event(pg.MOUSEBUTTONDOWN,button=1,pos=field.center))
        app.handle(pg.event.Event(pg.TEXTINPUT,text='201'))
        app.handle(pg.event.Event(pg.KEYDOWN,key=pg.K_RETURN,mod=0))
        assert app.dialog['error'] and app.editor.song==before
        app.handle(pg.event.Event(pg.KEYDOWN,key=pg.K_a,mod=pg.KMOD_CTRL))
        app.handle(pg.event.Event(pg.TEXTINPUT,text='175'))
        jobs=[]
        monkeypatch.setattr(app,'_start_media_job',lambda source,options,**kw:jobs.append((source,options,kw)))
        app.handle(pg.event.Event(pg.KEYDOWN,key=pg.K_RETURN,mod=0))
        source,options,kw=jobs[-1]
        assert options=={'operation':'volume','percent':175}
        app.accept_sample(adjust_sample_volume(source,175),kw['assignment'])
        target=tmp_path/'volume.sidpulse';save(target,app.editor.song)
        assert load(target)[0].samples==app.editor.song.samples
        app.editor.history.undo(app.editor.song)
        assert app.editor.song==before
        app.media_action('sample_volume');assert app.dialog['value']==100
    finally:app.close()
