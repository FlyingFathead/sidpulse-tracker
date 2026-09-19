from copy import deepcopy
from dataclasses import replace
import json

import pygame as pg
import pytest

from sidpulse.app import App
from sidpulse.commands.editor import Editor
from sidpulse.commands.pattern_fields import AUTOMATION_FIELDS
from sidpulse.preferences import config_path
from sidpulse.song.model import Cell, Song
from sidpulse.ui.keyboard import Command, dispatch


def source_editor():
    ed = Editor()
    for r in range(8):
        ed.pattern.rows[r][0] = Cell(48+r,1,'J',0x37,pulse_width=(None,0,-1,0xFFF)[r%4],attack=r,release=15-r)
        ed.pattern.rows[r][1] = Cell(60+r,2,'H',0x34,pulse_width=0x800,sustain=12,
                                    _extra_fields={'future':{'keep':r}})
    return ed


def select(ed, first, last):
    ed.anchor, ed.selection_end = first,last
    ed.row,ed.voice,ed.column = last


def test_copy_pw_to_other_channel_at_note_cursor_preserves_every_other_field_and_undo():
    ed=source_editor();before=deepcopy(ed.song)
    select(ed,(0,0,14),(3,0,14));ed.copy()
    assert ed.clipboard_fields == (frozenset(('pulse_width',)),)
    assert ed.clipboard[0][0].note is None
    ed.row,ed.voice,ed.column=0,1,0;ed.paste()
    for r in range(4):
        assert ed.pattern.rows[r][1] == replace(before.patterns[0].rows[r][1],pulse_width=before.patterns[0].rows[r][0].pulse_width)
    ed.history.undo(ed.song);assert ed.song==before
    ed.history.redo(ed.song);assert ed.pattern.rows[1][1].pulse_width==0


@pytest.mark.parametrize('scope,fields',[('notes',{'note'}),('automation',AUTOMATION_FIELDS),('both',AUTOMATION_FIELDS|{'note'})])
def test_paste_special_filters_whole_channel_copy(scope,fields):
    ed=source_editor();before=deepcopy(ed.song)
    ed.mark('start');ed.row=3;ed.mark('end');ed.copy()
    ed.row,ed.voice=0,1;ed.paste(scope=scope)
    for r in range(4):
        expected=replace(before.patterns[0].rows[r][1],**{f:getattr(before.patterns[0].rows[r][0],f) for f in fields})
        assert ed.pattern.rows[r][1]==expected


def test_paste_special_cannot_restore_data_outside_copied_selection():
    ed=source_editor();select(ed,(0,0,13),(3,0,15));ed.copy()
    before=deepcopy(ed.song);ed.row,ed.voice=0,1
    ed.paste(scope='notes');assert ed.song==before and 'no fields matching' in ed.status
    ed.paste(scope='both');assert ed.pattern.rows[0][1].note==60
    assert ed.pattern.rows[0][1].attack is None


def test_note_name_and_octave_are_one_copy_unit_in_reverse_selection():
    ed=source_editor();select(ed,(3,0,1),(0,0,1));ed.copy()
    before=deepcopy(ed.song);ed.row,ed.voice=0,1;ed.paste()
    for r in range(4):assert ed.pattern.rows[r][1]==replace(before.patterns[0].rows[r][1],note=48+r)


def test_multi_voice_selection_keeps_distinct_edge_fields():
    ed=source_editor();select(ed,(1,1,0),(0,0,14));ed.copy()
    assert ed.clipboard_fields==(frozenset(('pulse_width',)),frozenset(('note',)))
    ed.row,ed.voice=4,1;before=deepcopy(ed.song);ed.paste()
    for r in range(2):
        assert ed.pattern.rows[r+4][1]==replace(before.patterns[0].rows[r+4][1],pulse_width=before.patterns[0].rows[r][0].pulse_width)
        assert ed.pattern.rows[r+4][2]==Cell(note=before.patterns[0].rows[r][1].note)


def test_insert_paste_shifts_only_selected_automation_lanes():
    ed=source_editor();select(ed,(0,0,9),(1,0,15));ed.copy()
    before=deepcopy(ed.song);ed.row,ed.voice=2,1;ed.paste('insert')
    for r in range(len(ed.pattern.rows)):
        old=before.patterns[0].rows[r][1]
        src=(before.patterns[0].rows[r-2][0] if 2<=r<4 else before.patterns[0].rows[r-2][1] if r>=4 else old)
        assert ed.pattern.rows[r][1]==replace(old,**{f:getattr(src,f) for f in AUTOMATION_FIELDS})
    ed.history.undo(ed.song);assert ed.song==before


def test_cut_and_roll_automation_never_touch_notes_effects_or_extension_data():
    ed=source_editor();select(ed,(0,1,9),(3,1,15));before=deepcopy(ed.song)
    ed.copy(cut=True)
    for r in range(4):assert ed.pattern.rows[r][1]==replace(before.patterns[0].rows[r][1],**dict.fromkeys(AUTOMATION_FIELDS))
    ed.history.undo(ed.song);assert ed.song==before
    ed.roll(1)
    for r in range(4):assert ed.pattern.rows[r][1]==replace(before.patterns[0].rows[r][1],**{f:getattr(before.patterns[0].rows[(r-1)%4][1],f) for f in AUTOMATION_FIELDS})
    ed.history.undo(ed.song);ed.transpose(12);ed.set_block_instrument();assert ed.song==before


