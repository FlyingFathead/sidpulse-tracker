"""Use the supplied tracker face when present, with a system-monospace fallback."""
from pathlib import Path
import pygame as pg


def default_font_path():
    bundled = Path(__file__).resolve().parents[1] / 'assets' / 'DejaVuSansMono.ttf'
    if bundled.is_file():
        return str(bundled)
    return pg.font.match_font('dejavusansmono,consolas,liberationmono,monospace')
