"""Shared actions for mouse buttons and keyboard-focused modal dialogs."""
import pygame as pg


def choices(dialog):
    if dialog.get('kind')=='notice':return [('OK',pg.K_RETURN)]
    if 'recover' in dialog:return [('Load autosave',pg.K_y),('Skip',pg.K_n)]
    if 'discard' in dialog:return [('Save & Quit' if dialog.get('quit') else 'Save',pg.K_s),('Discard & Quit' if dialog.get('quit') else 'Discard',pg.K_d),('Cancel',pg.K_ESCAPE)]
    if dialog.get('quit'):return [('Discard & Quit',pg.K_y),('Cancel',pg.K_ESCAPE)]
    if 'export' in dialog:return [('Save + export',pg.K_s),('Export only',pg.K_e),('Cancel',pg.K_ESCAPE)]
    if 'yes' in dialog:return [('OK',pg.K_y),('Cancel',pg.K_ESCAPE)]
    if 'text' in dialog:return [('OK',pg.K_RETURN),('Cancel',pg.K_ESCAPE)]
    return [('Close',pg.K_RETURN)]


def focus(dialog):
    options=choices(dialog)
    return dialog.get('button_focus',len(options)-1 if any(k in dialog for k in ('discard','export','yes','recover')) else 0)
