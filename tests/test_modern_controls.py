from copy import deepcopy
import json

import pygame as pg
import pytest

from sidpulse.app import App
from sidpulse.preferences import config_path, load_keyboard_mapping, save_preferences
from sidpulse.ui.keyboard import Command, dispatch
from sidpulse.ui.pressable import pressed


def key(app, code, mods=0, text='', scan=0):
    app.handle(pg.event.Event(pg.KEYDOWN,key=code,mod=mods,unicode=text,scancode=scan))


def rect_for(app, action, value=None):
    app.renderer.render(app)
    return next(r for r,a,v in app.renderer.hits if a==action and v==value)


def click(app, action, value=None):
    rect=rect_for(app,action,value)
    app.handle(pg.event.Event(pg.MOUSEBUTTONDOWN,button=1,pos=rect.center))
    app.handle(pg.event.Event(pg.MOUSEBUTTONUP,button=1,pos=rect.center))


@pytest.fixture
def app():
    result=App(audio=False,size=(960,540))
    for row, pw in enumerate((0x100,0x200,0x300)):
        result.editor.pattern.rows[row][0].pulse_width=pw
        result.editor.pattern.rows[row][1].note=60+row
    result.editor.anchor=(0,0,13);result.editor.selection_end=(2,0,15)
    yield result
    result.close()


def test_modern_copy_paste_preserves_selected_pw_source_and_destination_notes(app):
    before=deepcopy(app.editor.song)
    key(app,pg.K_INSERT,pg.KMOD_CTRL)
    assert app.editor.song==before and app.clipboard_notice[0]=='Copied to clipboard'
    app.editor.row,app.editor.voice=0,1
    key(app,pg.K_INSERT,pg.KMOD_SHIFT)
    assert app.clipboard_notice[0]=='Pasted from clipboard'
    assert [r[1].pulse_width for r in app.editor.pattern.rows[:3]]==[0x100,0x200,0x300]
    assert [r[1].note for r in app.editor.pattern.rows[:3]]==[60,61,62]
    key(app,pg.K_BACKSPACE,pg.KMOD_CTRL)
    assert app.editor.song==before


def test_classic_keeps_roll_modern_has_alternate_roll_and_legacy_copy(app):
    app.set_keyboard_mapping('classic')
    key(app,pg.K_INSERT,pg.KMOD_CTRL)
    assert [r[0].pulse_width for r in app.editor.pattern.rows[:3]]==[0x300,0x100,0x200]
    key(app,pg.K_BACKSPACE,pg.KMOD_CTRL)
    app.set_keyboard_mapping('modern')
    key(app,pg.K_INSERT,pg.KMOD_CTRL|pg.KMOD_SHIFT)
    assert [r[0].pulse_width for r in app.editor.pattern.rows[:3]]==[0x300,0x100,0x200]
    key(app,pg.K_c,pg.KMOD_ALT)
    assert app.editor.clipboard and app.clipboard_notice[0]=='Copied to clipboard'


def test_keyboard_profile_dialog_cancel_save_reload_and_reset(app):
    before=deepcopy(app.editor.song)
    app.execute(Command('keyboard_mapping'));key(app,pg.K_ESCAPE)
    assert app.keyboard_mapping=='modern' and not config_path().exists()
    app.execute(Command('keyboard_mapping'));click(app,'dialog_button',pg.K_c)
    assert app.keyboard_mapping==load_keyboard_mapping()=='classic'
    assert json.loads(config_path().read_text())['keyboard_mapping']=='classic'
    app.close();other=App(audio=False)
    try:assert other.keyboard_mapping=='classic'
    finally:other.close()
    from sidpulse.ui.settings_reset import commit
    commit(app)
    assert app.keyboard_mapping==load_keyboard_mapping()=='modern'
    assert app.editor.song==before


@pytest.mark.parametrize('value',[None,0,False,[],{},'unknown','Modern'])
def test_invalid_keyboard_profile_falls_back_to_modern(value):
    save_preferences({'keyboard_mapping':value})
    assert load_keyboard_mapping()=='modern'


def test_profile_save_failure_keeps_old_mapping_and_dialog(app,monkeypatch):
    def fail(*args):raise OSError('Settings are read-only')
    monkeypatch.setattr('sidpulse.ui.pattern_clipboard.save_preferences',fail)
    app.open_keyboard_mapping();key(app,pg.K_c)
    assert app.keyboard_mapping=='modern' and 'read-only' in app.dialog['error']


def test_button_is_depressed_then_activates_once_on_release(app):
    rect=rect_for(app,'pattern_copy')
    raised=pg.image.tobytes(app.screen.subsurface(rect),'RGB')
    app.handle(pg.event.Event(pg.MOUSEBUTTONDOWN,button=1,pos=rect.center))
    assert app.editor.clipboard is None and pressed(app,'copy',False)
    app.renderer.render(app)
    assert pg.image.tobytes(app.screen.subsurface(rect),'RGB')!=raised
    app.handle(pg.event.Event(pg.MOUSEBUTTONUP,button=1,pos=rect.center))
    clipboard=app.editor.clipboard
    assert clipboard and app.clipboard_notice[0]=='Copied to clipboard'
    assert pressed(app,'copy',False)  # fast click remains visible briefly
    app.editor.pattern.rows[0][0].pulse_width=0x999
    app.handle(pg.event.Event(pg.MOUSEBUTTONUP,button=1,pos=rect.center))
    assert app.editor.clipboard is clipboard and clipboard[0][0].pulse_width==0x100


