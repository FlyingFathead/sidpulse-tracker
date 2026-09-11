"""First-run marker and the intro-song welcome screen."""
import json
import os
from pathlib import Path
import tempfile

import pygame as pg

from sidpulse import __version__
from sidpulse.preferences import config_path
from sidpulse.ui.instrument_graphs import button
from sidpulse.ui.themes import palette


def marker_path():
    return config_path().with_name('first-run.json')


def first_run():
    return not marker_path().is_file()


def open_dialog(app):
    app.dialog = {'kind': 'welcome', 'focus': 1}


def finish(app, play):
    marker = marker_path()
    try:
        marker.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(dir=marker.parent, suffix='.tmp')
        try:
            with os.fdopen(fd, 'w') as stream:
                json.dump({'welcome_seen': True, 'version': __version__}, stream)
                stream.write('\n')
            os.replace(temporary, marker)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
    except OSError as exc:
        app.editor.status = f'Welcome preference could not be saved: {exc}'
    app.dialog = None
    if play:
        play_intro(app)


def play_intro(app):
    """Share manual/CLI playback and wait for audio or a startup notice."""
    app.intro_pending = False
    if app.audio.error:
        app.editor.status = app.audio.error
    elif app.audio.ready and app.dialog is None:
        app.start_playback('song')
    elif app.audio.ready or app.audio.thread is not None:
        app.intro_pending = True
        app.editor.status = 'Welcome song ready; waiting for startup...'
    else:
        app.editor.status = f'Audio is disabled. {app.editor.song.title} is ready in the editor.'


def handle_event(app, event):
    dialog = app.dialog
    if event.type == pg.KEYDOWN:
        if event.key in (pg.K_TAB, pg.K_LEFT, pg.K_RIGHT):
            dialog['focus'] = 1 - dialog['focus']
        elif event.key in (pg.K_RETURN, pg.K_KP_ENTER, pg.K_SPACE):
            finish(app, dialog['focus'] == 0)
        elif event.key == pg.K_ESCAPE:
            finish(app, False)
    elif event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
        for rect, action, value in reversed(app.renderer.hits):
            if action == 'welcome_button' and rect.collidepoint(event.pos):
                finish(app, value)
                break


def draw(r, app):
    colors = palette(app.appearance)
    r.hits = []
    shade = pg.Surface(r.screen.get_size(), pg.SRCALPHA)
    shade.fill((0, 0, 0, 180))
    r.screen.blit(shade, (0, 0))
    w, h = min(78, r.cols - 2), min(17, r.lines - 2)
    x, y = (r.cols - w) / 2, (r.lines - h) / 2
    r.panel(x, y, w, h)
    frame = pg.Rect(round(x * r.cw), round(y * r.rh), round(w * r.cw), round(h * r.rh))
    pg.draw.rect(r.screen, colors['TEXT'], frame, 1)
    width = round(min((w - 6) * r.cw, r.rh * 5 * 427 / 105))
    size = (width, max(1, round(width * 105 / 427)))
    if size not in r.logo_cache:
        path = Path(__file__).resolve().parents[1] / 'assets/sidpulse-tracker-logo.svg'
        r.logo_cache[size] = pg.image.load_sized_svg(str(path), size)
    logo = r.logo_cache[size]
    r.screen.blit(logo, logo.get_rect(midtop=(r.screen.get_width() // 2, round((y + 1) * r.rh))))
    for row, text in ((7, f'Welcome to SIDpulse Tracker v{__version__}!'),
                      (9, f'{app.editor.song.title} is ready to explore.'),
                      (10.2, 'F2: patterns | F4: instruments | F8: stop')):
        rect = pg.Rect(round((x + 1) * r.cw), round((y + row) * r.rh), round((w - 2) * r.cw), r.rh)
        r.control_text(rect, text, colors['TEXT'])
    bw = (w - 7) / 2
    for i, (label, play) in enumerate((('Play intro song', True), ('Skip intro song', False))):
        button(r, x + 3 + i * (bw + 1), y + h - 3, bw, label, 'welcome_button', play,
               app.dialog['focus'] == i)
