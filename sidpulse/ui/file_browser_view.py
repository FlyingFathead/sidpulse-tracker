"""The one visible file browser, reused by load, save and both C64 exports."""
import pygame as pg
from .file_browser import LABELS, SUFFIXES


def draw_field(r, field, x, y, width, active, action):
    # Imported lazily: the application palette can change between frames.
    from . import renderer as c
    rect = r.well(x, y, width, 1.2)
    pad = max(2, r.cw // 3)
    inner = rect.inflate(-pad * 2, -2)
    columns = max(1, (inner.width - 2) // r.cw)
    text, caret, (lo, hi) = field.view(columns)
    clip = r.screen.get_clip()
    r.screen.set_clip(inner)
    if active and hi > lo:
        pg.draw.rect(r.screen, c.SELECT, (inner.x + lo * r.cw, inner.y,
                                         (hi - lo) * r.cw, inner.height))
    if text:
        r.screen.blit(r.font.render(text, True, c.YELLOW if active else c.CREAM), (inner.x, inner.y))
    if active:
        cx = inner.x + caret * r.cw
        pg.draw.line(r.screen, c.YELLOW, (cx, inner.y + 1), (cx, inner.bottom - 2), max(1, r.cw // 6))
        pg.key.set_text_input_rect(pg.Rect(cx, inner.y, max(1, r.cw), inner.height))
    r.screen.set_clip(clip)
    if active:
        pg.draw.rect(r.screen, c.YELLOW, rect, 1)
    r.hits.append((rect, action, None))


def draw(r, app, top, bottom):
    from . import renderer as c
    from .instrument_graphs import button
    b = app.browser
    r.text(2, top, 'Directory', c.TEXT)
    draw_field(r, b.location, 12, top, r.cols - 14, b.focus == 'directory', 'file_directory')
    split = max(40, r.cols * 2 // 3) if r.cols >= 100 else r.cols - 1
    y = top + 2
    height = max(3, bottom - y - 5)
    r.well(2, y, split - 4, height)
    r.text(3, y, 'Name (' + SUFFIXES[b.mode] + ')', c.CREAM, split - 6)
    show_dates = app.file_browser_show_modified and split - 6 >= 38
    date_x = split - 21
    name_width = date_x - 5 if show_dates else split - 8
    if show_dates:
        r.text(date_x, y, 'Modified', c.CREAM, 16)
    b.visible_rows = max(1, int(height - 1))
    start = max(0, b.index - b.visible_rows + 1)
    start = r.scroll_start('files',start,(str(b.directory),b.index),len(b.entries),b.visible_rows)
    for i, path in enumerate(b.entries[start:start + b.visible_rows], start):
        row = y + 1 + i - start
        selected = i == b.index
        if selected:
            r.rect(2.2, row + .05, split - 4.4, 1, c.CREAM if b.focus == 'list' else c.SELECT)
        label = '../' if i == 0 else path.name + ('/' if path.is_dir() else '')
        foreground = c.TEXT if selected and b.focus == 'list' else c.YELLOW
        r.text(3, row, label, foreground, name_width)
        if show_dates and i:
            r.text(date_x, row, b.modified.get(path, 'Unavailable'), foreground if selected else c.ACCENT, 16)
        r.hit(2, row, split - 4, 1, 'file', i)
    r.scroll_bar('files',split-3.5,y+1,b.visible_rows,len(b.entries),b.visible_rows)
    if not b.entries:
        r.text(3, y + 1, 'Directory unavailable. Ctrl+L to change it.', c.CREAM, split - 6)
    if r.cols >= 100:
        r.well(split, y, r.cols - split - 2, height)
        lines = [LABELS[b.mode] + ' ' + SUFFIXES[b.mode], '',
                 'Tab: move between fields', 'Arrows: list / text caret',
                 'Home/End: start / end', 'Shift+arrows: select text',
                 'Ctrl+A: select all', 'Ctrl+C/X/V: copy/cut/paste',
                 'Ctrl+L: edit directory', 'Alt+Up: parent directory', '',
                 'Filename starts from the', 'current project name.',
                 'Browse folders without', 'losing your filename edits.']
        for n, text in enumerate(lines[:max(0, int(height - 1))]):
            r.text(split + 1, y + n + .1, text, c.YELLOW if n == 0 else c.CREAM, r.cols - split - 4)
    r.text(2, bottom - 4, 'Filename', c.TEXT)
    draw_field(r, b.name, 12, bottom - 4, r.cols - 14, b.focus == 'name', 'filename')
    x = 2
    for label, action, focus in ((LABELS[b.mode], 'file_submit', 'action'),
                                 ('Cancel', 'file_cancel', 'cancel'),
                                 ('Parent', 'file_parent', None),
                                 ('Refresh', 'file_refresh', None)):
        width = len(label) + 4
        button(r, x, bottom - 2.5, width, label, action, None, b.focus == focus)
        x += width + 1
    hint = b.error or ('Enter in filename: ' + LABELS[b.mode].lower() + ' | Tab: switch fields | Esc: cancel')
    r.text(2, bottom - .9, hint, c.TEXT, r.cols - 4)
