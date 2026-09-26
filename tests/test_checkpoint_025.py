from copy import deepcopy
import os
import pygame as pg
import pytest

from sidpulse.app import App
from sidpulse.project.format import encode, decode, save, load
from sidpulse.song.model import example_song, Instrument, Cell
from sidpulse.ui.dialogs import choices, focus
from sidpulse.ui.keyboard import Command, NOTE_SCANCODES
from sidpulse.ui.menus import menu_items
from sidpulse.preferences import save_preferences, load_file_browser_dates


def key(app,k,scan=0,text='',up=False):
    app.handle(pg.event.Event(pg.KEYUP if up else pg.KEYDOWN,key=k,scancode=scan,mod=0,unicode=text))


def click(app,action,value=None):
    app.renderer.render(app)
    r=next(r for r,a,v in app.renderer.hits if a==action and v==value)
    app.handle(pg.event.Event(pg.MOUSEBUTTONDOWN,button=1,pos=r.center))
    app.handle(pg.event.Event(pg.MOUSEBUTTONUP,button=1,pos=r.center))


@pytest.fixture
def app():
    a=App(example_song(),audio=False)
    yield a
    a.close()


@pytest.mark.parametrize('command',['new','clear_patterns','clear_instruments'])
@pytest.mark.parametrize('dirty',[False,True])
def test_destructive_commands_always_default_cancel(app,command,dirty):
    if dirty:app.editor.song.title='Changed title'
    before=deepcopy(app.editor.song)
    app.execute(Command(command))
    assert [label for label,_ in choices(app.dialog)]==['OK','Cancel']
    assert choices(app.dialog)[focus(app.dialog)][0]=='Cancel'
    key(app,pg.K_RETURN)
    assert app.dialog is None and app.editor.song==before
    app.execute(Command(command));key(app,pg.K_ESCAPE)
    assert app.editor.song==before


def test_clear_patterns_is_atomic_undo_and_keeps_other_banks(app):
    before=deepcopy(app.editor.song)
    app.execute(Command('clear_patterns'));click(app,'dialog_button',pg.K_y)
    for pid,pat in app.editor.song.patterns.items():
        assert len(pat.rows)==len(before.patterns[pid].rows)
        assert pat.name==before.patterns[pid].name and not pat.controls
        assert all(cell==Cell() for row in pat.rows for cell in row)
    expected=deepcopy(before);expected.patterns=app.editor.song.patterns
    assert app.editor.song==expected
    app.execute(Command('undo'));assert app.editor.song==before
    app.execute(Command('redo'));assert app.editor.song==expected


def test_empty_bank_roundtrip_all_pages_audition_and_restoration(app,tmp_path):
    from sidpulse.playback.sequencer import Sequencer
    from sidpulse.export.psid import compile_song, ExportError
    from sidpulse.sid.backend_residfp import ReSIDfpBackend
    before=deepcopy(app.editor.song)
    app.autosave.settings['autosave_directory']=str(tmp_path)
    app.execute(Command('clear_instruments'));click(app,'dialog_button',pg.K_y)
    assert choices(app.dialog)[focus(app.dialog)][0]=='Cancel'
    assert app.editor.song==before
    click(app,'dialog_button',pg.K_y)
    backups=list((tmp_path/'manual-backups').glob('before-clear-instruments-*.sidpulse'))
    assert len(backups)==1 and load(backups[0])[0]==before
    assert app.editor.song.instruments=={}
    expected=deepcopy(before);expected.instruments={}
    assert app.editor.song==expected
    path=save(tmp_path/'empty.sidpulse',app.editor.song)
    assert load(path)[0]==expected and encode(expected)['format_version']==6
    for page in ('pattern','instrument','info','settings','help','samples','orders'):
        app.change_page(page);app.renderer.render(app)
    app.change_page('pattern');app.execute(Command('piano',(29,0,True)))
    assert not app.held
    sid=ReSIDfpBackend();seq=Sequencer(sid);seq.start(expected)
    seq.render(48000)
    assert all(not sid.registers[v*7+4] & 0xf0 for v in range(3))
    with pytest.raises(ExportError,match='instrument bank is empty'):compile_song(expected)
    app.editor.song=deepcopy(expected)
    app.change_page('instrument');app.add_instrument(Instrument('Back again'),1)
    assert app.editor.song.instruments[1].name=='Back again'
    app.renderer.render(app)
    assert decode(encode(app.editor.song))[0]==app.editor.song
    app.execute(Command('undo'));assert app.editor.song==expected
    app.execute(Command('undo'));assert app.editor.song==before


@pytest.mark.parametrize('dirty',[False,True])
@pytest.mark.parametrize('window_close',[False,True])
def test_quit_always_asks_cancel_first(app,dirty,window_close):
    if dirty:app.editor.song.title='Unsaved'
    if window_close:app.handle(pg.event.Event(pg.QUIT))
    else:app.execute(Command('quit'))
    assert app.running
    assert 'Discard & Quit' in [label for label,_ in choices(app.dialog)]
    assert choices(app.dialog)[focus(app.dialog)][0]=='Cancel'
    key(app,pg.K_RETURN);assert app.running and app.dialog is None
    app.confirm_quit()
    click(app,'dialog_button',pg.K_d if dirty else pg.K_y)
    assert not app.running


