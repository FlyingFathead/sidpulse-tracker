from copy import deepcopy
from sidpulse.commands.editor import Editor
from sidpulse.song.model import CUT, OFF, Cell


def test_note_specials_and_instrument_decimal_entry():
    e = Editor()
    e.enter_note(48)
    e.enter_note(OFF)
    e.enter_note(CUT)
    assert e.pattern.rows[0][0] == Cell(48, 1)
    assert e.pattern.rows[1][0].note == OFF
    e.row, e.column = 0, 2
    e.enter_digit("2")
    e.enter_digit("7")
    assert e.pattern.rows[0][0].instrument == 27
    assert 27 in e.song.instruments
    assert e.row == 1 and e.column == 2


def test_effect_nibbles_and_octave_column():
    e = Editor()
    e.enter_note(49)
    e.row, e.column = 0, 1
    e.enter_digit("5")
    assert e.pattern.rows[0][0].note == 61
    e.row, e.column = 0, 7
    e.enter_digit("H")
    e.row, e.column = 0, 8
    e.enter_digit("A")
    e.enter_digit("9")
    assert e.pattern.rows[0][0].effect == "H"
    assert e.pattern.rows[0][0].parameter == 0xA9


def test_insert_delete_channels_and_whole_rows():
    e = Editor()
    for v in range(3):
        e.pattern.rows[2][v] = Cell(48 + v, 1)
    original = deepcopy(e.song)
    e.row = 1
    e.insert_delete()
    assert e.pattern.rows[3][0].note == 48
    assert e.pattern.rows[2][1].note == 49
    e.history.undo(e.song)
    assert e.song == original
    e.insert_delete(entire=True)
    assert [c.note for c in e.pattern.rows[3]] == [48, 49, 50]
    e.insert_delete(delete=True, entire=True)
    assert e.song == original


def test_alt_mark_survives_movement_and_paste_semantics():
    e = Editor()
    e.pattern.rows[0][0] = Cell(48, 1)
    e.pattern.rows[1][0] = Cell(50, 1)
    e.mark("start")
    e.move(rows=1)
    e.mark("end")
    assert e.bounds() == (0, 1, 0, 0)
    e.copy()
    e.row = 4
    e.pattern.rows[4][0] = Cell(60, 2)
    e.paste("insert")
    assert [e.pattern.rows[r][0].note for r in range(4, 7)] == [48, 50, 60]
    e.history.undo(e.song)
    e.paste("overwrite")
    assert [e.pattern.rows[r][0].note for r in range(4, 7)] == [48, 50, None]
    e.history.undo(e.song)
    e.paste("mix")
    assert [e.pattern.rows[r][0].note for r in range(4, 6)] == [60, 50]


def test_transpose_clipboard_independence_and_redo():
    e = Editor()
    e.enter_note(48)
    e.row = 0
    e.copy()
    e.transpose(12)
    assert e.cell.note == 60
    assert e.clipboard[0][0].note == 48
    e.history.undo(e.song)
    assert e.cell.note == 48
    e.history.redo(e.song)
    assert e.cell.note == 60


def test_order_clone_and_undo_keep_patterns_independent():
    e = Editor()
    e.enter_note(48)
    before = deepcopy(e.song)
    e.order_edit("clone")
    assert e.song.orders == [1, 0]
    e.pattern.rows[0][0].note = 60
    assert e.song.patterns[0].rows[0][0].note == 48
    e.history.undo(e.song)
    e.repair_cursor()
    assert e.song == before
