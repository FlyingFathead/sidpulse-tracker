"""Manual order navigation must preserve the sample clock and voice state."""
from copy import deepcopy
from fractions import Fraction

import pygame as pg
import pytest

from sidpulse.app import App
from sidpulse.playback.sequencer import Sequencer
from sidpulse.song.model import Cell, Pattern, Song
from sidpulse.ui.keyboard import dispatch
from test_playback import TraceSID, wait_until


def ordered_song():
    song = Song(speed=6, tempo=137)
    song.orders = [0, 2, 1, 2]
    song.patterns = {i: Pattern(rows=[[Cell(), Cell(), Cell()] for _ in range(8)])
                     for i in range(3)}
    song.patterns[0].rows[0][0] = Cell(48, 1)
    return song


def test_skip_at_next_tick_keeps_clock_and_sustained_voice():
    sid = TraceSID(); seq = Sequencer(sid); seq.start(ordered_song())
    seq.render(123)
    before = (seq.frames, seq.next_tick, seq.programs, bytes(sid.registers), list(sid.events))
    assert seq.skip_order(1)
    assert (seq.frames, seq.next_tick, seq.programs, bytes(sid.registers), sid.events) == before
    boundary = int(Fraction(120000, 137))
    seq.render(boundary - 124)
    assert seq.order == 0
    seq.render(1)
    assert (seq.order, seq.pattern, seq.row, seq.tick, seq.frames) == (1, 2, 0, 0, boundary)
    assert seq.next_tick == Fraction(240000, 137)
    assert seq.notes[0] == 48 and seq.instruments[0] == 1
    assert seq.programs is before[2] and bytes(sid.registers) == before[3]


def test_rapid_skips_follow_orders_and_clamp_at_edges():
    seq = Sequencer(TraceSID()); seq.start(ordered_song()); seq.render(123)
    assert not seq.skip_order(-1)
    for _ in range(3): assert seq.skip_order(1)
    assert not seq.skip_order(1)
    assert seq.skip_order(-1)
    seq.render(int(seq.next_tick) - seq.frames)
    assert (seq.order, seq.pattern, seq.row) == (2, 1, 0)
    assert seq.skip_order(-1)
    seq.render(int(seq.next_tick) - seq.frames)
    assert (seq.order, seq.pattern) == (1, 2)


def test_skip_before_first_render_and_inactive_modes():
    seq = Sequencer(TraceSID()); seq.start(ordered_song())
    assert seq.skip_order(1); assert seq.skip_order(1)
    seq.render(1)
    assert (seq.order, seq.pattern, seq.frames) == (2, 1, 1)
    seq.pause(); before = seq.state
    assert not seq.skip_order(1) and seq.state == before
    seq.stop(); before = seq.state
    assert not seq.skip_order(-1) and seq.state == before
    seq.start(ordered_song(), 'pattern'); before = seq.state
    assert not seq.skip_order(1) and seq.state == before


def test_skip_trace_is_independent_of_buffer_partition():
    traces = []
    for chunks in ([5000], [1, 511, 2048, 2440]):
        song = ordered_song(); song.patterns[2].rows[0][0] = Cell(55, 2)
        sid = TraceSID(); seq = Sequencer(sid); seq.start(song); seq.render(123)
        seq.skip_order(1)
        for count in chunks: seq.render(count)
        traces.append((seq.state, sid.events))
    assert traces[0] == traces[1]
    assert any(frame == int(Fraction(120000, 137)) and reg == 4 and value & 1
               for frame, reg, value in traces[0][1])


@pytest.mark.parametrize('mapping', ['modern', 'classic'])
@pytest.mark.parametrize('symbol,mod,text,direction', [
    (pg.K_KP_PLUS, 0, '', 1), (pg.K_KP_MINUS, 0, '', -1),
    (pg.K_PLUS, 0, '+', 1), (pg.K_EQUALS, pg.KMOD_SHIFT, '+', 1),
    (pg.K_MINUS, 0, '-', -1), (pg.K_UNKNOWN, 0, '+', 1),
])
def test_info_keys_and_editor_keys_are_separate(mapping, symbol, mod, text, direction):
    event = pg.event.Event(pg.KEYDOWN, key=symbol, mod=mod, unicode=text, scancode=0)
    command = dispatch(event, 'info', mapping=mapping)
    assert (command.name, command.value) == ('skip_order', direction)
    other = dispatch(event, 'pattern', mapping=mapping)
    assert other is None or other.name != 'skip_order'


@pytest.mark.parametrize('frames', [2048, 512])
def test_real_worker_skips_with_keys_and_buttons_without_restart(frames):
    app = App(ordered_song(), audio=True, audio_buffer=frames)
    def press(symbol):
        app.handle(pg.event.Event(pg.KEYDOWN, key=symbol, mod=0, unicode='', scancode=0))
    try:
        wait_until(lambda: app.audio.ready or app.audio.error)
        assert not app.audio.error
        press(pg.K_F5)
        wait_until(lambda: app.audio.playback.frames > 1000)
        before = deepcopy(app.editor.song)
        elapsed = app.audio.playback.frames
        press(pg.K_KP_PLUS)
        wait_until(lambda: app.audio.playback.order == 1)
        assert app.audio.playback.frames > elapsed
        elapsed = app.audio.playback.frames
        app.renderer.render(app)
        rect = next(r for r, action, value in app.renderer.hits if (action, value) == ('skip_order', -1))
        app.handle(pg.event.Event(pg.MOUSEBUTTONDOWN, button=1, pos=rect.center))
        app.handle(pg.event.Event(pg.MOUSEBUTTONUP, button=1, pos=rect.center))
        wait_until(lambda: app.audio.playback.order == 0)
        assert app.audio.playback.frames > elapsed and not app.audio.error
        assert app.editor.song == before and not app.editor.history.undo_stack
        assert app.audio.playback.notes[0] == 48
    finally:
        app.close()
