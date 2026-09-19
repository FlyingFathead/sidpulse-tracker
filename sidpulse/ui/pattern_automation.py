"""Transient R/RA/RAL entry; incomplete commands never enter song data."""
import pygame as pg
from sidpulse.commands.pattern_fields import FIELDS


def location(app):
    ed = app.editor
    return ed.pattern_id, ed.row, ed.voice, ed.column


def prefix(app):
    entry = app.pattern_reset_entry
    return entry[1] if entry and entry[0] == location(app) else ''


def handle_event(app, event):
    ed = app.editor
    eligible = (app.page == 'pattern' and not app.dialog and not app.menu_path
                and not app.control_focus and FIELDS[ed.column] == 'pulse_width')
    if not eligible or app.pattern_reset_entry and not prefix(app):
        app.pattern_reset_entry = None
    if event.type != pg.KEYDOWN:
        if event.type in (pg.MOUSEBUTTONDOWN, pg.MOUSEWHEEL, pg.WINDOWFOCUSLOST, pg.VIDEORESIZE, pg.QUIT):
            app.pattern_reset_entry = None
        return False
    key, mods = event.key, event.mod
    current = prefix(app)
    if current:
        if key == pg.K_ESCAPE:
            app.pattern_reset_entry = None
            ed.status = 'Reset entry cancelled; automation unchanged.'
            return True
        if not mods & (pg.KMOD_CTRL | pg.KMOD_ALT | pg.KMOD_CAPS):
            if key == pg.K_BACKSPACE:
                app.pattern_reset_entry = (location(app), 'R') if current == 'RA' else None
                return True
            if key == pg.K_a and current == 'R':
                app.pattern_reset_entry = (location(app), 'RA')
                ed.status = 'RA: type L to reset all A D S R PW; Esc cancels.'
                return True
            if key == pg.K_l and current == 'RA':
                app.pattern_reset_entry = None
                ed.reset_automation()
                ed.column = FIELDS.index('pulse_width')
                ed.advance()
                return True
            if key == pg.K_RETURN:
                if current == 'R':
                    app.pattern_reset_entry = None
                    ed.enter_digit('R')  # explicit PW-only reset
                else:
                    ed.status = 'Finish RAL with L, or Esc to cancel.'
                return True
            if key == pg.K_r:
                app.pattern_reset_entry = (location(app), 'R')
                return True
            if getattr(event, 'unicode', '').isalnum():
                ed.status = 'Type RAL for all automation, R then Enter for PW only, or Esc to cancel.'
                return True
        app.pattern_reset_entry = None  # navigation/shortcuts cancel, then execute normally
    if eligible and key == pg.K_r and not mods & (pg.KMOD_CTRL | pg.KMOD_ALT | pg.KMOD_CAPS):
        app.pattern_reset_entry = (location(app), 'R')
        app.follow_playback = False
        ed.status = 'R: type A L to reset all A D S R PW; Enter resets only PW; Esc cancels.'
        return True
    return False
