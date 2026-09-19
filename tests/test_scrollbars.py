"""Overflow controls navigate views without changing songs or filename drafts."""
from copy import deepcopy
import pygame as pg
import pytest
from sidpulse.app import App
from sidpulse.song.model import Pattern


def drag(app, key, bottom=True):
    state = app.renderer.scrollbars.states[key]
    track, thumb, maximum, page = state['scrollbar']
    assert app.screen.get_rect().contains(track)
    app.handle(pg.event.Event(pg.MOUSEBUTTONDOWN, button=1, pos=thumb.center))
    # Redraw during the drag, as a real event loop does.
    for y in (track.centery, track.bottom + 100 if bottom else track.top - 100):
        app.handle(pg.event.Event(pg.MOUSEMOTION, pos=(thumb.centerx, y), buttons=(1,0,0), rel=(0,1)))
        app.renderer.render(app)
    app.handle(pg.event.Event(pg.MOUSEBUTTONUP, button=1, pos=thumb.center))
    assert state['scroll'] == (maximum if bottom else 0)
    assert 'scroll_drag' not in state


@pytest.mark.parametrize('page,key', [('pattern','pattern'), ('instrument','instruments'),
    ('samples','samples'), ('settings','settings'), ('help','help'), ('orders','orders'),
    ('files','files')])
def test_shared_scrollbars_reach_both_ends_without_editing(page,key,tmp_path):
    app=App(audio=False,size=(960,540))
    try:
        app.editor.song.orders=[0]*90
        app.change_page(page)
        if page=='files':
            for n in range(80): (tmp_path/f'{n:03d}.sidpulse').write_text('{}')
            app.browser.navigate(tmp_path)
            app.browser.set_name('Keep my filename.sidpulse')
        original=deepcopy(app.editor.song)
        name=app.browser.name.text
        app.renderer.render(app)
        drag(app,key)
        drag(app,key,False)
        assert app.editor.song==original and not app.editor.history.undo_stack
        assert app.browser.name.text==name
        if page=='help':
            app.handle(pg.event.Event(pg.MOUSEWHEEL,x=0,y=-1))
            app.renderer.render(app)
            assert app.help_scroll==3
        app.change_page('info');app.renderer.render(app)
        assert key not in app.renderer.scrollbars.visible
    finally: app.close()


@pytest.mark.parametrize('page,key,selection', [('instrument','instruments','instrument_slot'),('samples','samples','sample_index')])
def test_keyboard_selection_resumes_centering_after_manual_scroll(page,key,selection):
    app=App(audio=False,size=(960,540))
    try:
        app.change_page(page);app.renderer.render(app)
        drag(app,key)
        assert getattr(app,selection)==1
        app.handle(pg.event.Event(pg.KEYDOWN,key=pg.K_DOWN,mod=0,unicode='',scancode=0))
        app.renderer.render(app)
        assert getattr(app,selection)==2
        assert app.renderer.scrollbars.states[key]['scroll']==0
    finally: app.close()


def test_overflow_menus_comments_messages_presets_and_pattern_bank():
    app=App(audio=False,size=(480,360))
    try:
        app.menu_path=['UI Settings'];app.menu_indices=[0];app.renderer.render(app)
        drag(app,'menu:UI Settings')
        app.menu_path.clear();app.menu_indices.clear()
        app.open_presets();app.renderer.render(app)
        drag(app,'presets')
        app.dialog={'title':'Long notice','message':'A long explanation. '*100}
        app.renderer.render(app);drag(app,'message')
        app.dialog={'title':'Comments','text':'\n'.join(f'Line {n}' for n in range(80)),'multiline':True}
        app.renderer.render(app);drag(app,'comments',False)
        original=app.dialog['text'];drag(app,'comments');assert app.dialog['text']==original
        app.dialog=None
        app.editor.song.patterns.update({i:Pattern() for i in range(90)})
        app.change_page('orders');app.renderer.render(app);drag(app,'patterns')
    finally:app.close()


def test_fitting_views_hide_scrollbar_and_modal_blocks_underlying_drag():
    app=App(audio=False,size=(960,1800))
    try:
        app.change_page('settings');app.renderer.render(app)
        assert 'settings' not in app.renderer.scrollbars.visible
        app.change_page('instrument');app.renderer.render(app)
        track,thumb,_,_=app.renderer.scrollbars.states['instruments']['scrollbar']
        app.dialog={'title':'Notice','message':'Short notice.'}
        app.renderer.render(app)
        assert not app.renderer.scrollbars.visible
        app.handle(pg.event.Event(pg.MOUSEBUTTONDOWN,button=1,pos=thumb.center))
        assert app.instrument_slot==1
        app.dialog=None;app.renderer.render(app)
        state=app.renderer.scrollbars.states['instruments']
        app.handle(pg.event.Event(pg.MOUSEBUTTONDOWN,button=1,pos=state['scrollbar'][1].center))
        app.handle(pg.event.Event(pg.WINDOWFOCUSLOST))
        assert 'scroll_drag' not in state
    finally:app.close()
