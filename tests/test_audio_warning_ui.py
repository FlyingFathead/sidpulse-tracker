"""Audio shortcut, persisted detection toggle and unobtrusive warning behavior."""
import json
from copy import deepcopy
import time

import pygame as pg
import pytest

from sidpulse.app import App
from sidpulse.preferences import config_path, load_audio_underrun_detection, save_preferences
from sidpulse.ui.keyboard import dispatch
from sidpulse.ui.registry import COMMANDS, match_event
from sidpulse.ui.audio_buffer import open_dialog, activate


@pytest.fixture
def app():
    instance=App(audio=False)
    yield instance
    instance.close()


def test_detection_migrates_enabled_and_respects_real_booleans():
    assert load_audio_underrun_detection() is True
    for value, expected in ((False,False),(True,True),('false',True),(0,True),(None,True)):
        save_preferences({'audio_underrun_detection':value})
        assert load_audio_underrun_detection() is expected


@pytest.mark.parametrize('page',['pattern','info','instrument','settings','orders','samples','help','files'])
def test_alt_f12_unique_global_binding(page):
    event=pg.event.Event(pg.KEYDOWN,key=pg.K_F12,mod=pg.KMOD_ALT,scancode=0,unicode='')
    assert dispatch(event,page).name=='audio_settings'
    assert match_event(event,page)['id']=='audio.settings'
    rules=[e['id'] for e in COMMANDS for rule in e.get('key_rules',[])
           if rule.get('key')=='K_F12' and set(rule.get('modifiers',[]))=={'alt'}]
    assert rules==['audio.settings']


def test_options_save_cancel_and_checkbox_do_not_edit_song(app):
    song=deepcopy(app.editor.song)
    open_dialog(app);app.dialog['detection']=False;activate(app,'cancel')
    assert app.audio_underrun_detection is True and not config_path().exists()
    open_dialog(app);app.renderer.render(app)
    rect=next(r for r,a,_ in app.renderer.hits if a=='audio_detection')
    app.handle(pg.event.Event(pg.MOUSEBUTTONDOWN,button=1,pos=rect.center))
    assert app.dialog['detection'] is False
    activate(app,'ok')
    assert app.audio_underrun_detection is False and load_audio_underrun_detection() is False
    assert app.editor.song==song
    assert json.loads(config_path().read_text())['audio_buffer']==2048


def test_warning_does_not_open_modal_change_focus_or_overwrite_editor_status(app,monkeypatch):
    app.editor.status='Editing stays visible'
    page=app.page
    app.audio.underruns=1;app.audio.missing_frames=2048
    app.update_audio_warning()
    assert app.dialog is None and app.page==page and app.editor.status=='Editing stays visible'
    assert 'Buffer underrun' in app.audio_warning and 'Alt+F12' in app.audio_warning
    texts=[];original=app.renderer.text
    def text(x,y,content,*a,**kw):
        texts.append((x,y,content));return original(x,y,content,*a,**kw)
    monkeypatch.setattr(app.renderer,'text',text)
    app.renderer.render(app)
    warning=next((x,y,s) for x,y,s in texts if 'Buffer underrun' in s)
    assert warning[0]==1 and warning[1]>=app.renderer.lines-3
    app.audio_warning_until=time.monotonic()-1;texts.clear();app.renderer.render(app)
    assert not any('Buffer underrun' in s for _,_,s in texts)


def test_disabled_detector_suppresses_notifications_and_keeps_diagnostics(app):
    app.audio_underrun_detection=False;app.audio.underruns=3;app.audio.late_callbacks=2
    app.update_audio_warning()
    assert not app.audio_warning and app.audio.underruns==3
    app.audio_underrun_detection=True;app.update_audio_warning()
    assert not app.audio_warning  # historical events do not flash on re-enable
    app.audio.late_callbacks=3;app.update_audio_warning()
    assert app.audio_warning.startswith('Late audio callback')


@pytest.mark.parametrize('size,zoom',[((480,360),3),((1280,900),1),((800,600),.5)])
def test_detection_checkbox_fits_audio_dialog(app,size,zoom):
    app.zoom=zoom
    app.handle(pg.event.Event(pg.VIDEORESIZE,w=size[0],h=size[1]))
    open_dialog(app);app.renderer.render(app)
    rect=next(r for r,a,_ in app.renderer.hits if a=='audio_detection')
    assert app.screen.get_rect().contains(rect)
    assert all(not rect.colliderect(other) for other,a,_ in app.renderer.hits if a=='buffer_button')
