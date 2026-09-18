"""Staged audio settings with asynchronous output testing and application."""
import pygame as pg

from sidpulse.preferences import BUFFERS, DEFAULT_BUFFER
from sidpulse.ui.instrument_graphs import button, slider_thumb
from sidpulse.ui.themes import palette

SAMPLE_RATE = 48000
# Retain the existing buffer / OK / Cancel / detector keyboard focus order.
FOCUS_COUNT = 8


def open_dialog(app, step=0):
    app.release_audition()
    pg.key.stop_text_input()
    index = max(0, min(len(BUFFERS) - 1, BUFFERS.index(app.audio_buffer) + step))
    app.dialog = {'kind': 'audio_buffer', 'title': 'Audio settings (Alt+F12)',
                  'index': index, 'focus': 0, 'drag_rect': None,
                  'detection': app.audio_underrun_detection,
                  'device': app.audio_output_device, 'pending': None,
                  'test_request': None, 'picker': False, 'scroll': 0}
    app.audio.send('refresh_outputs')


def choices(app):
    names = list(app.audio.output_devices)
    selected = app.dialog['device']
    if selected is not None and selected not in names:
        names.append(selected)  # retain a disconnected saved preference visibly
    return [None, *names]


def device_label(app, name):
    if name is None:
        return 'System default'
    return name + (' (unavailable)' if name not in app.audio.output_devices else '')


def move_device(app, step):
    values = choices(app)
    app.dialog['device'] = values[(values.index(app.dialog['device']) + step) % len(values)]
    app.dialog.pop('error', None)


def sync(app):
    dialog = app.dialog
    if not dialog or dialog.get('kind') != 'audio_buffer':
        return
    if app.audio.error:
        dialog['error'] = app.audio.error
        dialog['pending'] = None
        dialog['test_request'] = None
        return
    result = app.audio.test_result
    if result and result[0] == dialog['test_request']:
        dialog['test_request'] = None
        if not result[1]:
            dialog['error'] = result[2]
    pending = dialog['pending']
    result = app.audio.output_result
    if not pending or not result or result[0] != pending['id']:
        return
    dialog['pending'] = None
    if pending.get('rollback'):
        if not result[1]:
            dialog['error'] += '; restore failed: ' + result[2]
        return
    if not result[1]:
        dialog['error'] = result[2]
        return
    try:
        app.save_audio_settings(*pending['settings'])
    except (OSError, ValueError) as exc:
        dialog['error'] = str(exc)
        dialog['pending'] = {'id': app.audio.request('output', *pending['previous']),
                             'rollback': True}
    else:
        app.dialog = None


def activate(app, action):
    dialog = app.dialog
    if action == 'cancel':
        app.audio.send('stop_test')
        pending = dialog['pending']
        if pending and not pending.get('rollback'):
            app.audio.request('output', *pending['previous'])
        app.dialog = None
        return
    if dialog['pending']:
        return
    dialog.pop('error', None)
    if action == 'defaults':
        app.audio.send('stop_test')
        dialog.update(index=BUFFERS.index(DEFAULT_BUFFER), detection=True, device=None,
                      picker=False, test_request=None)
    elif action == 'refresh':
        app.audio.send('refresh_outputs')
    elif action == 'test':
        if app.audio.test_active or dialog['test_request'] is not None:
            app.audio.send('stop_test')
            dialog['test_request'] = None
        elif not app.audio.ready:
            dialog['error'] = app.audio.error or 'Audio is not ready.'
        else:
            dialog['test_request'] = app.audio.request('test_output', BUFFERS[dialog['index']], dialog['device'])
    elif action == 'ok':
        settings = (BUFFERS[dialog['index']], dialog['detection'], dialog['device'])
        if app.audio.thread is None:  # audio-disabled editor: preferences only
            try:
                old = app.audio_buffer
                app.save_audio_settings(*settings)
                if old != settings[0]:
                    app.audio.send('buffer', settings[0])
            except (OSError, ValueError) as exc:
                dialog['error'] = str(exc)
            else:
                app.dialog = None
        elif not app.audio.ready:
            dialog['error'] = app.audio.error or 'Audio is not ready.'
        else:
            previous = (app.audio.buffer_frames, app.audio.output_device)
            dialog['pending'] = {'id': app.audio.request('output', settings[0], settings[2]),
                                 'settings': settings, 'previous': previous}


def set_from_mouse(dialog, x, rect):
    index = round((x - rect.left) * (len(BUFFERS) - 1) / max(1, rect.width - 1))
    dialog['index'] = max(0, min(len(BUFFERS) - 1, index))


