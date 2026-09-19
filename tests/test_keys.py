import pygame as pg
import pytest
from sidpulse.ui.keyboard import dispatch


def key(sym, scan=0, mod=0, text="", up=False):
    return pg.event.Event(pg.KEYUP if up else pg.KEYDOWN, key=sym, scancode=scan, mod=mod, unicode=text)


@pytest.mark.parametrize("scan,offset", [(29, 0), (22, 1), (27, 2), (16, 11), (20, 12), (31, 13), (12, 24), (19, 28)])
def test_schism_physical_piano(scan, offset):
    # Symbol deliberately unrelated: note input must follow physical position.
    command = dispatch(key(pg.K_a, scan))
    assert command.name == "piano"
    assert command.value[1] == offset


def test_reserved_and_schism_commands_are_not_hijacked():
    assert dispatch(key(pg.K_PERIOD, 55)).name == "clear"
    assert dispatch(key(pg.K_COMMA, 54)).name == "mask"
    assert dispatch(key(pg.K_c, mod=pg.KMOD_CTRL)).name == "center"
    assert dispatch(key(pg.K_c, mod=pg.KMOD_ALT)).name == "copy"
    assert dispatch(key(pg.K_p, mod=pg.KMOD_ALT)).value == "insert"
    assert dispatch(key(pg.K_o, mod=pg.KMOD_ALT)).value == "overwrite"
    assert dispatch(key(pg.K_BACKSPACE, mod=pg.KMOD_CTRL)).name == "undo"
    assert dispatch(key(pg.K_KP_PLUS, mod=pg.KMOD_CTRL)).name == "order_pattern"
    assert dispatch(key(pg.K_MINUS, mod=pg.KMOD_CTRL | pg.KMOD_ALT)).name == "zoom"
    assert dispatch(key(pg.K_z, mod=pg.KMOD_CTRL)).name == "pending"


def test_note_off_finnish_and_caps_preview():
    assert dispatch(key(pg.K_UNKNOWN, 53)).value == -1
    assert dispatch(key(pg.K_1, 30)).value == -2
    assert dispatch(key(pg.K_z, 29, pg.KMOD_CAPS)).value[2] is True
    assert dispatch(key(pg.K_z, 29, up=True)).name == "release"
    assert dispatch(key(pg.K_z, 29), "instrument").value[2] is True


def test_shift_selection_moves_one_field_digit():
    cmd = dispatch(key(pg.K_RIGHT, mod=pg.KMOD_SHIFT))
    assert cmd.value == (0, 1, True)


def test_non_note_columns_do_not_jazz():
    assert dispatch(key(pg.K_a, 4, text="a"), column=7).name == "digit"
    assert dispatch(key(pg.K_2, 31, text="2"), column=2).name == "digit"
