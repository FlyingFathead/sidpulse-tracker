"""Filename caret/selection behaviour without a GUI or external dependency."""
import pytest
from sidpulse.ui.text_edit import TextEdit
from sidpulse.ui.file_browser import filename_caret


def editor(text='Broken_Machine_v21.sidpulse'):
    return TextEdit(text, filename_caret(text))


def test_default_caret_changes_only_revision_digit():
    e = editor()
    assert e.selected_text == ''
    e.delete(backwards=True);e.insert('2')
    assert e.text == 'Broken_Machine_v22.sidpulse'


def test_middle_insert_delete_and_home_end_preserve_other_characters():
    e = editor();original = e.text
    e.move_to(0);e.insert('A_');e.move_to(2);e.delete(backwards=True);e.delete(backwards=True)
    assert e.text == original
    e.move_to(original.index('21'));e.delete();e.insert('3')
    assert e.text == 'Broken_Machine_v31.sidpulse'
    e.move_to(len(e.text));assert e.caret == len(e.text)


@pytest.mark.parametrize('backwards', [False, True])
def test_delete_selection_and_collapse_without_mutation(backwards):
    e = editor('name_01.sidpulse');e.move_to(5);e.move_to(7,True)
    assert e.selected_text == '01'
    e.delete(backwards);assert e.text == 'name_.sidpulse' and e.caret == 5
    e = editor('name_01.sidpulse');e.move_to(5);e.move_to(7,True)
    e.move(-1 if backwards else 1)
    assert e.text == 'name_01.sidpulse' and e.caret == (5 if backwards else 7)
    assert e.anchor is None


def test_shift_selection_replace_not_whole_name():
    e = editor('Suho_verse21.sidpulse');e.move(-1,select=True);e.move(-1,select=True)
    assert e.selected_text == '21'
    e.insert('22');assert e.text == 'Suho_verse22.sidpulse'


def test_select_all_and_clipboard_control_sanitization():
    e = editor();e.select_all();e.insert('ääkköset 演奏\n\r\x00\t.sidpulse')
    assert e.text == 'ääkköset 演奏.sidpulse' and e.anchor is None


def test_empty_paste_does_not_delete_selection():
    e = editor();before=e.text;e.select_all();e.insert('');e.insert('\x00\n')
    assert e.text == before


def test_word_navigation_and_delete():
    e=editor('song_verse_002.sidpulse');e.move(-1,word=True)
    assert e.text[e.caret:].startswith('002.')
    e.move_to(filename_caret(e.text));e.delete(backwards=True,word=True)
    assert e.text=='song_verse_.sidpulse'
    e.move_to(0);e.delete(word=True);assert e.text=='verse_.sidpulse'


@pytest.mark.parametrize('width',[1,2,8,18,50])
@pytest.mark.parametrize('position',[0,1,5,15,30,120])
def test_long_value_scroll_caret_and_click(width,position):
    e=editor('a'*100+'_v01.sidpulse');e.move_to(position)
    text,col,selection=e.view(width)
    assert 0<=col<width and len(text)<=width and e.scroll+col==e.caret
    e.click(col);assert e.caret==min(position,len(e.text))


def test_scrolled_selection_clipping():
    e=editor('a'*60+'.sidpulse');e.select_all();text,cursor,(lo,hi)=e.view(10)
    assert 0<=lo<=hi<=10 and cursor<10 and len(text)<=10
    e.move_to(0);assert e.view(10)[1]==0 and e.scroll==0


def test_backspace_and_delete_at_edges_are_noops():
    e=editor('x');e.move_to(0);e.delete(True);assert e.text=='x'
    e.move_to(1);e.delete();assert e.text=='x'
    e.select_all();e.delete();e.delete(True);e.delete();assert e.text=='' and e.caret==0