def handle_event(app, event):
    dialog = app.dialog
    if event.type == pg.KEYDOWN and event.key == pg.K_ESCAPE:
        if dialog['picker']:
            dialog['picker'] = False
        else:
            activate(app, 'cancel')
        return
    if dialog['pending']:
        if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
            for rect, action, value in app.renderer.hits:
                if action == 'buffer_button' and value == 'cancel' and rect.collidepoint(event.pos):
                    activate(app, 'cancel')
        return
    if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
        for rect, action, value in reversed(app.renderer.hits):
            if not rect.collidepoint(event.pos):
                continue
            if action == 'audio_choice':
                dialog['device'] = value
                dialog['picker'] = False
                dialog.pop('error', None)
            elif action == 'audio_device':
                dialog['focus'] = 4
                dialog['picker'] = not dialog['picker']
                dialog['scroll'] = max(0, choices(app).index(dialog['device']) - 2)
            elif action == 'buffer_slider':
                dialog['focus'] = 0
                dialog['drag_rect'] = rect.copy()
                set_from_mouse(dialog, event.pos[0], rect)
            elif action in ('buffer_button', 'audio_action'):
                activate(app, value)
            elif action == 'audio_detection':
                dialog['focus'] = 3
                dialog['detection'] = not dialog['detection']
            return
        dialog['picker'] = False
    elif event.type == pg.MOUSEMOTION and dialog['drag_rect'] is not None:
        set_from_mouse(dialog, event.pos[0], dialog['drag_rect'])
    elif event.type == pg.MOUSEBUTTONUP and event.button == 1:
        if dialog['drag_rect'] is not None:
            set_from_mouse(dialog, event.pos[0], dialog['drag_rect'])
            dialog['drag_rect'] = None
    elif event.type == pg.MOUSEWHEEL:
        if dialog['picker']:
            dialog['scroll'] = max(0, min(max(0, len(choices(app)) - 5), dialog['scroll'] - event.y))
        elif dialog['focus'] == 4:
            move_device(app, -event.y)
        else:
            dialog['focus'] = 0
            dialog['index'] = max(0, min(len(BUFFERS) - 1, dialog['index'] + event.y))
    elif event.type == pg.KEYDOWN:
        key = event.key
        if dialog['picker']:
            if key in (pg.K_UP, pg.K_DOWN):
                move_device(app, -1 if key == pg.K_UP else 1)
                dialog['scroll'] = max(0, choices(app).index(dialog['device']) - 2)
            elif key in (pg.K_RETURN, pg.K_KP_ENTER, pg.K_SPACE, pg.K_TAB):
                dialog['picker'] = False
            return
        if key == pg.K_TAB:
            dialog['focus'] = (dialog['focus'] + (-1 if event.mod & pg.KMOD_SHIFT else 1)) % FOCUS_COUNT
        elif key in (pg.K_RETURN, pg.K_KP_ENTER, pg.K_SPACE):
            focus = dialog['focus']
            if focus == 3:
                dialog['detection'] = not dialog['detection']
            elif focus == 4:
                dialog['picker'] = True
                dialog['scroll'] = max(0, choices(app).index(dialog['device']) - 2)
            else:
                activate(app, {0: 'ok', 1: 'ok', 2: 'cancel', 5: 'test', 6: 'refresh', 7: 'defaults'}[focus])
        elif key in (pg.K_LEFT, pg.K_RIGHT):
            step = -1 if key == pg.K_LEFT else 1
            if dialog['focus'] == 0:
                dialog['index'] = max(0, min(len(BUFFERS) - 1, dialog['index'] + step))
            elif dialog['focus'] == 3:
                dialog['detection'] = not dialog['detection']
            elif dialog['focus'] == 4:
                move_device(app, step)
            elif dialog['focus'] in (1, 2):
                dialog['focus'] = 1 + (dialog['focus'] - 1 + step) % 2
        elif key in (pg.K_UP, pg.K_DOWN):
            if dialog['focus'] == 4:
                move_device(app, -1 if key == pg.K_UP else 1)
            else:
                dialog['focus'] = 0 if key == pg.K_UP else 1
        elif key in (pg.K_HOME, pg.K_END):
            if dialog['focus'] == 0:
                dialog['index'] = 0 if key == pg.K_HOME else len(BUFFERS) - 1
            elif dialog['focus'] == 4:
                dialog['device'] = choices(app)[0 if key == pg.K_HOME else -1]


