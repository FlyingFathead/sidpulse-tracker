"""Exact four-version results, shared expensive work, and selectable comparison UI."""
from copy import deepcopy
from dataclasses import replace
import pytest
import pygame as pg

from sidpulse.export.comparison import compile_comparison, Comparison, VersionResult
from sidpulse.export.squeeze import SqueezeOptions
from sidpulse.export.psid import compile_song, ExportMemoryError, ExportError
from sidpulse.export.prg import compile_prg
from sidpulse.song.model import Song, example_song
from sidpulse.preferences import (load_squeeze_comparison, load_squeeze_show_all_versions,
                                  save_preferences, config_path, reset_preferences)
from sidpulse.app import App
from sidpulse.ui import export_squeezer as ui
from export_gui_helpers import finish_export_analysis
from sidpulse.ui.squeezer_comparison import visible_entries


@pytest.mark.parametrize('kind', ['sid','prg'])
def test_cached_comparison_is_identical_to_four_independent_compiles(kind, monkeypatch):
    import sidpulse.export.psid as psid
    import sidpulse.export.squeeze_v2 as v2
    import sidpulse.export.squeeze_v201 as v201
    import sidpulse.export.squeeze_v202 as v202
    song = example_song(); before = deepcopy(song); options = SqueezeOptions()
    compiler = compile_song if kind=='sid' else compile_prg
    expected = {v:compiler(song,squeeze=replace(options,version=v)) for v in (1,2,201,202)}
    counts = {}
    for module,name in ((psid,'_record_song'),(psid,'optimized_stream_candidates'),
                        (v2,'additional_candidates'),(v201,'additional_candidates'),(v202,'additional_candidates')):
        original = getattr(module,name); identity = module.__name__+'.'+name
        def counted(*args, _original=original, _identity=identity, **kwargs):
            counts[_identity] = counts.get(_identity,0)+1
            return _original(*args,**kwargs)
        monkeypatch.setattr(module,name,counted)
    comparison = compile_comparison(song,options,kind)
    assert {e.version:e.result for e in comparison.entries} == expected
    assert song == before
    assert all(count==1 for key,count in counts.items() if not key.endswith('._record_song'))
    assert counts['sidpulse.export.psid._record_song'] <= 2  # includes source-cleanup check
    assert len(comparison.best.result.data) == min(len(r.data) for r in expected.values())


def test_one_oversized_version_does_not_hide_a_valid_alternative(monkeypatch):
    import sidpulse.export.psid as psid
    expected = compile_song(Song())
    def compile(song, *, squeeze, **kwargs):
        if squeeze.version == 1: raise ExportMemoryError(512,40000,100)
        return expected
    monkeypatch.setattr(psid,'compile_song',compile)
    result = compile_comparison(Song(),SqueezeOptions(),'sid')
    assert result.entries[0].error and result.entries[0].result is None
    assert result.best.version == 202
    def fail(*args, **kwargs): raise ExportError('Squeeze replay verification failed')
    monkeypatch.setattr(psid,'compile_song',fail)
    with pytest.raises(ExportError,match='verification failed'):
        compile_comparison(Song(),SqueezeOptions(),'sid')


def test_complete_tie_keeps_current_choice_and_size_only_tie_uses_ram_then_cycles():
    result = compile_song(Song())
    equal = Comparison(tuple(VersionResult(v,result) for v in (1,2,201,202)))
    assert len(equal.leaders)==4 and equal.best.version==202
    assert equal.preferred(1).version==1 and equal.preferred(2).version==2
    assert equal.preferred(99).version==202
    larger_ram = replace(result,squeeze_report=replace(result.squeeze_report,zero_page_bytes=20))
    slow = replace(result,squeeze_report=replace(result.squeeze_report,verified_max_cycles=99999))
    different = Comparison((VersionResult(1,result),VersionResult(2,larger_ram),VersionResult(201,slow)))
    assert [entry.version for entry in different.leaders]==[1]
    unknown = replace(result,squeeze_report=replace(result.squeeze_report,verified_max_cycles=0))
    assert Comparison((VersionResult(1,result),VersionResult(201,unknown))).best.version==1


@pytest.mark.parametrize('value',[None,1,'false',[],{},False,True])
def test_config_boolean_and_safe_default(value):
    save_preferences({'export_compare_squeezers':value,'export_show_all_versions':value})
    assert load_squeeze_comparison() is (value if type(value) is bool else True)
    assert load_squeeze_show_all_versions() is (value if type(value) is bool else True)


