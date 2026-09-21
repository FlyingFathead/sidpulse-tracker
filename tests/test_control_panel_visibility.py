from copy import deepcopy
import json

import pygame as pg
import pytest

from sidpulse.app import App
from sidpulse.preferences import load_control_panel_visibility, load_pattern_clipboard_buttons, config_path
from sidpulse.ui.keyboard import Command


@pytest.mark.parametrize('size,initial_voices', [
    ((960,1080), {0,1}), ((960,540), {0,1,2}), ((800,600), {0,1}),
])
def test_narrow_default_keeps_font_and_follows_all_voices(size, initial_voices):
    app=App(audio=False,size=size)
    try:
        app.change_page('orders')
        app.renderer.render(app)
        font=app.renderer.font
        metrics=(app.renderer.cw,app.renderer.rh)
        before=deepcopy(app.editor.song)
        app.change_page('pattern')
        app.renderer.render(app)
        assert not app.renderer.control_visible
        assert {v[1] for r,a,v in app.renderer.hits if a=='cell'}==initial_voices
        toggle=next(r for r,a,v in app.renderer.hits if a=='control_panel_toggle')
        assert app.screen.get_rect().contains(toggle)
        assert not any(a=='control_focus' for _,a,_ in app.renderer.hits)
        assert app.control_panel_visible is None
        for voice in (2,1,0):
            app.editor.voice=voice
            app.renderer.render(app)
            cells=[(r,v[2]) for r,a,v in app.renderer.hits
                   if a=='cell' and v[:2]==(app.editor.row,voice)]
            assert {column for _,column in cells}==set(range(17))
            assert all(app.screen.get_rect().contains(r) for r,_ in cells)
            assert app.renderer.font is font
            assert (app.renderer.cw,app.renderer.rh)==metrics
            assert not app.renderer.control_visible
        assert app.zoom==1 and app.editor.song==before
    finally:app.close()


def test_toggle_persists_across_playback_views_stop_and_reload_without_music_changes():
    app=App(audio=False)
    try:
        original=deepcopy(app.editor.song);state=app.audio.playback
        app.renderer.render(app);assert app.renderer.control_visible
        for page in ('pattern','info','pattern','info'):
            app.change_page(page);app.renderer.render(app)
            rect=next(r for r,a,v in reversed(app.renderer.hits) if a=='control_panel_toggle')
            app.handle(pg.event.Event(pg.MOUSEBUTTONDOWN,button=1,pos=rect.center))
            app.renderer.render(app)
            expected=app.control_panel_visible
            assert app.renderer.control_visible==expected
            for other in ('pattern','info'):
                app.change_page(other);app.renderer.render(app)
                assert app.renderer.control_visible==expected
            assert app.editor.song==original and app.audio.playback==state
        assert load_control_panel_visibility() is True
        app.toggle_control_panel();app.close()
        app=App(audio=False,size=(1920,1080));app.renderer.render(app)
        assert app.control_panel_visible is False and not app.renderer.control_visible
        app.execute(Command('control_focus'));app.renderer.render(app)
        assert app.control_focus and app.renderer.control_visible
    finally:app.close()


@pytest.mark.parametrize('value',[None,'false',0,{},[]])
def test_bad_visibility_preferences_fall_back_without_coercion(value):
    path=config_path();path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps({'control_panel_visible':value,'pattern_clipboard_buttons':value}))
    assert load_control_panel_visibility() is None
    assert load_pattern_clipboard_buttons() is True
