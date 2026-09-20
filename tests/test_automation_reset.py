from copy import deepcopy
import pygame as pg
import pytest

from sidpulse.app import App
from sidpulse.song.model import ENVELOPE_FIELDS

AUTOMATION_FIELDS = (*ENVELOPE_FIELDS, 'pulse_width')
from sidpulse.project.format import decode, encode
from sidpulse.song.model import Cell
from sidpulse.ui.keyboard import Command


def key(app, code, text='', mod=0, scan=0):
    app.handle(pg.event.Event(pg.KEYDOWN, key=code, unicode=text, mod=mod, scancode=scan))


@pytest.fixture
def app():
    app = App(audio=False)
    app.editor.pattern.rows[0][0] = Cell(48, 1, 'H', 0x23, attack=2, decay=3, sustain=4, release=5,
                                       pulse_width=0x456, _extra_fields={'future': 7})
    app.editor.column = 14
    yield app
    app.close()


def test_r_ra_are_transient_and_ral_commits_one_undoable_reset(app):
    before = deepcopy(app.editor.song)
    document = encode(before)
    revision = app.editor.history.revision
    key(app, pg.K_r, 'r')
    assert app.pattern_reset_entry[1] == 'R'
    key(app, pg.K_a, 'a')
    assert app.pattern_reset_entry[1] == 'RA'
    assert app.editor.song == before and encode(app.editor.song) == document
    assert app.editor.history.revision == revision
    key(app, pg.K_l, 'l')
    cell = app.editor.pattern.rows[0][0]
    assert all(getattr(cell, f) == -1 for f in AUTOMATION_FIELDS)
    assert (cell.note, cell.instrument, cell.effect, cell.parameter, cell._extra_fields) == (48, 1, 'H', 0x23, {'future': 7})
    assert app.editor.row == 1 and app.editor.column == 14
    assert app.editor.history.revision == revision + 1 and app.pattern_reset_entry is None
    loaded, _ = decode(encode(app.editor.song))
    assert loaded == app.editor.song
    app.execute(Command('undo'))
    assert app.editor.song == before


@pytest.mark.parametrize('cancel', ['escape', 'move', 'page', 'focus', 'mouse', 'menu'])
def test_partial_reset_cancel_never_changes_song(app, cancel):
    before = deepcopy(app.editor.song)
    key(app, pg.K_r, 'r'); key(app, pg.K_a, 'a')
    if cancel == 'escape': key(app, pg.K_ESCAPE)
    elif cancel == 'move': key(app, pg.K_RIGHT)
    elif cancel == 'page': app.change_page('instrument')
    elif cancel == 'focus': app.handle(pg.event.Event(pg.WINDOWFOCUSLOST))
    elif cancel == 'mouse': app.handle(pg.event.Event(pg.MOUSEBUTTONDOWN, button=1, pos=(0, 0)))
    else: app.open_menu()
    assert app.pattern_reset_entry is None and app.editor.song == before


def test_partial_reset_backspace_invalid_letter_and_explicit_pw_only(app):
    before = deepcopy(app.editor.cell)
    key(app, pg.K_r, 'r'); key(app, pg.K_a, 'a')
    key(app, pg.K_RETURN)
    key(app, pg.K_2, '2')
    assert app.editor.cell == before and app.pattern_reset_entry[1] == 'RA'
    key(app, pg.K_BACKSPACE)
    assert app.pattern_reset_entry[1] == 'R'
    key(app, pg.K_RETURN)
    cell = app.editor.pattern.rows[0][0]
    assert cell.pulse_width == -1 and (cell.attack, cell.decay, cell.sustain, cell.release) == (2, 3, 4, 5)


def test_adsr_r_is_immediate_and_caps_lock_still_auditions(app, monkeypatch):
    app.editor.column = 10
    key(app, pg.K_r, 'r', scan=21)
    assert app.editor.pattern.rows[0][0].attack == -1
    app.editor.row = 0; app.editor.column = 14
    before = deepcopy(app.editor.song)
    sent = []; monkeypatch.setattr(app.audio, 'send', lambda *args: sent.append(args))
    key(app, pg.K_r, 'R', mod=pg.KMOD_CAPS, scan=21)
    assert not app.pattern_reset_entry and app.editor.song == before
    assert any(c[0] == 'on' for c in sent)


@pytest.mark.parametrize('buttons', [True, False])
def test_reset_all_button_targets_selection_preserves_music_and_undo(app, buttons):
    app.pattern_clipboard_buttons = buttons
    before = deepcopy(app.editor.song)
    app.editor.anchor = (0, 0, 13); app.editor.selection_end = (2, 1, 15)
    app.renderer.render(app)
    rect = next(r for r, a, _ in app.renderer.hits if a == 'reset_automation')
    assert app.screen.get_rect().contains(rect)
    app.handle(pg.event.Event(pg.MOUSEBUTTONDOWN, button=1, pos=rect.center))
    assert app.editor.song == before
    app.handle(pg.event.Event(pg.MOUSEBUTTONUP, button=1, pos=rect.center))
    assert app.dialog['kind'] == 'pattern_edit_confirm' and app.dialog['button_focus'] == 1
    assert app.editor.song == before
    key(app, pg.K_LEFT)
    key(app, pg.K_RETURN)
    for row in range(3):
        for voice in range(3):
            cell = app.editor.pattern.rows[row][voice]
            if voice < 2:
                assert all(getattr(cell, f) == -1 for f in AUTOMATION_FIELDS)
            else:
                assert cell == before.patterns[0].rows[row][voice]
    cell = app.editor.pattern.rows[0][0]
    assert (cell.note, cell.instrument, cell.effect, cell.parameter, cell._extra_fields) == (48, 1, 'H', 0x23, {'future': 7})
    assert app.editor.song.instruments == before.instruments
    app.execute(Command('undo')); assert app.editor.song == before


def test_ral_is_current_cell_even_with_selection_and_renderer_explains_each_reset(app, monkeypatch):
    app.editor.anchor = (0, 0, 13); app.editor.selection_end = (3, 2, 15)
    key(app, pg.K_r, 'r'); key(app, pg.K_a, 'a'); key(app, pg.K_l, 'l')
    assert app.editor.pattern.rows[0][1] == Cell()
    assert app.editor.pattern.rows[1][0] == Cell()
    app.renderer.render(app)
    labels = []
    monkeypatch.setattr(app.renderer, 'text', lambda x,y,text,*args: labels.append(text))
    app.renderer.voice_cell(app.editor.pattern.rows[0][0], 0, 0)
    assert labels.count('R') == 4 and labels[-1] == 'RAL'
    app.renderer.voice_cell(Cell(pulse_width=-1), 0, 0)
    assert labels[-1] == 'R..'
