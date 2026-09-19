"""Ranked Top 3, all-version access and a visible scroll control without analysis."""
from dataclasses import replace
from types import SimpleNamespace
import pygame as pg
import pytest
from sidpulse.app import App
from sidpulse.export.comparison import Comparison,VersionResult
from sidpulse.export.squeeze import SqueezeOptions,SqueezeReport,CleanupStats
from sidpulse.export.psid import ExportResult
from sidpulse.ui import export_squeezer as ui
from sidpulse.ui.squeezer_comparison import visible_entries


def result(size, cycles=100, ram=500):
    report=SqueezeReport(True,'Test fixture',1000,ram,100,ram-100,2,4,CleanupStats(),verified_calls=10,verified_max_cycles=cycles)
    return ExportResult(b'x'*size,10,1,1.0,1000,(),report)


def dialog(song, entries, version=202):
    comparison=Comparison(tuple(entries));entry=next(e for e in entries if e.version==version)
    return dict(kind='export_squeezer',title='Export',target='prg',options=SqueezeOptions(version=version),focus=8,
                result=entry.result,source=song,scroll=0,ensure_focus=False,version_open=False,compare=True,comparison=comparison,
                show_all_versions=False)


def test_ranking_ties_unknown_cpu_and_unavailable_candidates():
    d=dialog(None,[VersionResult(1,result(400)),VersionResult(2,result(300)),VersionResult(201,result(200)),VersionResult(202,result(100))])
    assert [e.version for e in visible_entries(d)]==[202,201,2]
    d['options']=SqueezeOptions(version=1)
    assert [e.version for e in visible_entries(d)]==[202,201,2]  # explicit larger choice does not alter ranking
    d['show_all_versions']=True
    assert [e.version for e in visible_entries(d)]==[202,201,2,1]
    same=result(100)
    d=dialog(None,[VersionResult(v,same) for v in (1,2,201,202)],version=1)
    assert visible_entries(d)[0].version==1 and len(d['comparison'].leaders)==4
    entries=[VersionResult(1,result(100,cycles=0)),VersionResult(2,result(100,cycles=200)),
             VersionResult(201,result(100,cycles=100,ram=501)),VersionResult(202,result(100,cycles=100))]
    d=dialog(None,entries)
    assert [e.version for e in visible_entries(d)]==[202,2,1]
    d=dialog(None,[VersionResult(1,error='Does not fit'),VersionResult(202,result(100))])
    assert [e.version for e in visible_entries(d)]==[202]
    d['show_all_versions']=True;assert visible_entries(d)[-1].version==1


@pytest.mark.parametrize('size',[(360,360),(480,360),(960,540),(960,1080)])
def test_scrollbar_top_three_and_worst_choice_keep_exact_result_without_compiling(size,monkeypatch):
    app=App(audio=False,size=size)
    try:
        entries=[VersionResult(v,result(n)) for v,n in ((1,400),(2,300),(201,200),(202,100))]
        app.dialog=dialog(app.editor.song,entries)
        def forbidden(*args,**kwargs):raise AssertionError('View change launched analysis')
        monkeypatch.setattr(ui,'analyze',forbidden)
        app.renderer.render(app)
        track,thumb,maximum,page=app.dialog['scrollbar']
        assert maximum>0 and app.screen.get_rect().contains(track)
        buttons={v:r.copy() for r,a,v in app.renderer.hits if a=='squeeze_button'}
        assert set(buttons)=={'analyze','save','export','cancel'}
        for a in ('squeeze_scroll_track','squeeze_scroll_thumb'):assert any(action==a for _,action,_ in app.renderer.hits)
        app.handle(pg.event.Event(pg.MOUSEBUTTONDOWN,button=1,pos=thumb.center))
        app.handle(pg.event.Event(pg.MOUSEMOTION,pos=(thumb.centerx,track.bottom+100),rel=(0,100),buttons=(1,0,0)))
        app.handle(pg.event.Event(pg.MOUSEBUTTONUP,button=1,pos=(thumb.centerx,track.bottom)))
        app.renderer.render(app)
        assert app.dialog['scroll']==app.dialog['scroll_max'] and 'scroll_drag' not in app.dialog
        assert buttons=={v:r for r,a,v in app.renderer.hits if a=='squeeze_button'}
        # Wheel and Home/End remain usable and reach exact bounds.
        app.handle(pg.event.Event(pg.MOUSEWHEEL,y=1,x=0));app.renderer.render(app)
        assert app.dialog['scroll']<app.dialog['scroll_max']
        app.handle(pg.event.Event(pg.KEYDOWN,key=pg.K_HOME,mod=0,unicode=''));app.renderer.render(app)
        assert app.dialog['scroll']==0
        track,thumb,maximum,page=app.dialog['scrollbar']
        app.handle(pg.event.Event(pg.MOUSEBUTTONDOWN,button=1,pos=(track.centerx,track.bottom-2)))
        app.renderer.render(app);assert app.dialog['scroll']>0
        app.handle(pg.event.Event(pg.KEYDOWN,key=pg.K_END,mod=0,unicode=''));app.renderer.render(app)
        assert app.dialog['scroll']==app.dialog['scroll_max']
        # Clicking Show all only changes the view. The larger version is selectable.
        app.dialog.update(focus=20,ensure_focus=True);app.renderer.render(app)
        rect=next(r for r,a,_ in app.renderer.hits if a=='squeeze_show_all')
        app.handle(pg.event.Event(pg.MOUSEBUTTONDOWN,button=1,pos=rect.center));assert len(visible_entries(app.dialog))==4
        index=next(i for i,e in enumerate(visible_entries(app.dialog)) if e.version==1)
        app.dialog.update(focus=11+index,ensure_focus=True);app.renderer.render(app)
        rect=next(r for r,a,v in app.renderer.hits if a=='squeeze_use_version' and v==1)
        app.handle(pg.event.Event(pg.MOUSEBUTTONDOWN,button=1,pos=rect.center))
        assert app.dialog['result'] is entries[0].result and app.dialog['options'].version==1
        ui.toggle_all_versions(app);app.renderer.render(app)
        assert [e.version for e in visible_entries(app.dialog)]==[202,201,2]
        assert app.dialog['result'] is entries[0].result and not app.export_jobs
        # Dropdown access to the worst choice works even while Top 3 stays visible.
        ui.select_version(app,202);ui.select_version(app,1)
        assert app.dialog['result'] is entries[0].result
    finally:app.close()
