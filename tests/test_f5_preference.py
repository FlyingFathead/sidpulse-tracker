from copy import deepcopy
from dataclasses import replace
import json
import pygame as pg
import pytest
from sidpulse.app import App
from sidpulse.preferences import config_path,load_restart_on_f5,save_preferences
from sidpulse.ui.keyboard import Command
from test_checkpoint_026 import key,click


@pytest.mark.parametrize('state',['stopped','playing','paused'])
@pytest.mark.parametrize('enabled',[False,True])
@pytest.mark.parametrize('force',[False,True])
def test_f5_restart_policy_and_ctrl_override(monkeypatch,state,enabled,force):
    save_preferences({'restart_on_f5':enabled})
    app=App(audio=False)
    try:
        app.audio.ready=True
        app.audio.playback=replace(app.audio.playback,status=state,frames=120000,order=2,row=20)
        before=deepcopy(app.editor.song)
        calls=[];monkeypatch.setattr(app.audio,'send',lambda *args:calls.append(args))
        key(app,pg.K_F5,mod=pg.KMOD_CTRL if force else 0)
        plays=[c for c in calls if c[0]=='play']
        assert len(plays)==int(force or enabled or state=='stopped')
        if plays: assert plays[0][2:]==('song',0,0,None)
        assert app.page=='info' and app.editor.song==before
        assert app.audio.playback.frames==120000
    finally:app.close()


def test_restart_preference_defaults_and_bad_values():
    assert not load_restart_on_f5()
    for value in ('true',1,None,[],{}):
        save_preferences({'restart_on_f5':value})
        assert not load_restart_on_f5()
    config_path().write_text('bad json')
    assert not load_restart_on_f5()


def test_setting_click_and_keyboard_persist_without_changing_song():
    save_preferences({'audio_buffer':2048})
    app=App(audio=False)
    try:
        before=deepcopy(app.editor.song)
        app.execute(Command('f5_restart_settings'))
        assert app.page=='settings' and app.property_index==23 and not app.restart_on_f5
        click(app,'setting_edit',23)
        assert app.restart_on_f5 and load_restart_on_f5() and app.dialog is None
        assert json.loads(config_path().read_text())['audio_buffer']==2048
        key(app,pg.K_RETURN)
        assert not app.restart_on_f5 and not load_restart_on_f5()
        key(app,pg.K_RIGHT)
        assert app.restart_on_f5 and app.editor.song==before and not app.editor.dirty
    finally:app.close()
    reopened=App(audio=False)
    try:assert reopened.restart_on_f5
    finally:reopened.close()
