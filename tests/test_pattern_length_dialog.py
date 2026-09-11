from copy import deepcopy
import pygame as pg
import pytest
from sidpulse.app import App
from sidpulse.song.model import Cell,ControlCell,Pattern
from sidpulse.ui.keyboard import Command
from test_checkpoint_026 import key,click


@pytest.fixture
def app():
    a=App(audio=False)
    yield a
    a.close()


def open_length(app):
    key(app,pg.K_F2,mod=pg.KMOD_CTRL)
    assert app.dialog['kind']=='pattern_length'


def text(app,value):
    app.handle(pg.event.Event(pg.TEXTINPUT,text=value))


def test_slider_min_max_staged_and_cancel(app):
    before=deepcopy(app.editor.song)
    open_length(app);app.renderer.render(app)
    track=next(r for r,a,_ in app.renderer.hits if a=='length_slider')
    app.handle(pg.event.Event(pg.MOUSEBUTTONDOWN,button=1,pos=track.midleft))
    assert app.dialog['value']==1
    app.handle(pg.event.Event(pg.MOUSEMOTION,pos=(track.right+100,track.centery)))
    app.handle(pg.event.Event(pg.MOUSEBUTTONUP,button=1,pos=(track.right+100,track.centery)))
    assert app.dialog['value']==256 and app.editor.song==before
    click(app,'length_button','cancel')
    assert app.dialog is None and app.editor.song==before and not app.editor.dirty


def test_only_clicking_number_activates_typing_and_links_slider(app):
    open_length(app)
    text(app,'128');key(app,pg.K_1,'1')
    assert app.dialog['value']==64 and not app.dialog['editing']
    key(app,pg.K_TAB);text(app,'128')
    assert app.dialog['value']==64 and not app.dialog['editing']
    click(app,'length_value')
    for char in '128':text(app,char)
    assert app.dialog['value']==128 and app.dialog['text']=='128'
    text(app,'9');assert app.dialog['text']=='128'
    app.renderer.render(app)
    track=next(r for r,a,_ in app.renderer.hits if a=='length_slider')
    # The same displayed slider can replace the manually entered draft.
    app.handle(pg.event.Event(pg.MOUSEBUTTONDOWN,button=1,pos=(track.right-1,track.centery)))
    app.handle(pg.event.Event(pg.MOUSEBUTTONUP,button=1,pos=(track.right-1,track.centery)))
    assert app.dialog['value']==256 and not app.dialog['editing']
    app.renderer.render(app)
    click(app,'length_button','ok')
    assert app.dialog is None and len(app.editor.pattern.rows)==256


@pytest.mark.parametrize('invalid',['000','999'])
def test_invalid_number_cannot_resize(app,invalid):
    open_length(app);click(app,'length_value');text(app,invalid)
    before=deepcopy(app.editor.song)
    click(app,'length_button','ok')
    assert app.dialog['error'] and app.editor.song==before
    key(app,pg.K_a,mod=pg.KMOD_CTRL);text(app,'032');text(app,'abc')
    assert app.dialog['value']==32 and app.dialog['text']=='032'
    key(app,pg.K_RETURN)
    assert app.dialog is None and len(app.editor.pattern.rows)==32


def test_shorten_correct_pattern_preserves_others_and_undo_restores_controls(app):
    app.editor.song.patterns[1]=Pattern(name='Other pattern')
    app.editor.pattern.rows[50][2]=Cell(60,1)
    app.editor.pattern.controls[50]=ControlCell(cutoff=123)
    before=deepcopy(app.editor.song)
    open_length(app);click(app,'length_value');text(app,'032')
    # Playback-follow may switch the visible pattern while the modal is open.
    app.editor.select_pattern(1)
    click(app,'length_button','ok')
    assert len(app.editor.song.patterns[0].rows)==32 and not app.editor.song.patterns[0].controls
    assert app.editor.song.patterns[1]==before.patterns[1]
    assert len(app.editor.history.undo_stack)==1
    app.execute(Command('undo'));assert app.editor.song==before
    app.execute(Command('redo'));assert len(app.editor.song.patterns[0].rows)==32


@pytest.mark.parametrize('size,zoom',[((1280,900),1),((480,360),3),((800,600),.5)])
def test_centered_field_and_controls_fit_after_resize(app,size,zoom):
    app.zoom=zoom;open_length(app)
    app.handle(pg.event.Event(pg.VIDEORESIZE,w=size[0],h=size[1]))
    app.renderer.render(app)
    hits=app.renderer.hits
    assert len(hits)==4 and all(app.screen.get_rect().contains(r) for r,_,_ in hits)
    track=next(r for r,a,_ in hits if a=='length_slider')
    value=next(r for r,a,_ in hits if a=='length_value')
    assert abs(track.centerx-value.centerx)<=1 and value.top>track.bottom
    assert all(not value.colliderect(r) for r,a,_ in hits if a=='length_button')
    key(app,pg.K_END);key(app,pg.K_ESCAPE)
    assert app.dialog is None and len(app.editor.pattern.rows)==64
