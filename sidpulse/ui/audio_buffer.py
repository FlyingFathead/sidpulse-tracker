"""A staged audio-buffer choice: dragging never reopens the audio device."""
import pygame as pg

from sidpulse.preferences import BUFFERS
from sidpulse.ui.instrument_graphs import button, slider_thumb
from sidpulse.ui.themes import palette

LABELS = ('OK', 'Cancel')
SAMPLE_RATE = 48000


def open_dialog(app, step=0):
    app.release_audition()
    pg.key.stop_text_input()
    index = max(0, min(len(BUFFERS) - 1, BUFFERS.index(app.audio_buffer) + step))
    app.dialog = {'kind': 'audio_buffer', 'title': 'Default audio buffer',
                  'index': index, 'focus': 0, 'drag_rect': None}


def activate(app, action):
    dialog = app.dialog
    if action == 'cancel':
        app.dialog = None
    elif action == 'ok':
        try:
            app.apply_audio_buffer(BUFFERS[dialog['index']])
        except (ValueError, OSError) as exc:
            dialog['error'] = str(exc)
        else:
            app.dialog = None


def set_from_mouse(dialog, x, rect):
    index = round((x - rect.left) * (len(BUFFERS) - 1) / max(1, rect.width - 1))
    dialog['index'] = max(0, min(len(BUFFERS) - 1, index))


def handle_event(app, event):
    dialog = app.dialog
    if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
        for rect, action, value in reversed(app.renderer.hits):
            if not rect.collidepoint(event.pos):
                continue
            if action == 'buffer_slider':
                dialog['focus'] = 0
                dialog['drag_rect'] = rect.copy()
                set_from_mouse(dialog, event.pos[0], rect)
            elif action == 'buffer_button':
                activate(app, value)
            return
    elif event.type == pg.MOUSEMOTION and dialog['drag_rect'] is not None:
        set_from_mouse(dialog, event.pos[0], dialog['drag_rect'])
    elif event.type == pg.MOUSEBUTTONUP and event.button == 1:
        if dialog['drag_rect'] is not None:
            set_from_mouse(dialog, event.pos[0], dialog['drag_rect'])
            dialog['drag_rect'] = None
    elif event.type == pg.MOUSEWHEEL:
        dialog['focus'] = 0
        dialog['index'] = max(0, min(len(BUFFERS) - 1, dialog['index'] + event.y))
    elif event.type == pg.KEYDOWN:
        key = event.key
        if key == pg.K_ESCAPE:
            activate(app, 'cancel')
        elif key == pg.K_TAB:
            dialog['focus'] = (dialog['focus'] + (-1 if event.mod & pg.KMOD_SHIFT else 1)) % 3
        elif key in (pg.K_RETURN, pg.K_KP_ENTER, pg.K_SPACE):
            activate(app, ('ok', 'ok', 'cancel')[dialog['focus']])
        elif key in (pg.K_LEFT, pg.K_RIGHT):
            step = -1 if key == pg.K_LEFT else 1
            if dialog['focus'] == 0:
                dialog['index'] = max(0, min(len(BUFFERS) - 1, dialog['index'] + step))
            else:
                dialog['focus'] = 1 + (dialog['focus'] - 1 + step) % 2
        elif key in (pg.K_UP, pg.K_DOWN):
            dialog['focus'] = 0 if key == pg.K_UP else 1
        elif key in (pg.K_HOME, pg.K_END) and dialog['focus'] == 0:
            dialog['index'] = 0 if key == pg.K_HOME else len(BUFFERS) - 1


def draw(renderer, app):
    r = renderer
    dialog = app.dialog
    colors = palette(app.appearance)
    r.hits = []
    shade = pg.Surface(r.screen.get_size(), pg.SRCALPHA)
    shade.fill((0, 0, 0, 175))
    r.screen.blit(shade, (0, 0))
    w, h = min(70, r.cols - 2), min(14, r.lines - 2)
    x, y = (r.cols - w) / 2, (r.lines - h) / 2
    r.panel(x, y, w, h)
    frame = pg.Rect(round(x * r.cw), round(y * r.rh), round(w * r.cw), round(h * r.rh))
    pg.draw.rect(r.screen, colors['TEXT'], frame, 1)
    r.control_text(pg.Rect(frame.x, frame.y + 4, frame.width, r.rh), dialog['title'], colors['TEXT'])
    samples = BUFFERS[dialog['index']]
    r.text(x + 2, y + 2, f'Current value: {samples} samples', colors['TEXT'], w - 4)
    r.text(x + 2, y + 3, f'{samples * 1000 / SAMPLE_RATE:.1f} ms per buffer', colors['TEXT'], w - 4)
    slider = r.well(x + 2, y + 5, w - 4, 1.3).inflate(-4, -5)
    proportion = dialog['index'] / (len(BUFFERS) - 1)
    pg.draw.rect(r.screen, colors['SLIDER'], (slider.x, slider.y, round(slider.width * proportion), slider.height))
    slider_thumb(r, slider, proportion)
    if dialog['focus'] == 0:
        pg.draw.rect(r.screen, colors['TEXT'], slider.inflate(10, 12), 1)
    r.hits.append((slider.inflate(0, 8), 'buffer_slider', None))
    r.text(x + 2, y + 6.6, 'Less delay', colors['TEXT'])
    r.text(x + w - 2 - len('More stability'), y + 6.6, 'More stability', colors['TEXT'])
    bw = (w - 5) / 2
    for i, (label, action) in enumerate(zip(LABELS, ('ok', 'cancel'))):
        button(r, x + 2 + i * (bw + 1), y + h - 3, bw, label,
               'buffer_button', action, dialog['focus'] == i + 1)
    hint = dialog.get('error', 'Drag / arrows: adjust | Tab: buttons | Esc: cancel')
    r.text(x + 2, y + h - 1.3, hint, colors['TEXT'], w - 4)
