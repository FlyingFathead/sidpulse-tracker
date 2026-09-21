"""The fitted grid retains editable fields, independent page metrics and caches."""
from copy import deepcopy
import json

import pygame as pg
import pytest

from sidpulse.app import App
from sidpulse.preferences import config_path, load_pattern_fit_three, save_preferences
from sidpulse.ui.keyboard import Command
from sidpulse.ui.menus import menu_items


def click(app, action, value):
    rect = next(r for r, a, v in app.renderer.hits if (a, v) == (action, value))
    for kind in (pg.MOUSEBUTTONDOWN, pg.MOUSEBUTTONUP):
        app.handle(pg.event.Event(kind, button=1, pos=rect.center))


@pytest.mark.parametrize('size,zoom', [((960,1080),1), ((960,540),1),
    ((800,600),1), ((1280,900),2), ((1920,1080),1.5)])
@pytest.mark.parametrize('control', [False, True])
def test_all_fields_fit_and_mouse_positions_match_after_resize(size, zoom, control):
    app = App(audio=False, size=(1280,900), zoom=zoom)
    try:
        assert app.pattern_fit_three
        before = deepcopy(app.editor.song)
        app.screen = pg.display.set_mode(size)
        app.control_panel_visible = control
        r = app.renderer
        for row in (0, 63, 30):
            app.editor.row = row
            r.render(app)
            cells = [(rect, value) for rect, action, value in r.hits
                     if action == 'cell' and value[0] == row]
            assert len(cells) == 3 * 17
            for rect, value in cells:
                assert app.screen.get_rect().contains(rect)
                assert rect.bottom <= (r.lines-r.footer_rows)*r.rh
                assert app.pattern_position(rect.center) == value
            assert r.control_visible == control
            assert app.screen.get_rect().contains(next(rect for rect, action, _ in r.hits
                                                       if action == 'control_panel_toggle'))
        assert app.zoom == zoom and app.editor.song == before
    finally:
        app.close()


def test_menu_toggle_persists_without_changing_song_zoom_or_info_view():
    app = App(audio=False, size=(960,1080))
    try:
        before = deepcopy(app.editor.song)
        status = app.editor.status
        r = app.renderer
        app.change_page('info'); r.render(app)
        info = pg.image.tobytes(app.screen, 'RGB')
        app.change_page('pattern'); r.render(app)
        page_font = r.font
        toolbar = [(tuple(rect), action) for rect, action, _ in r.hits
                   if action in ('pattern_copy', 'reset_automation')]
        items = menu_items('UI Settings')
        index = next(i for i, item in enumerate(items) if item.command == 'pattern_fit_three_toggle')
        app.menu_path = ['UI Settings']; app.menu_indices = [index]
        r.render(app); click(app, 'menu', index)
        assert not app.pattern_fit_three and not load_pattern_fit_three()
        app.menu_path.clear(); app.menu_indices.clear()
        r.render(app)
        assert {v[1] for _, a, v in r.hits if a == 'cell'} == {0, 1}
        assert r.font is page_font
        assert toolbar == [(tuple(rect), action) for rect, action, _ in r.hits
                           if action in ('pattern_copy', 'reset_automation')]
        for voice in (2, 0):
            app.editor.voice = voice; r.render(app)
            assert len([v for _, a, v in r.hits if a == 'cell' and v[:2] == (0, voice)]) == 17
        app.editor.status = status
        app.change_page('info'); r.render(app)
        assert pg.image.tobytes(app.screen, 'RGB') == info
        assert app.editor.song == before and app.zoom == 1
        app.close()
        app = App(audio=False, size=(960,1080))
        assert not app.pattern_fit_three
        app.execute(Command('pattern_fit_three_toggle'))
        assert app.pattern_fit_three and load_pattern_fit_three()
    finally:
        app.close()


def test_fitted_mouse_drag_copy_paste_and_undo_only_change_pw():
    app = App(audio=False, size=(800,600))
    try:
        ed, r = app.editor, app.renderer
        for row in range(4):
            ed.pattern.rows[row][0].pulse_width = 0x123 + row
            ed.pattern.rows[row][2].note = 60 + row
        ed.mark_saved()
        before = deepcopy(ed.song)
        r.render(app)
        assert r.pattern_geometry['cw'] < r.cw
        first = next(rect for rect, a, v in r.hits if a == 'cell' and v == (0,0,15))
        last = next(rect for rect, a, v in r.hits if a == 'cell' and v == (3,0,15))
        app.handle(pg.event.Event(pg.MOUSEBUTTONDOWN, button=1, pos=first.center))
        app.handle(pg.event.Event(pg.MOUSEMOTION, pos=last.center, buttons=(1,0,0), rel=(0,0)))
        app.handle(pg.event.Event(pg.MOUSEBUTTONUP, button=1, pos=last.center))
        assert ed.selected_fields(0) == {'pulse_width'}
        app.execute(Command('copy', False))
        r.render(app); click(app, 'cell', (0,2,0))
        app.execute(Command('paste', 'overwrite'))
        for row in range(4):
            assert ed.pattern.rows[row][2].pulse_width == 0x123 + row
            assert ed.pattern.rows[row][2].note == 60 + row
        app.execute(Command('undo'))
        assert ed.song == before
    finally:
        app.close()


def test_steady_frames_reuse_fonts_glyphs_and_hit_rectangles(monkeypatch):
    app = App(audio=False, size=(960,1080))
    try:
        r = app.renderer
        r.render(app)
        font, metrics = r.font, r.pattern_layout.metrics
        cells = r.pattern_hit_cache[1]
        cached = tuple(dict(cache) for cache in metrics[3:])
        def unexpected_font(*args, **kwargs):
            raise AssertionError('Steady F2 frames must reuse existing fonts')
        monkeypatch.setattr(pg.font, 'Font', unexpected_font)
        for _ in range(4):
            r.render(app)
            assert r.font is font and r.pattern_layout.metrics is metrics
            assert r.pattern_hit_cache[1] is cells
            assert tuple(dict(cache) for cache in metrics[3:]) == cached
    finally:
        app.close()


def test_tiny_view_keeps_font_floor_and_selected_fields_reachable():
    app = App(audio=False, size=(480,360), zoom=3)
    try:
        app.control_panel_visible = True
        for voice in range(3):
            app.editor.voice = voice
            app.renderer.render(app)
            assert app.renderer.pattern_geometry['font_size'] >= 8
            cells = [rect for rect, a, v in app.renderer.hits
                     if a == 'cell' and v[:2] == (app.editor.row, voice)]
            assert len(cells) == 17 and all(app.screen.get_rect().contains(rect) for rect in cells)
    finally:
        app.close()


@pytest.mark.parametrize('value', [None, 0, 'false', [], {}, True, False])
def test_preference_accepts_only_booleans_and_migrates_missing_key(value):
    assert load_pattern_fit_three() is True
    save_preferences({'pattern_fit_three': value, 'audio_buffer': 4096})
    assert load_pattern_fit_three() is (value if type(value) is bool else True)
    assert json.loads(config_path().read_text())['audio_buffer'] == 4096