def test_mix_fills_empty_fields_but_keeps_explicit_zero_reset_and_fx_pair():
    ed=source_editor();select(ed,(0,0,6),(3,0,15));ed.copy()
    ed.pattern.rows[0][1]=Cell(60,2,'',None,pulse_width=None)
    ed.pattern.rows[1][1].pulse_width=0
    ed.pattern.rows[2][1].pulse_width=-1
    ed.row,ed.voice=0,1;ed.paste('mix')
    assert ed.pattern.rows[0][1].effect=='J' and ed.pattern.rows[0][1].parameter==0x37
    assert ed.pattern.rows[1][1].effect=='H' and ed.pattern.rows[1][1].parameter==0x34
    assert ed.pattern.rows[1][1].pulse_width==0 and ed.pattern.rows[2][1].pulse_width==-1
    assert ed.pattern.rows[0][1].note==60


def test_field_copy_survives_pattern_change_and_clips_at_destination_end():
    ed=source_editor();select(ed,(0,0,13),(3,0,15));ed.copy();ed.select_pattern(1)
    ed.row,ed.voice=63,2;ed.paste();assert ed.pattern.rows[63][2].pulse_width is None
    ed.row=62;ed.paste();assert ed.pattern.rows[63][2].pulse_width==0


@pytest.fixture
def app():
    instance=App(source_editor().song,audio=False)
    instance.renderer.render(instance)
    yield instance
    instance.close()


def click(app, action, value=None):
    app.renderer.render(app)
    rect=next(r for r,a,v in app.renderer.hits if a==action and (value is None or v==value))
    app.handle(pg.event.Event(pg.MOUSEBUTTONDOWN,button=1,pos=rect.center))
    app.handle(pg.event.Event(pg.MOUSEBUTTONUP,button=1,pos=rect.center))


def key(app,sym,mod=0):
    app.handle(pg.event.Event(pg.KEYDOWN,key=sym,mod=mod,scancode=0,unicode=''))


def test_mouse_drag_copy_button_and_paste_button_only_transfer_pw(app):
    first=next(r for r,a,v in app.renderer.hits if a=='cell' and v==(0,0,14))
    last=next(r for r,a,v in app.renderer.hits if a=='cell' and v==(3,0,14))
    app.handle(pg.event.Event(pg.MOUSEBUTTONDOWN,button=1,pos=first.center))
    app.handle(pg.event.Event(pg.MOUSEMOTION,pos=last.center,buttons=(1,0,0),rel=(0,0)))
    app.handle(pg.event.Event(pg.MOUSEBUTTONUP,button=1,pos=last.center))
    assert app.editor.bounds()==(0,3,0,0) and app.editor.selected_fields(0)=={'pulse_width'}
    click(app,'pattern_copy');before=deepcopy(app.editor.song)
    click(app,'cell',(0,1,0));click(app,'pattern_paste')
    for r in range(4):assert app.editor.pattern.rows[r][1]==replace(before.patterns[0].rows[r][1],pulse_width=before.patterns[0].rows[r][0].pulse_width)


def test_header_and_keyboard_selection_then_paste_special_mouse_and_escape(app):
    click(app,'select_field',(0,13));assert app.editor.bounds()==(0,63,0,0)
    key(app,pg.K_c,pg.KMOD_ALT);click(app,'cell',(0,1,0))
    key(app,pg.K_v,pg.KMOD_CTRL|pg.KMOD_SHIFT);assert app.dialog['kind']=='paste_special'
    before=deepcopy(app.editor.song);key(app,pg.K_ESCAPE);assert app.editor.song==before
    key(app,pg.K_v,pg.KMOD_CTRL|pg.KMOD_SHIFT);click(app,'dialog_button',pg.K_a)
    assert app.editor.pattern.rows[3][1].pulse_width==0xFFF and app.editor.pattern.rows[3][1].note==63
    click(app,'cell',(0,0,9));key(app,pg.K_DOWN,pg.KMOD_SHIFT);key(app,pg.K_RIGHT,pg.KMOD_SHIFT)
    assert app.editor.bounds()==(0,1,0,0) and app.editor.selected_fields(0)=={'attack','decay'}
    assert dispatch(pg.event.Event(pg.KEYDOWN,key=pg.K_c,mod=pg.KMOD_CTRL,scancode=0,unicode='')).name=='center'


def test_drag_scrolls_beyond_visible_rows_and_releases_on_focus_loss(app):
    rect=next(r for r,a,v in app.renderer.hits if a=='cell' and v==(0,0,13))
    app.handle(pg.event.Event(pg.MOUSEBUTTONDOWN,button=1,pos=rect.center))
    initial=app.renderer.pattern_geometry['last_row']
    for _ in range(4):
        app.pattern_drag['scroll_time']=0
        app.update_pattern_selection((rect.centerx,app.renderer.pattern_geometry['bottom']+10),scroll=True)
        app.renderer.render(app)
    assert app.editor.row>initial and app.editor.selected_fields(0)=={'pulse_width'}
    app.handle(pg.event.Event(pg.WINDOWFOCUSLOST));assert app.pattern_drag is None


def test_buttons_hide_and_persist_without_dirtying_song(app):
    before=deepcopy(app.editor.song)
    app.page='settings';app.property_index=26;app.change_property(1)
    assert not app.pattern_clipboard_buttons
    assert json.loads(config_path().read_text())['pattern_clipboard_buttons'] is False
    app.change_page('pattern');app.renderer.render(app)
    assert not any(a.startswith('pattern_copy') or a=='paste_special' for _,a,_ in app.renderer.hits)
    assert app.editor.song==before and not app.editor.dirty
