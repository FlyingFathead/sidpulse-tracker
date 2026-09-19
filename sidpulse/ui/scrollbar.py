"""Shared vertical scrollbars, in pixels or rows, with no document mutations."""
import pygame as pg
from .instrument_graphs import button_frame


def handle_scrollbar(state, event):
    if event.type in (pg.WINDOWFOCUSLOST, pg.VIDEORESIZE, pg.KEYDOWN):
        state.pop('scroll_drag', None)
    if event.type == pg.MOUSEBUTTONUP and event.button == 1:
        return state.pop('scroll_drag', None) is not None
    geometry = state.get('scrollbar')
    if geometry is None:
        return False
    track, thumb, maximum, page = geometry
    if event.type == pg.MOUSEMOTION and 'scroll_drag' in state:
        if not getattr(event, 'buttons', (True,))[0]:
            state.pop('scroll_drag', None)
            return True
        fraction = (event.pos[1] - track.y - state['scroll_drag']) / max(1, track.height - thumb.height)
        state['scroll'] = round(max(0, min(1, fraction)) * maximum)
    elif event.type == pg.MOUSEBUTTONDOWN and event.button == 1 and track.collidepoint(event.pos):
        if thumb.collidepoint(event.pos):
            state['scroll_drag'] = event.pos[1] - thumb.y
        else:
            direction = -1 if event.pos[1] < thumb.top else 1
            state['scroll'] = max(0, min(maximum, state['scroll'] + direction * page))
    else:
        return False
    state['ensure_focus'] = False
    return True


def draw_scrollbar(renderer, state, track, content_height, viewport_height, colors,
                   prefix='scroll', value=None):
    maximum = max(0, content_height - viewport_height)
    state['scroll_max'] = maximum
    state['scroll'] = max(0, min(maximum, state.get('scroll', 0)))
    if not maximum or track.height <= 0:
        state.pop('scrollbar', None)
        state.pop('scroll_drag', None)
        return
    height = min(max(1, track.height - 4), max(22, round(track.height * viewport_height / content_height)))
    thumb = pg.Rect(track.x, track.y + round((track.height - height) * state['scroll'] / maximum), track.width, height)
    pg.draw.rect(renderer.screen, colors['WELL'], track)
    pg.draw.rect(renderer.screen, colors['EDGE'], track, 1)
    button_frame(renderer, thumb, 'scroll_drag' in state)
    if thumb.height > 12:
        pg.draw.line(renderer.screen, colors['TEXT'], (thumb.left + 3, thumb.centery), (thumb.right - 4, thumb.centery))
    state['scrollbar'] = (track.copy(), thumb.copy(), maximum, viewport_height)
    renderer.hits.append((track, prefix + '_track', value))
    renderer.hits.append((thumb, prefix + '_thumb', value))


class Scrollbars:
    """View-only offsets. Keyboard/click selection changes restore cursor following."""
    def __init__(self):
        self.context = None
        self.states = {}
        self.visible = []

    @staticmethod
    def context_for(app):
        return (app.page, id(app.editor.song), id(app.dialog), tuple(app.menu_path), app.screen.get_size())

    def begin(self, context):
        if context != self.context:
            self.states.clear()
            self.context = context
        self.visible.clear()

    def offset(self, key, default, token, total, visible):
        state = self.states.setdefault(key, {})
        signature = (token, total, visible)
        if state.get('token') != signature:
            state.update(scroll=default, token=signature)
            state.pop('scroll_drag', None)
        state['scroll'] = max(0, min(max(0, total - visible), state['scroll']))
        return state['scroll']

    def draw(self, renderer, key, track, total, visible, colors):
        state = self.states[key]
        draw_scrollbar(renderer, state, track, total, visible, colors, value=key)
        if 'scrollbar' in state:
            self.visible.append(key)

    def handle(self, app, event):
        if self.context != self.context_for(app):
            return False
        if event.type not in (pg.MOUSEBUTTONDOWN, pg.MOUSEBUTTONUP, pg.MOUSEMOTION,
                              pg.WINDOWFOCUSLOST, pg.VIDEORESIZE, pg.KEYDOWN):
            return False
        for key in reversed(self.visible):
            state = self.states[key]
            if handle_scrollbar(state, event):
                if key == 'help':
                    app.help_scroll = state['scroll']
                    _, total, visible = state['token']
                    state['token'] = ((app.help_topic, app.help_scroll), total, visible)
                return True
        return False