def draw(renderer, app):
    r = renderer
    dialog = app.dialog
    colors = palette(app.appearance)
    r.hits = []
    shade = pg.Surface(r.screen.get_size(), pg.SRCALPHA)
    shade.fill((0, 0, 0, 175))
    r.screen.blit(shade, (0, 0))
    w, h = min(76, r.cols - 2), 21
    x, y = (r.cols - w) / 2, (r.lines - h) / 2
    r.panel(x, y, w, h)
    frame = pg.Rect(round(x * r.cw), round(y * r.rh), round(w * r.cw), round(h * r.rh))
    pg.draw.rect(r.screen, colors['TEXT'], frame, 1)
    r.control_text(pg.Rect(frame.x, frame.y + 4, frame.width, r.rh), dialog['title'], colors['TEXT'])
    r.text(x + 2, y + 2, 'Output device:', colors['TEXT'])
    rect = r.well(x + 2, y + 3, w - 4, 1.4)
    r.text(x + 3, y + 3.2, device_label(app, dialog['device']), colors['CREAM'], w - 8)
    r.text(x + w - 4, y + 3.2, 'v', colors['CREAM'])
    r.hits.append((rect, 'audio_device', None))
    if dialog['focus'] == 4:
        pg.draw.rect(r.screen, colors['TEXT'], rect, 1)
    bw = (w - 6) / 3
    testing = app.audio.test_active or dialog['test_request'] is not None
    for i, (label, action) in enumerate((('Stop test' if testing else 'Test arpeggio', 'test'),
                                        ('Refresh outputs', 'refresh'), ('Reset defaults', 'defaults'))):
        button(r, x + 2 + i * (bw + 1), y + 5, bw, label,
               'audio_action', action, dialog['focus'] == i + 5)
    samples = BUFFERS[dialog['index']]
    r.text(x + 2, y + 7, f'Buffer: {samples} samples / {samples * 1000 / SAMPLE_RATE:.1f} ms', colors['TEXT'], w - 4)
    slider = r.well(x + 2, y + 9, w - 4, 1.3).inflate(-4, -5)
    proportion = dialog['index'] / (len(BUFFERS) - 1)
    pg.draw.rect(r.screen, colors['SLIDER'], (slider.x, slider.y, round(slider.width * proportion), slider.height))
    slider_thumb(r, slider, proportion)
    if dialog['focus'] == 0:
        pg.draw.rect(r.screen, colors['TEXT'], slider.inflate(10, 12), 1)
    r.hits.append((slider.inflate(0, 8), 'buffer_slider', None))
    r.text(x + 2, y + 10.6, 'Less delay', colors['TEXT'])
    r.text(x + w - 2 - len('More stability'), y + 10.6, 'More stability', colors['TEXT'])
    label = ('[x]' if dialog['detection'] else '[ ]') + ' Detect audio underruns / warn'
    rect = r.rect(x + 2, y + 12, w - 4, 1.4, colors['PANEL'])
    r.control_text(rect, label, colors['TEXT'])
    r.hits.append((rect, 'audio_detection', None))
    if dialog['focus'] == 3:
        pg.draw.rect(r.screen, colors['TEXT'], rect, 1)
    r.text(x + 2, y + 14,
           f'Missing {app.audio.missing_frames}f | late {app.audio.late_callbacks} | max {app.audio.max_callback_interval * 1000:.1f}ms',
           colors['TEXT'], w - 4)
    status = ('Applying audio settings...' if dialog['pending'] else
              'Testing output; song playback resumes afterwards.' if testing else
              app.audio.output_notice or app.audio.output_list_error or
              'Test previews the selection. OK saves; Cancel discards.')
    r.text(x + 2, y + 15.5, dialog.get('error', status), colors['TEXT'], w - 4)
    bw = (w - 5) / 2
    for i, (label, action) in enumerate((('OK', 'ok'), ('Cancel', 'cancel'))):
        button(r, x + 2 + i * (bw + 1), y + 17.5, bw, label,
               'buffer_button', action, dialog['focus'] == i + 1)
    r.text(x + 2, y + 19.6, 'Tab: focus | Arrows: adjust | Esc: cancel', colors['TEXT'], w - 4)
    if dialog['picker']:
        values = choices(app)
        start = max(0, min(dialog['scroll'], max(0, len(values) - 5)))
        # Prevent clicks from reaching controls behind the open device list.
        r.hits = [(rect, 'audio_device', None) for rect, action, _ in r.hits if action == 'audio_device']
        for i, value in enumerate(values[start:start + 5]):
            row = r.rect(x + 2, y + 4.4 + i * 1.4, w - 4, 1.4, colors['PANEL'])
            pg.draw.rect(r.screen, colors['TEXT'], row, 1)
            prefix = '> ' if value == dialog['device'] else '  '
            r.text(x + 2.3, y + 4.6 + i * 1.4, prefix + device_label(app, value), colors['TEXT'], w - 5)
            r.hits.append((row, 'audio_choice', value))
