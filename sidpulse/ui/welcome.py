"""Startup splash with an explicit, per-user opt-out and demo playback."""
import json
from pathlib import Path

import pygame as pg

from sidpulse import __version__
from sidpulse.preferences import config_path, save_preferences
from sidpulse.ui.instrument_graphs import button_frame
from sidpulse.ui.themes import palette


def show_on_startup():
    """Show by default; old welcome_seen markers are not an explicit opt-out."""
    try:
        data = json.loads(config_path().read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return True
    return not (isinstance(data, dict) and data.get('hide_welcome_on_startup') is True)


def open_dialog(app):
    app.dialog = {'kind': 'welcome', 'focus': 0,
                  'hide_on_startup': not show_on_startup()}


def finish(app, play):
    hide = app.dialog['hide_on_startup']
    save_error = None
    try:
        save_preferences({'hide_welcome_on_startup': hide})
    except OSError as exc:
        save_error = str(exc)
    app.dialog = None
    if not play:
        app.new_project()
    if save_error:
        app.notice('Welcome preference could not be saved', save_error)
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
            step = -1 if event.key == pg.K_LEFT or (event.key == pg.K_TAB
                    and getattr(event, 'mod', 0) & pg.KMOD_SHIFT) else 1
            dialog['focus'] = (dialog['focus'] + step) % 3
        elif event.key in (pg.K_RETURN, pg.K_KP_ENTER, pg.K_SPACE):
            if dialog['focus'] == 2:
                dialog['hide_on_startup'] = not dialog['hide_on_startup']
            else:
                finish(app, dialog['focus'] == 1)
        elif event.key == pg.K_ESCAPE:
            finish(app, False)
    elif event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
        for rect, action, value in reversed(app.renderer.hits):
            if not rect.collidepoint(event.pos):
                continue
            if action == 'welcome_checkbox':
                dialog['focus'] = 2
                dialog['hide_on_startup'] = not dialog['hide_on_startup']
                break
            if action == 'welcome_button':
                finish(app, value)
                break


def draw(r, app):
    colors = palette(app.appearance)
    r.hits = []
    shade = pg.Surface(r.screen.get_size(), pg.SRCALPHA)
    shade.fill((0, 0, 0, 180))
    r.screen.blit(shade, (0, 0))
    # Bound this modal's metrics separately so all content fits at high zoom.
    unit = min(r.rh, (r.screen.get_height() - 24) / 18)
    frame = pg.Rect(0, 0, min(r.screen.get_width() - 24, max(420, 78 * r.cw)), round(18 * unit))
    frame.center = r.screen.get_rect().center
    pg.draw.rect(r.screen, colors['PANEL'], frame)
    pg.draw.rect(r.screen, colors['TEXT'], frame, 1)
    font_size = max(10, min(r.layout.font_size, round(unit * .75)))
    assets = Path(__file__).resolve().parents[1] / 'assets'

    def font(size, bold=True):
        key = (size, bold)
        if key not in r.welcome_font_cache:
            result = pg.font.Font(str(assets / 'DejaVuSansMono.ttf'), size)
            result.set_bold(bold)
            r.welcome_font_cache[key] = result
        return r.welcome_font_cache[key]

    def label(text, center, small=False, color=None):
        face = font(max(10, round(font_size * .75)), False) if small else font(font_size)
        rendered = face.render(text, True, colors['TEXT'] if color is None else color)
        glyph = rendered.subsurface(rendered.get_bounding_rect())
        r.screen.blit(glyph, glyph.get_rect(center=center))

    width = round(min(frame.width - 4 * unit, unit * 5 * 427 / 105))
    size = (width, max(1, round(width * 105 / 427)))
    if size not in r.logo_cache:
        path = assets / 'sidpulse-tracker-logo.svg'
        r.logo_cache[size] = pg.image.load_sized_svg(str(path), size)
    logo = r.logo_cache[size]
    r.screen.blit(logo, logo.get_rect(midtop=(frame.centerx, round(frame.top + unit))))
    for row, text in ((7.2, f'Version {__version__}'),
                      (9.3, 'Start a new song or explore the demo.')):
        label(text, (frame.centerx, round(frame.top + row * unit)))
    label('F2: patterns | F4: instruments | F8: stop',
          (frame.centerx, round(frame.top + 10.8 * unit)), small=True)
    bw = (frame.width - 5 * unit) / 2
    for i, (text, play) in enumerate((('New song', False), ('Play demo song', True))):
        rect = pg.Rect(round(frame.left + 2 * unit + i * (bw + unit)),
                       round(frame.top + 13 * unit), round(bw), round(1.5 * unit))
        selected = app.dialog['focus'] == i
        button_frame(r, rect, selected)
        label(text, rect.center, color=colors['CREAM'] if selected else colors['TEXT'])
        r.hits.append((rect, 'welcome_button', play))

    # Small, secondary control in the lower-left corner; the whole label clicks.
    mark = 'x' if app.dialog['hide_on_startup'] else ' '
    text = f"[{mark}] Don't show this on startup"
    face = font(max(10, round(font_size * .75)), False)
    glyph = face.render(text, True, colors['TEXT'])
    rect = glyph.get_rect(midleft=(round(frame.left + unit), round(frame.bottom - 1.2 * unit)))
    r.screen.blit(glyph, rect)
    hit = rect.inflate(8, 8)
    r.hits.append((hit, 'welcome_checkbox', None))
    if app.dialog['focus'] == 2:
        pg.draw.rect(r.screen, colors['TEXT'], hit, 1)
