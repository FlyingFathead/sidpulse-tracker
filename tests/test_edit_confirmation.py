from copy import deepcopy
import json
import pygame as pg
import pytest

from sidpulse.app import App
from sidpulse.preferences import config_path, load_confirm_cut, load_instrument_monitor_buttons, save_preferences
from sidpulse.song.model import Cell
from sidpulse.ui.keyboard import Command
from sidpulse.ui.menus import menu_items


def key(app, code, mod=0):
    app.handle(pg.event.Event(pg.KEYDOWN,key=code,mod=mod,unicode='',scancode=0))


def click(app, action, value=None):
    app.renderer.render(app)
    rect = next(r for r,a,v in app.renderer.hits if (a,v)==(action,value))
    app.handle(pg.event.Event(pg.MOUSEBUTTONDOWN,button=1,pos=rect.center))
    app.handle(pg.event.Event(pg.MOUSEBUTTONUP,button=1,pos=rect.center))


@pytest.fixture
def app():
    result=App(audio=False,size=(960,540))
    result.editor.pattern.rows[0][0]=Cell(48,1,'H',0x23,attack=3,pulse_width=0x456)
    result.editor.pattern.rows[1][0]=Cell(50,1,pulse_width=0x789)
    result.editor.anchor=(0,0,13);result.editor.selection_end=(1,0,15)
    yield result
    result.close()


@pytest.mark.parametrize('operation',['pattern_cut','reset_automation'])
def test_default_enter_cancels_without_song_clipboard_history_or_preference_changes(app,operation):
    before=deepcopy(app.editor.song);revision=app.editor.history.revision
    app.editor.copy();clipboard=deepcopy(app.editor.clipboard)
    app.follow_playback=True
    click(app,operation)
    assert not app.follow_playback and app.dialog['button_focus']==1
    key(app,pg.K_RETURN)
    assert app.dialog is None and app.editor.song==before
    assert app.editor.history.revision==revision and app.editor.clipboard==clipboard
    assert not config_path().exists()


def test_cut_checkbox_cancel_does_not_disable_confirmation_and_confirm_is_undoable(app):
    before=deepcopy(app.editor.song)
    click(app,'pattern_cut');click(app,'cut_confirmation_checkbox')
    key(app,pg.K_ESCAPE)
    assert app.confirm_cut and load_confirm_cut()
    click(app,'pattern_cut')
    assert not app.dialog['skip_next_time']
    # From Cancel, Tab focuses the checkbox; Space toggles it without cutting.
    key(app,pg.K_TAB);key(app,pg.K_SPACE)
    assert app.dialog['skip_next_time'] and app.editor.song==before
    click(app,'dialog_button',pg.K_y)
    assert app.dialog is None and not app.confirm_cut and not load_confirm_cut()
    assert [r[0].pulse_width for r in app.editor.pattern.rows[:2]]==[None,None]
    assert [r[0].note for r in app.editor.pattern.rows[:2]]==[48,50]
    assert app.editor.pattern.rows[0][0].attack==3
    assert [r[0].pulse_width for r in app.editor.clipboard]==[0x456,0x789]
    assert len(app.editor.history.undo_stack)==1
    app.execute(Command('undo'));assert app.editor.song==before
    key(app,pg.K_z,pg.KMOD_ALT)
    assert app.dialog is None and app.clipboard_notice[0]=='Cut to clipboard'
    from sidpulse.ui.settings_reset import commit
    commit(app)
    assert app.confirm_cut and load_confirm_cut()


def test_cut_preference_failure_is_non_destructive(app,monkeypatch):
    before=deepcopy(app.editor.song)
    click(app,'pattern_cut');click(app,'cut_confirmation_checkbox')
    def fail(*args):raise OSError('read-only')
    monkeypatch.setattr('sidpulse.ui.edit_confirmation.save_preferences',fail)
    click(app,'dialog_button',pg.K_y)
    assert 'read-only' in app.dialog['error'] and app.confirm_cut
    assert app.editor.song==before and app.editor.clipboard is None


def test_changed_target_cannot_be_cut_under_old_confirmation(app):
    before=deepcopy(app.editor.song)
    app.copy_fields(True);app.editor.voice=1
    key(app,pg.K_y)
    assert app.editor.song==before and app.editor.clipboard is None
    assert 'Selection changed' in app.clipboard_notice[0]


@pytest.mark.parametrize('value',[None,1,'false',[],{}])
def test_invalid_preferences_keep_confirm_and_monitor_enabled(value):
    save_preferences({'confirm_cut':value,'instrument_monitor_buttons':value})
    assert load_confirm_cut() and load_instrument_monitor_buttons()


def test_monitor_toggle_hides_both_banks_and_bypasses_only_instrument_mutes(app,monkeypatch):
    sent=[];monkeypatch.setattr(app.audio,'send',lambda *args:sent.append(args))
    app.muted=[False,True,False];app.muted_instruments={1};app.solo_instrument=1
    before=deepcopy(app.editor.song)
    app.execute(Command('instrument_monitor_buttons'))
    assert not load_instrument_monitor_buttons()
    assert sent[-1]==('instrument_monitor',(),None)
    for page in ('instrument','samples'):
        app.change_page(page);app.renderer.render(app)
        assert not any(a in ('instrument_mute','instrument_solo','bank_monitor_disabled') for _,a,_ in app.renderer.hits)
    app.execute(Command('instrument_mute',1))
    assert app.muted_instruments=={1}
    app.execute(Command('instrument_monitor_buttons'))
    assert sent[-1]==('instrument_monitor',(1,),1)
    assert app.muted==[False,True,False] and app.editor.song==before
    app.renderer.render(app)
    assert any(a=='bank_monitor_disabled' for _,a,_ in app.renderer.hits)


def test_ui_submenu_exists_and_mouse_keeps_parent_latched(app,monkeypatch):
    app.screen=pg.display.set_mode((1280,900))
    app.open_menu('Settings Menu')
    index=next(i for i,e in enumerate(menu_items('Settings Menu')) if e.value=='UI Settings')
    click(app,'menu',index)
    assert app.menu_path==['Settings Menu','UI Settings'] and app.menu_indices[-2]==index
    import sidpulse.ui.renderer as module
    original=module.button_frame;frames=[]
    def frame(r,rect,selected=False,fill=None):
        frames.append(selected);return original(r,rect,selected,fill)
    monkeypatch.setattr(module,'button_frame',frame)
    app.renderer.configure(app.screen,app.zoom,app.appearance);app.renderer.menu(app)
    assert frames[index] and sum(frames)==2
    assert any(e.command=='instrument_monitor_buttons' for e in menu_items('UI Settings'))