@pytest.mark.parametrize('size',[(360,360),(480,360),(960,1080)])
def test_columns_buttons_keyboard_selection_and_comparison_off(size,monkeypatch):
    app=App(audio=False,size=size)
    try:
        before=deepcopy(app.editor.song)
        app.begin_export();finish_export_analysis(app)
        comparison=app.dialog['comparison']
        assert comparison and app.dialog['options'].version==comparison.best.version
        assert len(visible_entries(app.dialog))==4
        for entry in comparison.entries:
            index=next(i for i,e in enumerate(visible_entries(app.dialog)) if e.version==entry.version)
            app.dialog['focus']=11+index;app.dialog['ensure_focus']=True
            app.renderer.render(app)
            hits=[(r,v) for r,a,v in app.renderer.hits if a=='squeeze_use_version']
            assert entry.version in {v for _,v in hits}
            if size[0]>=960: assert {v for _,v in hits}=={1,2,201,202}
            assert all(app.screen.get_rect().contains(r) for r,_ in hits)
            rect=next(r for r,v in hits if v==entry.version)
            app.handle(pg.event.Event(pg.MOUSEBUTTONDOWN,button=1,pos=rect.center))
            assert app.dialog['result'] is entry.result
            assert app.dialog['focus']==11+next(i for i,e in enumerate(visible_entries(app.dialog)) if e.version==entry.version)
            assert not app.dialog.get('busy') and not app.export_jobs
        app.dialog['focus']=11+next(i for i,e in enumerate(visible_entries(app.dialog)) if e.version==1)
        app.handle(pg.event.Event(pg.KEYDOWN,key=pg.K_RETURN,mod=0,unicode=''))
        assert app.dialog['options'].version==1
        ui.toggle_comparison(app)
        assert not app.dialog['compare'] and app.dialog['comparison'] is None
        ui.analyze(app);finish_export_analysis(app)
        assert app.dialog['comparison'] is None and app.dialog['result'].squeeze_report.squeezer_version==1
        app.renderer.render(app)
        assert not any(a=='squeeze_use_version' for _,a,_ in app.renderer.hits)
        ui.activate(app,'export')
        assert load_squeeze_comparison() is False and app.editor.song==before
    finally:app.close()


def test_cancel_does_not_save_comparison_toggle():
    app=App(audio=False)
    try:
        app.begin_export();finish_export_analysis(app)
        ui.toggle_comparison(app);ui.activate(app,'cancel')
        assert load_squeeze_comparison() is True
    finally:app.close()


def test_show_all_default_persists_on_cancel_and_restart_and_reset_restores_it(monkeypatch):
    calls=[]
    monkeypatch.setattr(ui,'analyze',lambda app:calls.append(app.dialog))
    assert load_squeeze_show_all_versions() is True  # Missing config migrates to all.
    save_preferences({'audio_buffer':512,'export_squeeze':{'version':1}})
    app=App(audio=False)
    try:
        ui.open_dialog(app)
        assert app.dialog['show_all_versions'] is True
        app.dialog['comparison']=object()
        ui.toggle_all_versions(app)
        assert app.dialog['show_all_versions'] is False and len(calls)==1
        ui.activate(app,'cancel')
        assert load_squeeze_show_all_versions() is False
    finally:app.close()
    app=App(audio=False)
    try:
        ui.open_dialog(app,'prg')
        assert app.dialog['show_all_versions'] is False
        app.dialog['comparison']=object()
        ui.toggle_all_versions(app)
        assert load_squeeze_show_all_versions() is True and len(calls)==2
        import json
        saved=json.loads(config_path().read_text())
        assert saved['audio_buffer']==512 and saved['export_squeeze']['version']==1
        ui.toggle_all_versions(app)
        reset_preferences()
        ui.open_dialog(app)
        assert app.dialog['show_all_versions'] is True
    finally:app.close()


def test_show_all_write_failure_keeps_current_choice_and_reports_error(monkeypatch):
    monkeypatch.setattr(ui,'analyze',lambda app:None)
    app=App(audio=False)
    try:
        ui.open_dialog(app);app.dialog['comparison']=object()
        def fail(updates):raise OSError('Read-only settings')
        monkeypatch.setattr(ui,'save_preferences',fail)
        ui.toggle_all_versions(app)
        assert app.dialog['show_all_versions'] is True
        assert 'Read-only settings' in app.dialog['error']
    finally:app.close()
