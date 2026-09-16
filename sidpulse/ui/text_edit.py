"""Single-line Unicode editing model, independent of SDL and song state.

The cursor is an insertion caret, not a piano-roll cell or a dialog button.
Selection is explicit: opening a field never selects/replaces its whole value.
"""
from dataclasses import dataclass


@dataclass
class TextEdit:
    text: str = ""
    caret: int = 0
    anchor: int | None = None
    scroll: int = 0

    def __post_init__(self):
        self.reset(self.text, self.caret)

    def reset(self, text: str, caret: int | None = None) -> None:
        self.text = str(text)
        self.caret = len(self.text) if caret is None else max(0, min(len(self.text), caret))
        self.anchor = None
        self.scroll = 0

    @property
    def selection(self) -> tuple[int, int]:
        other = self.caret if self.anchor is None else self.anchor
        return min(self.caret, other), max(self.caret, other)

    @property
    def selected_text(self) -> str:
        lo, hi = self.selection
        return self.text[lo:hi]

    def move_to(self, position: int, select: bool = False) -> None:
        if select:
            if self.anchor is None:
                self.anchor = self.caret
        else:
            self.anchor = None
        self.caret = max(0, min(len(self.text), position))

    def select_all(self) -> None:
        self.anchor, self.caret = 0, len(self.text)

    def _word_edge(self, direction: int) -> int:
        # Dots, slashes, spaces and underscores delimit filename components.
        pos = self.caret
        if direction < 0:
            while pos > 0 and not self.text[pos - 1].isalnum():
                pos -= 1
            while pos > 0 and self.text[pos - 1].isalnum():
                pos -= 1
        else:
            while pos < len(self.text) and self.text[pos].isalnum():
                pos += 1
            while pos < len(self.text) and not self.text[pos].isalnum():
                pos += 1
        return pos

    def move(self, direction: int, *, select: bool = False, word: bool = False) -> None:
        lo, hi = self.selection
        if not select and lo != hi:
            self.move_to(lo if direction < 0 else hi)
        else:
            self.move_to(self._word_edge(direction) if word else self.caret + direction, select)

    def insert(self, value: str) -> None:
        # A paste cannot inject a NUL, newline, tab or other control character.
        value = ''.join(c for c in value if c >= ' ' and c != '\x7f')
        if not value:
            return
        lo, hi = self.selection
        self.text = self.text[:lo] + value + self.text[hi:]
        self.caret = lo + len(value)
        self.anchor = None

    def delete(self, backwards: bool = False, word: bool = False) -> None:
        lo, hi = self.selection
        if lo == hi:
            if word:
                edge = self._word_edge(-1 if backwards else 1)
                lo, hi = min(edge, self.caret), max(edge, self.caret)
            elif backwards:
                lo = max(0, lo - 1)
            else:
                hi = min(len(self.text), hi + 1)
        self.text = self.text[:lo] + self.text[hi:]
        self.caret, self.anchor = lo, None

    def view(self, columns: int) -> tuple[str, int, tuple[int, int]]:
        """Visible text, caret column and clipped selection (end exclusive)."""
        columns = max(1, int(columns))
        self.scroll = max(0, min(self.scroll, self.caret))
        if self.caret >= self.scroll + columns:
            self.scroll = self.caret - columns + 1
        self.scroll = min(self.scroll, max(0, len(self.text) - columns + 1))
        lo, hi = self.selection
        lo = max(0, min(columns, lo - self.scroll))
        hi = max(0, min(columns, hi - self.scroll))
        return self.text[self.scroll:self.scroll + columns], self.caret - self.scroll, (lo, hi)

    def click(self, column: int, select: bool = False) -> None:
        self.move_to(self.scroll + max(0, column), select)