@pytest.mark.parametrize('cancel',['outside','focus','resize','page','escape'])
def test_button_cancel_never_changes_clipboard_or_song(app,cancel):
    before=deepcopy(app.editor.song);rect=rect_for(app,'pattern_copy')
    app.handle(pg.event.Event(pg.MOUSEBUTTONDOWN,button=1,pos=rect.center))
    if cancel=='outside':
        pos=(rect.right+10,rect.bottom+10)
        app.handle(pg.event.Event(pg.MOUSEMOTION,pos=pos,buttons=(1,0,0),rel=(10,10)))
        assert not pressed(app,'copy',False)
    else:
        pos=rect.center
        if cancel=='focus':app.handle(pg.event.Event(pg.WINDOWFOCUSLOST))
        elif cancel=='resize':app.handle(pg.event.Event(pg.VIDEORESIZE,w=800,h=600))
        elif cancel=='page':app.change_page('instrument')
        else:key(app,pg.K_ESCAPE)
    app.handle(pg.event.Event(pg.MOUSEBUTTONUP,button=1,pos=pos))
    assert app.editor.clipboard is None and app.editor.song==before


def test_empty_paste_and_special_show_feedback_and_special_success_uses_same_notice(app):
    click(app,'pattern_paste');assert app.clipboard_notice[0]=='Clipboard is empty'
    click(app,'paste_special');assert app.clipboard_notice[0]=='Clipboard is empty' and app.dialog is None
    click(app,'pattern_copy');app.editor.row,app.editor.voice=0,1
    click(app,'paste_special');assert app.dialog['kind']=='paste_special'
    click(app,'dialog_button',pg.K_a)
    assert app.clipboard_notice[0]=='Pasted from clipboard'
    assert app.editor.pattern.rows[0][1].pulse_width==0x100


@pytest.mark.parametrize('page',['instrument','samples'])
def test_modern_octave_keys_are_contextual_clamped_and_preserve_song(app,page):
    before=deepcopy(app.editor.song);app.change_page(page)
    for code,mods,text in [(pg.K_PLUS,0,'+'),(pg.K_EQUALS,pg.KMOD_SHIFT,'+'),(pg.K_KP_PLUS,0,'+')]:
        key(app,code,mods,text);assert app.editor.octave in range(5,8)
    assert app.editor.octave==7
    key(app,pg.K_PLUS,0,'+');assert app.editor.octave==7
    key(app,pg.K_KP_MINUS);assert app.editor.octave==6
    key(app,pg.K_0,text='0',scan=39);assert app.editor.octave==4
    for _ in range(8):key(app,pg.K_MINUS)
    assert app.editor.octave==0
    key(app,pg.K_KP0,pg.KMOD_NUM);assert app.editor.octave==4
    assert app.editor.song==before


def test_classic_zero_still_auditions_and_numeric_dialogs_keep_zero(app):
    app.set_keyboard_mapping('classic')
    ev=pg.event.Event(pg.KEYDOWN,key=pg.K_0,mod=0,scancode=39,unicode='0')
    assert dispatch(ev,'instrument',mapping='classic').name=='piano'
    app.set_keyboard_mapping('modern');app.change_page('instrument');app.editor.octave=6
    app.text_dialog('Number','',lambda value:None)
    key(app,pg.K_0,text='0',scan=39);app.handle(pg.event.Event(pg.TEXTINPUT,text='0'))
    assert app.dialog['text']=='0' and app.editor.octave==6
    app.dialog=None;app.change_page('pattern');app.editor.column=14
    key(app,pg.K_0,text='0',scan=39)
    assert app.editor.octave==6  # pattern numbers retain their existing meaning


@pytest.mark.parametrize('page',['pattern','instrument','samples'])
@pytest.mark.parametrize('size',[(960,540),(480,360)])
def test_octave_buttons_show_current_value_and_work_in_both_modes(app,page,size):
    app.screen=pg.display.set_mode(size);app.change_page(page);before=deepcopy(app.editor.song)
    for profile in ('modern','classic'):
        app.set_keyboard_mapping(profile);app.editor.octave=4
        for action,value,expected in [('octave',1,5),('octave_reset',None,4),('octave',-1,3)]:
            rect=rect_for(app,action,value)
            assert app.screen.get_rect().contains(rect)
            click(app,action,value);assert app.editor.octave==expected
    assert app.editor.song==before


def test_next_audition_note_uses_changed_octave_without_editing_instrument(app,monkeypatch):
    app.change_page('instrument');sent=[]
    monkeypatch.setattr(app.audio,'send',lambda *args:sent.append(args))
    before=deepcopy(app.editor.song)
    key(app,pg.K_PLUS,text='+');key(app,pg.K_z,text='z',scan=29)
    assert any(args[0]=='on' and args[2]==60 for args in sent)
    assert app.editor.song==before
