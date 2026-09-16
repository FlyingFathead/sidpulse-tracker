"""Real pygame key-event routing tests (skip when pygame-ce is unavailable)."""
from copy import deepcopy
import pytest
pg = pytest.importorskip("pygame", reason="pygame-ce is needed for real SDL event tests")
from sidpulse.ui.keyboard import dispatch, NOTE_SCANCODES
from sidpulse.commands.editor import Editor
from sidpulse.song.model import Cell


def key(text, mod=0, scan=None):
    physical = 39 if text == "0" else 29 + int(text) if text in "123456789" and len(text) == 1 else 0
    return pg.event.Event(pg.KEYDOWN, key=ord(text) if len(text) == 1 else pg.K_UNKNOWN,
                          scancode=physical if scan is None else scan, mod=mod, unicode=text)


@pytest.mark.parametrize("digit", "0123456789")
def test_octave_slot_digits_take_priority_over_piano_scancodes(digit):
    command = dispatch(key(digit), "pattern", 1)
    assert command.name == "digit" and command.value == digit


@pytest.mark.parametrize("digit", "01234567")
def test_real_key_dispatch_plus_model_changes_octave_only(digit):
    e = Editor()
    e.pattern.rows[0][0] = Cell(63, 3, "H", 0x34)
    e.column = 1
    cmd = dispatch(key(digit), "pattern", e.column)
    assert cmd.name == "digit"
    e.enter_digit(cmd.value)
    assert e.pattern.rows[0][0] == Cell(12 * int(digit) + 3, 3, "H", 0x34)


@pytest.mark.parametrize("digit", "0123456789")
def test_numlock_keypad_uses_typed_digit(digit):
    event = key(digit, pg.KMOD_NUM, scan=98 if digit == "0" else 88 + int(digit))
    event.key = getattr(pg, "K_KP" + digit)
    assert dispatch(event, "pattern", 1).value == digit


def test_numlock_off_keypad_without_text_does_not_invent_octave():
    event = pg.event.Event(pg.KEYDOWN, key=pg.K_KP4, scancode=92, mod=0, unicode="")
    cmd = dispatch(event, "pattern", 1)
    assert cmd is None or (cmd.name == "digit" and cmd.value == "")


@pytest.mark.parametrize("digit", "0123456789")
def test_caps_lock_at_octave_slot_never_writes_a_digit(digit):
    event = key(digit, pg.KMOD_CAPS)
    cmd = dispatch(event, "pattern", 1)
    if event.scancode in NOTE_SCANCODES:
        assert cmd.name == "piano" and cmd.value[2] is True
    else:
        assert cmd is None


@pytest.mark.parametrize("digit", "0235679")
def test_note_name_slot_retains_black_key_and_extended_piano_notes(digit):
    event = key(digit)
    cmd = dispatch(event, "pattern", 0)
    assert cmd.name == "piano" and cmd.value[1] == NOTE_SCANCODES[event.scancode]


@pytest.mark.parametrize("digit,expected", [("1", "note"), ("4", "audition_cell"), ("8", "audition_row")])
def test_note_name_special_keys_are_unchanged(digit, expected):
    assert dispatch(key(digit), "pattern", 0).name == expected


@pytest.mark.parametrize("column", [2, 3, 7, 8])
def test_instrument_and_parameter_fields_keep_numeric_entry(column):
    cmd = dispatch(key("3"), "pattern", column)
    assert cmd.name == "digit" and cmd.value == "3"


def test_alt_digit_still_sets_skip_not_octave():
    cmd = dispatch(key("3", pg.KMOD_ALT), "pattern", 1)
    assert cmd.name == "skip" and cmd.value == 3


def test_shifted_numeric_text_on_other_layouts_and_shifted_symbols():
    assert dispatch(key("3", pg.KMOD_SHIFT), "pattern", 1).value == "3"
    cmd = dispatch(key("#", pg.KMOD_SHIFT, scan=32), "pattern", 1)
    assert cmd is None or (cmd.name == "digit" and cmd.value == "#")


def test_instrument_page_keeps_normal_number_piano_keys():
    cmd = dispatch(key("3"), "instrument", 1)
    assert cmd.name == "piano" and cmd.value[2] is True


def test_non_numeric_piano_key_still_works_at_octave_slot():
    cmd = dispatch(key("z", scan=29), "pattern", 1)
    assert cmd.name == "piano" and cmd.value[1] == 0


def test_key_release_remains_release():
    event = key("3")
    event = pg.event.Event(pg.KEYUP, **event.dict)
    assert dispatch(event, "pattern", 1).name == "release"
