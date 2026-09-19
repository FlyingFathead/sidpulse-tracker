"""Composite buttons preserve direct rendering and live hit geometry."""
import pygame as pg
import pytest
from sidpulse.app import App
from sidpulse.ui.instrument_graphs import button


@pytest.mark.parametrize('size',[(960,1080),(640,360)])
@pytest.mark.parametrize('page',['pattern','info','instrument','samples','recording'])
@pytest.mark.parametrize('theme',['Classic crimson','High contrast'])
def test_cached_button_pixels_and_targets_match_direct_drawing(size,page,theme):
    app=App(audio=False,size=size)
    try:
        app.appearance={**app.appearance,'theme':theme}
        if page=='recording':app.open_automation_recording();app.toggle_pulse_recording()
        else:app.change_page(page)
        r=app.renderer;r.render(app)
        pixels=pg.image.tobytes(app.screen,'RGB');hits=list(r.hits)
        cache=r.button_cache;r.button_cache=None
        r.render(app)
        assert pg.image.tobytes(app.screen,'RGB')==pixels
        assert r.hits==hits
        r.button_cache=cache
    finally:app.close()


def test_button_cache_is_bounded_tracks_visual_state_and_rebuilds_after_zoom():
    app=App(audio=False)
    try:
        r=app.renderer;r.render(app)
        for index in range(200):
            button(r,1,1,20,str(index),'test',index,selected=bool(index%2),fill=(120,20,30))
        assert len(r.button_cache)==128
        for selected in (False,True):
            r.screen.fill((0,0,0))
            rect=button(r,2,2,25,'Arm recording','automation_arm',selected=selected,fill=(120,20,30))
            pixels=pg.image.tobytes(r.screen.subsurface(rect),'RGB')
            cache=r.button_cache;r.button_cache=None
            button(r,2,2,25,'Arm recording','automation_arm',selected=selected,fill=(120,20,30))
            assert pg.image.tobytes(r.screen.subsurface(rect),'RGB')==pixels
            r.button_cache=cache
        old=tuple(r.button_cache);app.zoom=2;r.render(app)
        assert len(r.button_cache)<128 and not any(k in r.button_cache for k in old)
    finally:app.close()
