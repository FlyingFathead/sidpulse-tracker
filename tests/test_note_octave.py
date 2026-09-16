"""Octave-only edits: pure model/history tests, with no SDL dependency."""
from copy import deepcopy
import pytest
from sidpulse.commands.editor import Editor
from sidpulse.song.model import Cell, CUT, OFF
from sidpulse.project.format import load, save


def editor_with_note(note=63):
    e = Editor()
    e.pattern.rows[0][1] = Cell(note, 3, "H", 0x34)
    e.voice, e.column = 1, 1
    e.instrument = 4  # Deliberately different: no edit-mask injection allowed.
    e.edit_mask = {"note", "instrument", "effect"}
    e.last_cell = Cell(48, 2, "J", 0x47)
    e.octave, e.skip = 6, 2
    e.mark_saved()
    return e


@pytest.mark.parametrize("pitch_class", range(12))
@pytest.mark.parametrize("octave", range(8))
def test_digit_changes_only_octave_for_every_pitch_class(pitch_class, octave):
    e = editor_with_note(5 * 12 + pitch_class)
    expected = deepcopy(e.song)
    expected.patterns[0].rows[0][1].note = octave * 12 + pitch_class
    e.enter_digit(str(octave))
    assert e.song == expected
    assert (e.row, e.voice, e.column, e.octave, e.instrument) == (2, 1, 1, 6, 4)
    assert e.last_cell == expected.patterns[0].rows[0][1]


def test_screenshot_d_sharp_five_to_four_then_three_and_undo_redo():
    e = editor_with_note()
    e.skip = 0
    original = deepcopy(e.song)
    e.enter_digit("4")
    assert e.cell == Cell(51, 3, "H", 0x34)
    middle = deepcopy(e.song)
    e.enter_digit("3")
    assert e.cell == Cell(39, 3, "H", 0x34)
    assert len(e.history.undo_stack) == 2
    e.history.undo(e.song)
    assert e.song == middle
    e.history.undo(e.song)
    assert e.song == original and not e.dirty
    e.history.redo(e.song)
    assert e.song == middle


@pytest.mark.parametrize("note", [None, OFF, CUT])
def test_digits_do_not_invent_pitches_for_blank_release_or_cut(note):
    e = editor_with_note(note)
    before = deepcopy(e.song)
    last = deepcopy(e.last_cell)
    e.enter_digit("4")
    assert e.song == before and e.last_cell == last
    assert e.row == 0 and not e.history.undo_stack
    assert "pitched note" in e.status


@pytest.mark.parametrize("text", ["8", "9"])
def test_out_of_range_octave_is_rejected_without_mutation_or_advance(text):
    e = editor_with_note()
    before = deepcopy(e.song)
    e.enter_digit(text)
    assert e.song == before and not e.dirty
    assert e.row == 0 and not e.history.undo_stack
    assert "0..7" in e.status


@pytest.mark.parametrize("text", ["", "04", "-1", "a", "\u0664"])
def test_non_ascii_or_multi_character_input_is_not_an_octave(text):
    e = editor_with_note()
    before = deepcopy(e.song)
    e.enter_digit(text)
    assert e.song == before and e.row == 0


def test_same_octave_uses_skip_but_does_not_add_spurious_undo():
    e = editor_with_note()
    e.enter_digit("5")
    assert not e.history.undo_stack and not e.dirty
    assert e.row == 2


def test_existing_row_skip_wrap_is_retained():
    e = editor_with_note()
    e.pattern.rows[-1][1] = Cell(63, 3)
    e.row = len(e.pattern.rows) - 1
    e.enter_digit("4")
    assert e.pattern.rows[-1][1].note == 51 and e.row == 1


def test_selection_and_repeat_last_note_do_not_revert_octave():
    e = editor_with_note()
    e.anchor, e.selection_end = (0, 0), (10, 2)
    before = deepcopy(e.song)
    e.enter_digit("3")
    expected = deepcopy(before)
    expected.patterns[0].rows[0][1].note = 39
    assert e.song == expected  # Selection is not implicitly transposed.
    assert (e.anchor, e.selection_end) == ((0, 0), (10, 2))
    e.repeat_field()
    assert e.pattern.rows[2][1].note == 39


def test_octave_edit_survives_native_save_load(tmp_path):
    e = editor_with_note()
    e.enter_digit("4")
    path = save(tmp_path / "octave.sidpulse", e.song, {"pattern_grid": {"rows_per_beat": 12, "beats_per_bar": 4}})
    song, metadata = load(path)
    assert song == e.song and song.patterns[0].rows[0][1].note == 51
    assert metadata["pattern_grid"]["rows_per_beat"] == 12


def test_export_limit_keeps_actionable_instruction_and_refusal():
    from sidpulse.export.psid import ExportMemoryError
    error = ExportMemoryError(512, 30000, 8000)
    assert "Shorten or simplify the project and try again." in str(error)
    assert ".sidpulse is unchanged" in str(error)
    assert "future compact player" not in str(error)
    assert error.required_bytes == 38512 and error.budget_bytes == 36864
