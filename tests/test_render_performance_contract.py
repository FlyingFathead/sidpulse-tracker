from copy import deepcopy
import pygame as pg
import pytest
from sidpulse.app import App
from sidpulse.song.model import Cell
from sidpulse.ui.keyboard import Command


@pytest.mark.parametrize('page',['pattern','info'])
@pytest.mark.parametrize('size',[(960,1080),(1280,900),(480,360)])
def test_cached_cells_match_direct_render_and_refresh_values(page,size):
    app=App(audio=False,size=size)
    try:
        app.change_page(page)
        for row in range(6):
            app.editor.pattern.rows[row][row%3]=Cell(48+row,1,'H',0x23,attack=row,pulse_width=0x123+row)
        app.editor.pattern.rows[6][0]=Cell(attack=-1,decay=-1,sustain=-1,release=-1,pulse_width=-1)
        r=app.renderer
        for mutation in ('initial','edit','theme','zoom'):
            if mutation=='edit':app.editor.pattern.rows[0][0].pulse_width=0xFFF
            elif mutation=='theme':app.appearance['colors']['AUTOMATION']='#12ab34'
            elif mutation=='zoom':app.zoom=1.4
            r.render(app);cached=pg.image.tobytes(app.screen,'RGB')
            optimized=r.cached_voice_cell;r.cached_voice_cell=r.voice_cell
            r.render(app);direct=pg.image.tobytes(app.screen,'RGB')
            r.cached_voice_cell=optimized
            assert cached==direct,mutation
    finally:app.close()


def test_cached_mouse_targets_follow_scroll_resize_and_control_expansion():
    app=App(audio=False,size=(960,540))
    try:
        r=app.renderer
        for row,width,control in ((0,960,False),(63,960,False),(0,700,True),(30,1280,False)):
            app.screen=pg.display.set_mode((width,540));app.editor.row=row;app.control_panel_visible=control
            r.render(app)
            cached=[(tuple(rect),action,value) for rect,action,value in r.hits if action=='cell']
            r.pattern_hit_cache=None;r.render(app)
            assert cached==[(tuple(rect),action,value) for rect,action,value in r.hits if action=='cell']
            assert any(value[0]==row for _,_,value in cached)
    finally:app.close()


def test_dirty_display_cache_does_not_replace_exact_save_checks():
    app=App(audio=False)
    try:
        r=app.renderer;ed=app.editor;r.render(app)
        assert not r.dirty_display_cache[1]
        ed.enter_note(48);r.render(app);assert r.dirty_display_cache[1]
        app.execute(Command('undo'));r.render(app);assert not r.dirty_display_cache[1]
        app.execute(Command('redo'));ed.mark_saved();r.render(app);assert not r.dirty_display_cache[1]
        ed.song.title='Out-of-history mutation'
        assert ed.dirty  # The unsaved-work guard is exact, even before refresh.
        r.dirty_display_cache=(r.dirty_display_cache[0],False,0)
        r.render(app);assert r.dirty_display_cache[1]
        app.execute(Command('quit'));assert app.dialog and app.running
    finally:app.close()


def test_responsive_layout_keeps_cached_fonts_on_steady_frames():
    app=App(audio=False,size=(720,480),zoom=1.8)
    try:
        app.control_panel_visible=False
        app.renderer.render(app)
        font=app.renderer.font
        app.renderer.render(app)
        assert app.renderer.font is font
        app.control_panel_visible=True
        app.renderer.render(app)
        assert app.renderer.control_visible
        app.change_page('instrument');app.renderer.render(app)
        font=app.renderer.font;app.renderer.render(app)
        assert app.renderer.font is font
    finally:app.close()
