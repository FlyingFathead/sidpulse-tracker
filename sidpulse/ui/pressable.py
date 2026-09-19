"""Mouse capture for momentary buttons; activate once on release inside."""
import time
import pygame as pg


def begin(app, rect, command, pos):
    app.button_press = dict(rect=rect.copy(), command=command, pos=pos,
                            page=app.page, dialog=app.dialog)
    app.button_flash = None


def pressed(app, name, value=None):
    state = app.button_press
    if state and (state['command'].name, state['command'].value) == (name, value):
        return state['rect'].collidepoint(state['pos'])
    flash = app.button_flash
    return bool(flash and flash[:2] == (name, value) and time.monotonic() < flash[2])


def handle_event(app, event):
    state = app.button_press
    if not state:
        return False
    if app.page != state['page'] or app.dialog is not state['dialog'] or app.menu_path:
        app.button_press = None
        return False
    if event.type == pg.MOUSEMOTION:
        state['pos'] = event.pos
        if not getattr(event, 'buttons', (True,))[0]:
            app.button_press = None
        return True
    if event.type == pg.MOUSEBUTTONUP and event.button == 1:
        app.button_press = None
        if state['rect'].collidepoint(event.pos):
            command = state['command']
            # Very fast down/up pairs can arrive between frames. Retain a short
            # pressed frame without blocking the event loop or audio.
            app.button_flash = (command.name, command.value, time.monotonic() + .16)
            app.execute(command, event)
        return True
    if event.type in (pg.KEYDOWN, pg.QUIT, pg.WINDOWFOCUSLOST, pg.VIDEORESIZE, pg.MOUSEBUTTONDOWN):
        app.button_press = app.button_flash = None
    return False
