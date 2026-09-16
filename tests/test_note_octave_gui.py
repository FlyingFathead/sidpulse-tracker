"""Mouse-hitbox -> key dispatch -> undo integration, with real pygame."""
import pytest
pg = pytest.importorskip("pygame", reason="pygame-ce required for GUI integration")
from sidpulse.app import App
from sidpulse.song.model import Song, Cell


def test_click_octave_digit_type_three_undo_and_redo(monkeypatch):
    app = App(Song(), audio=False)
    try:
        e = app.editor
        e.pattern.rows[0][0] = Cell(63, 3, "H", 0x34)
        e.instrument = 4
        e.skip = 0
        calls = []
        monkeypatch.setattr(app.audio, "send", lambda *args: calls.append(args))
        app.renderer.render(app)
        rect = next(rect for rect, action, data in app.renderer.hits
                    if action == "cell" and data == (0, 0, 1))
        app.handle(pg.event.Event(pg.MOUSEBUTTONDOWN, button=1, pos=rect.center))
        app.handle(pg.event.Event(pg.MOUSEBUTTONUP, button=1, pos=rect.center))
        assert e.column == 1
        app.handle(pg.event.Event(pg.KEYDOWN, key=pg.K_3, scancode=32, mod=0, unicode="3"))
        assert e.cell == Cell(39, 3, "H", 0x34)
        assert not any(call[0] == "on" for call in calls)
        app.handle(pg.event.Event(pg.KEYDOWN, key=pg.K_BACKSPACE, scancode=42, mod=pg.KMOD_CTRL, unicode=""))
        assert e.cell == Cell(63, 3, "H", 0x34)
        app.handle(pg.event.Event(pg.KEYDOWN, key=pg.K_BACKSPACE, scancode=42,
                                mod=pg.KMOD_CTRL | pg.KMOD_SHIFT, unicode=""))
        assert e.cell == Cell(39, 3, "H", 0x34)
        app.renderer.render(app)
    finally:
        app.close()
