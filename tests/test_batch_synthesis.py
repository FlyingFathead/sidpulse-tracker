from copy import deepcopy
import time

import numpy as np
import pygame as pg
import pytest

from sidpulse.app import App
from sidpulse.audio.media import make_sample
from sidpulse.audio.synthesis_batch import synthesize_mapped_samples
from sidpulse.export.squeeze import SqueezeOptions
from sidpulse.song.model import Song, Instrument, Pattern, Cell
from sidpulse.ui import batch_synthesis, export_squeezer
from sidpulse.ui.dialogs import choices, focus


def source_song():
    song = Song()
    t = np.arange(600)/4000
    tone = np.rint(22000*np.sin(2*np.pi*150*t)*np.exp(-t*20)).astype('<i2')
    noise = np.rint(np.random.default_rng(4).uniform(-1,1,len(t))*20000*np.exp(-t*30)).astype('<i2')
    song.samples = {'1':make_sample('Kick reference',tone.tobytes(),4000),
                    '2':make_sample('Snare reference',noise.tobytes(),4000)}
    song.instruments = {1:Instrument(name='Kick',sample_override=True,sample_slot=1),
                        2:Instrument(name='Snare',sample_override=True,sample_slot=2),
                        3:Instrument(name='Second kick',sample_override=True,sample_slot=1),
                        4:Instrument(name='Unchanged SID')}
    song.patterns = {0:Pattern(rows=[[Cell(48,4),Cell(),Cell(48,1)],
                                   [Cell(),Cell(),Cell(48,2)]])}
    song.orders = [0]
    return song


@pytest.fixture(scope='module')
def fitted():
    source = source_song(); before = deepcopy(source)
    result = synthesize_mapped_samples(source)
    assert source == before and result['fitted_samples'] == 2
    assert [p['number'] for p in result['proposals']] == [1,2,3]
    return result


def export_menu(app, result=None):
    app.dialog = dict(kind='export_squeezer',title='Export PRG',target='prg',pcm=True,
                      result=result,source=deepcopy(app.editor.song),busy=False,
                      options=SqueezeOptions(),compare=False,focus=7,scroll=0)
    return app.dialog


def key(app, value):
    app.handle(pg.event.Event(pg.KEYDOWN,key=value,mod=0,unicode=''))


def click(app, action, value):
    app.renderer.render(app)
    rect = next(r for r,a,v in app.renderer.hits if (a,v)==(action,value))
    app.handle(pg.event.Event(pg.MOUSEBUTTONDOWN,button=1,pos=rect.center))
    app.handle(pg.event.Event(pg.MOUSEBUTTONUP,button=1,pos=rect.center))


@pytest.mark.parametrize('size',[(480,360),(640,480),(1280,900)])
@pytest.mark.parametrize('action',['export','save'])
def test_warning_has_three_choices_synthesis_focused_and_digi_requires_choice(size, action, monkeypatch):
    app = App(source_song(),audio=False,size=size)
    try:
        before = deepcopy(app.editor.song); calls = []
        compiled = object(); original = export_menu(app,compiled)
        monkeypatch.setattr(app,'prompt_export',lambda result,kind:calls.append((result,kind)))
        monkeypatch.setattr(app,'save_project',lambda:calls.append('save'))
        export_squeezer.activate(app,action)
        assert app.dialog['kind']=='pcm_export_confirm' and not calls
        assert [c[0] for c in choices(app.dialog)]==['Continue as DIGI','Synthesize all samples','Cancel']
        assert focus(app.dialog)==1
        app.renderer.render(app)
        assert all(app.screen.get_rect().contains(r) for r,_,_ in app.renderer.hits)
        click(app,'dialog_button',pg.K_ESCAPE)
        assert app.dialog is original and app.editor.song==before
        export_squeezer.activate(app,action)
        click(app,'dialog_button',pg.K_y)
        if action=='save':
            assert calls==['save']; app.after_save()
        assert calls[-1]==(compiled,'prg') and app.editor.song==before
    finally: app.close()


def test_unmapped_sample_bank_has_no_warning_and_failed_pcm_analysis_still_offers_synthesis(monkeypatch):
    app = App(source_song(),audio=False)
    try:
        d=export_menu(app)
        d['error']='PCM cannot fit'
        export_squeezer.activate(app,'export')
        assert app.dialog['kind']=='pcm_export_confirm'
        key(app,pg.K_ESCAPE)
        for inst in app.editor.song.instruments.values():inst.sample_override=False
        result=object();export_menu(app,result)
        calls=[];monkeypatch.setattr(app,'prompt_export',lambda *args:calls.append(args))
        export_squeezer.activate(app,'export')
        assert calls==[(result,'prg')] and app.editor.song.samples
    finally: app.close()


