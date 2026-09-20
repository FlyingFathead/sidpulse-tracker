"""Page changes must not shrink the UI just to display extra pattern voices."""
from copy import deepcopy

import pygame as pg
import pytest

from sidpulse.app import App


@pytest.mark.parametrize('size,zoom', [
    ((1280, 900), 1), ((960, 1080), 1), ((960, 540), 1),
    ((1920, 1080), 1.5), ((1280, 900), 2),
])
def test_f2_and_info_keep_requested_font_and_cached_glyphs(size, zoom):
    app = App(audio=False, size=size, zoom=zoom)
    try:
        app.change_page('orders')
        r = app.renderer
        r.render(app)
        metrics = (r.layout.font_size, r.cw, r.rh)
        font = r.font
        before = deepcopy(app.editor.song)
        for page in ('pattern', 'info', 'orders', 'pattern'):
            if page == 'pattern':
                app.handle(pg.event.Event(pg.KEYDOWN, key=pg.K_F2, mod=0,
                                          unicode='', scancode=0))
            else:
                app.change_page(page)
            r.render(app)
            assert (r.layout.font_size, r.cw, r.rh) == metrics
            assert r.font is font
            r.render(app)
            assert r.font is font
        assert app.zoom == zoom
        assert app.editor.song == before
    finally:
        app.close()


@pytest.mark.parametrize('size,zoom', [((960, 1080), 1), ((1280, 900), 2),
                                      ((480, 360), 3)])
def test_fewer_visible_voices_still_follow_every_channel_and_field(size, zoom):
    app = App(audio=False, size=size, zoom=zoom)
    try:
        app.change_page('pattern')
        for voice in range(3):
            app.editor.voice = voice
            app.editor.row = len(app.editor.pattern.rows) - 1
            app.renderer.render(app)
            for column in range(17):
                target = next(rect for rect, action, value in app.renderer.hits
                              if action == 'cell' and value == (app.editor.row, voice, column))
                assert app.screen.get_rect().contains(target)
                assert target.bottom <= (app.renderer.lines - app.renderer.footer_rows) * app.renderer.rh
        assert app.zoom == zoom
    finally:
        app.close()
