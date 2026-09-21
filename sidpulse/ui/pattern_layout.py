"""Fit F2's voice grid without changing the surrounding page or row spacing."""
from collections import OrderedDict
from contextlib import contextmanager

import pygame as pg


class PatternGridLayout:
    # Below this size individual hex digits become difficult to distinguish.
    MIN_FONT_SIZE = 8
    ATTRIBUTES = ('font', 'cw', 'cols', 'text_cache', 'cell_cache', 'button_cache')

    def __init__(self):
        self.key = None
        self.metrics = None
        self.font_size = None

    @contextmanager
    def fitted(self, renderer, enabled):
        r = renderer
        required = 122 if r.control_visible else 102
        if not enabled or r.cols >= required:
            yield r.layout.font_size
            return
        key = (r.signature, required)
        if key != self.key:
            size = r.layout.font_size
            font, cw = r.font, r.cw
            while size > self.MIN_FONT_SIZE and r.screen.get_width() // cw < required:
                size -= 1
                font = pg.font.Font(r.font_path, size)
                font.set_bold(r.appearance['font_bold'])
                cw = max(1, font.size('M')[0])
            self.font_size = size
            self.metrics = (font, cw, r.screen.get_width() // cw,
                            OrderedDict(), OrderedDict(), OrderedDict())
            self.key = key
        original = tuple(getattr(r, name) for name in self.ATTRIBUTES)
        try:
            for name, value in zip(self.ATTRIBUTES, self.metrics):
                setattr(r, name, value)
            yield self.font_size
        finally:
            for name, value in zip(self.ATTRIBUTES, original):
                setattr(r, name, value)