def test_shared_sample_fits_are_independent_and_record_provenance(fitted):
    result=deepcopy(fitted)
    a,b,c=[p['result']['instrument'] for p in result['proposals']]
    for number,inst in enumerate((a,b,c),1):
        assert not inst.sample_override and inst.sample_slot==0
        assert inst._extra_fields['editor_frozen']
        assert inst._extra_fields['sample_synthesis']['sample_slot']==(2 if number==2 else 1)
    assert (a.name,b.name,c.name)==('Kick','Snare','Second kick')
    original=deepcopy(c)
    a.pitch_sequence.append(5);a._extra_fields['sample_synthesis']['source_name']='changed'
    assert c==original


@pytest.mark.parametrize('size',[(480,360),(640,480),(1280,900)])
def test_review_audition_cancel_atomic_apply_save_and_undo(size, fitted, monkeypatch, tmp_path):
    from sidpulse.project.format import save, load
    from sidpulse.export.psid import compile_song
    app=App(source_song(),audio=False,size=size)
    try:
        before=deepcopy(app.editor.song); original=export_menu(app); calls=[]
        monkeypatch.setattr(app.audio,'send',lambda *args:calls.append(args))
        def show():
            batch_synthesis.show_result(app,deepcopy(fitted),{'return_dialog':original},deepcopy(before))
            app.renderer.render(app)
            assert all(app.screen.get_rect().contains(r) for r,_,_ in app.renderer.hits)
        show()
        click(app,'batch_action','sample');assert calls[-1][0]=='sample_on'
        click(app,'batch_action','instrument');assert calls[-1][0]=='on'
        key(app,pg.K_END);assert app.dialog['selected']==2
        click(app,'batch_action','cancel');assert app.dialog is original and app.editor.song==before
        show();click(app,'batch_action','use')
        assert app.dialog is original and app.dialog['busy'] and not app.dialog['pcm']
        assert len(app.editor.history.undo_stack)==1
        assert app.editor.song.samples==before.samples and app.editor.song.patterns==before.patterns
        assert app.editor.song.instruments[4]==before.instruments[4]
        assert all(not i.sample_override for i in app.editor.song.instruments.values())
        save(tmp_path/'batch.sidpulse',app.editor.song)
        restored=load(tmp_path/'batch.sidpulse')[0];assert restored==app.editor.song
        encoded=compile_song(restored).data
        restored.samples={};assert compile_song(restored).data==encoded
        app.editor.history.undo(app.editor.song);assert app.editor.song==before
    finally:app.close()


def test_stale_batch_result_and_stale_review_cannot_replace_instruments(fitted):
    app=App(source_song(),audio=False)
    try:
        before=deepcopy(app.editor.song);original=export_menu(app)
        app.editor.song.title='Changed'
        with pytest.raises(ValueError,match='changed during'):
            batch_synthesis.show_result(app,deepcopy(fitted),{'return_dialog':original},before)
        batch_synthesis.show_result(app,deepcopy(fitted),{'return_dialog':original},deepcopy(app.editor.song))
        app.editor.song.title='Changed again';latest=deepcopy(app.editor.song)
        batch_synthesis.activate(app,'use')
        assert app.dialog['kind']=='notice' and app.editor.song==latest
        assert not app.editor.history.undo_stack
    finally:app.close()


@pytest.mark.parametrize('invalid',['missing','long','short','silent'])
def test_invalid_batch_never_mutates_source(invalid):
    song=source_song()
    if invalid=='missing':del song.samples['2']
    elif invalid=='long':song.samples['2']=make_sample('long',bytes(20000),4000)
    elif invalid=='short':song.samples['2']=make_sample('short',bytes(10),4000)
    else:song.samples['2']=make_sample('silent',bytes(1200),4000)
    before=deepcopy(song)
    with pytest.raises(ValueError,match='[Ss]ample 02'):synthesize_mapped_samples(song)
    assert song==before


def poll_until_done(app):
    deadline=time.monotonic()+30
    while app.media_jobs and time.monotonic()<deadline:
        app.poll_media_jobs();time.sleep(.01)
    assert not app.media_jobs


def test_default_enter_runs_real_batch_worker_and_cancel_or_failure_restores_export():
    app=App(source_song(),audio=False)
    try:
        before=deepcopy(app.editor.song);original=export_menu(app)
        export_squeezer.activate(app,'export');key(app,pg.K_RETURN)
        assert app.dialog['kind']=='media_job'
        poll_until_done(app)
        assert app.dialog['kind']=='sample_synthesis_batch'
        assert app.dialog['result']['fitted_samples']==2 and app.editor.song==before
        key(app,pg.K_ESCAPE);assert app.dialog is original
        export_squeezer.activate(app,'export');key(app,pg.K_RETURN);key(app,pg.K_ESCAPE)
        assert app.dialog is original;poll_until_done(app);assert app.editor.song==before
        del app.editor.song.samples['2'];invalid=deepcopy(app.editor.song)
        export_squeezer.activate(app,'export');key(app,pg.K_RETURN);poll_until_done(app)
        assert app.dialog['kind']=='notice' and app.editor.song==invalid
        key(app,pg.K_ESCAPE);assert app.dialog is original
    finally:app.close()