@pytest.mark.parametrize('tab,index',[('general',0),('general',2),('adsr',2),('motion',9),('roll',0)])
def test_qwerty_auditions_across_parameter_focus(app,monkeypatch,tab,index):
    messages=[];monkeypatch.setattr(app.audio,'send',lambda *args:messages.append(args))
    app.change_page('instrument');app.choose_instrument_tab(tab);app.property_index=index
    before=deepcopy(app.editor.song)
    for scan in NOTE_SCANCODES:
        key(app,pg.K_b,scan,'b')
        assert app.dialog is None
        key(app,pg.K_b,scan,'b',up=True)
    assert len([m for m in messages if m[0]=='on'])==len(NOTE_SCANCODES)
    assert app.editor.song==before
    key(app,pg.K_RETURN);assert app.dialog is None
    if index==0:
        key(app,pg.K_LEFT);key(app,pg.K_RIGHT);assert app.dialog is None


def test_slider_and_label_do_not_open_text_input(app,monkeypatch):
    app.change_page('instrument');app.choose_instrument_tab('adsr')
    app.renderer.render(app)
    slider=next(r for r,a,d in app.renderer.hits if a=='graph_drag' and d['field']=='attack' and d['kind']=='slider')
    app.handle(pg.event.Event(pg.MOUSEBUTTONDOWN,button=1,pos=slider.center))
    key(app,pg.K_b,5,'b');assert app.dialog is None and 5 in app.held
    app.handle(pg.event.Event(pg.MOUSEBUTTONUP,button=1,pos=slider.center))
    click(app,'edit_instrument_field',2)
    assert 'text' in app.dialog and not app.held


def test_manual_preset_draft_uses_click_only_entry(app,monkeypatch):
    messages=[];monkeypatch.setattr(app.audio,'send',lambda *args:messages.append(args))
    app.open_presets();app.chooser_mode('manual');app.dialog['manual_index']=2
    key(app,pg.K_b,5,'b')
    assert 'text' not in app.dialog and messages[-1][0]=='on'
    key(app,pg.K_b,5,'b',up=True);key(app,pg.K_RETURN)
    assert 'text' not in app.dialog
    click(app,'edit_instrument_field',2)
    assert 'text' in app.dialog


def test_file_dates_default_toggle_and_cache(app,tmp_path):
    from datetime import datetime
    assert load_file_browser_dates() and app.file_browser_show_modified
    path=save(tmp_path/'a.sidpulse',app.editor.song)
    stamp=1700000000;os.utime(path,(stamp,stamp))
    app.file_dir=tmp_path;app.browse('open');app.renderer.render(app)
    assert app.file_modified[path]==datetime.fromtimestamp(stamp).strftime('%Y-%m-%d %H:%M')
    before=deepcopy(app.editor.song)
    app.change_page('settings');app.property_index=21;app.change_property(1)
    assert not app.file_browser_show_modified and not load_file_browser_dates()
    assert app.editor.song==before
    save_preferences({'file_browser_show_modified':'bad value'})
    assert load_file_browser_dates()


def test_file_menu_places_clear_buttons_below_new():
    assert [item.command for item in menu_items('File Menu')][:3]==['new','clear_patterns','clear_instruments']


def test_sequence_length_only_opens_from_value_click(app):
    app.change_page('instrument');app.choose_instrument_tab('roll')
    key(app,pg.K_RETURN)
    assert app.dialog is None
    click(app,'graph_length')
    assert app.dialog['title']=='Sequence length' and 'text' in app.dialog


@pytest.mark.parametrize('size',[(480,360),(980,780),(1440,1050)])
def test_confirmation_buttons_stay_visible_after_resize(app,size):
    app.handle(pg.event.Event(pg.VIDEORESIZE,w=size[0],h=size[1],size=size))
    app.execute(Command('clear_instruments'))
    app.renderer.render(app)
    buttons=[r for r,a,v in app.renderer.hits if a=='dialog_button']
    assert len(buttons)==2 and all(app.renderer.screen.get_rect().contains(r) for r in buttons)
    assert choices(app.dialog)[focus(app.dialog)][0]=='Cancel'


def test_f4_bulk_clear_two_cancel_default_steps_and_failed_backup(app,tmp_path,monkeypatch):
    app.change_page('instrument');app.renderer.render(app)
    assert any(action=='clear_instruments' for _,action,_ in app.renderer.hits)
    before=deepcopy(app.editor.song)
    click(app,'clear_instruments')
    click(app,'dialog_button',pg.K_y)
    key(app,pg.K_RETURN)
    assert app.dialog is None and app.editor.song==before
    app.autosave.settings['autosave_directory']=str(tmp_path)
    from sidpulse import app as app_module
    monkeypatch.setattr(app_module,'save',lambda *args: (_ for _ in ()).throw(OSError('disk unavailable')))
    app.execute(Command('clear_instruments'))
    click(app,'dialog_button',pg.K_y)
    click(app,'dialog_button',pg.K_y)
    assert app.editor.song==before and app.dialog['kind']=='notice'
    assert not list(tmp_path.rglob('*.sidpulse'))
