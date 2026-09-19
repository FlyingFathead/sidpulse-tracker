"""Confirm destructive pattern commands without changing their reviewed target."""
import pygame as pg

from sidpulse.preferences import save_preferences


def target(app):
    ed = app.editor
    return (id(ed), ed.history.revision, ed.pattern_id, ed.row, ed.voice,
            ed.column, ed.anchor, ed.selection_end)


def open_dialog(app, operation):
    app.release_audition()
    app.pattern_reset_entry = None
    app.follow_playback = False
    ed = app.editor
    r0, r1, v0, v1 = ed.bounds()
    scope = f'Pattern {ed.pattern_id:03d}, rows {r0:03d}-{r1:03d}, CH {v0+1}-{v1+1}.'
    if operation == 'cut':
        fields = ed.selection_description() if ed.anchor is not None else 'Current cell, all fields.'
        message = scope + ' ' + fields + ' Cut these fields to the clipboard and clear them here? Undo restores the cut data.'
    else:
        message = scope + ' Replace A D S R PW with instrument-default reset commands throughout this area? Notes, IN and FX stay intact. Undo restores the previous automation.'
    app.dialog = {'kind': 'pattern_edit_confirm', 'operation': operation,
                  'title': 'Cut selected fields?' if operation == 'cut' else 'Reset all automation?',
                  'message': message, 'button_focus': 1, 'skip_next_time': False,
                  'target': target(app)}


def handle_event(app, event):
    dialog = app.dialog
    cut = dialog['operation'] == 'cut'
    if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
        for rect, action, value in reversed(app.renderer.hits):
            if rect.collidepoint(event.pos):
                if action == 'cut_confirmation_checkbox':
                    dialog['skip_next_time'] = not dialog['skip_next_time']
                    dialog['button_focus'] = 2
                    return
                if action == 'dialog_button':
                    handle_event(app, pg.event.Event(pg.KEYDOWN, key=value, mod=0))
                    return
        return
    if event.type != pg.KEYDOWN:
        return
    key = event.key
    if key in (pg.K_TAB, pg.K_LEFT, pg.K_RIGHT):
        step = -1 if key == pg.K_LEFT or key == pg.K_TAB and event.mod & pg.KMOD_SHIFT else 1
        dialog['button_focus'] = (dialog['button_focus'] + step) % (3 if cut else 2)
        return
    if key in (pg.K_RETURN, pg.K_KP_ENTER, pg.K_SPACE):
        if dialog['button_focus'] == 2:
            dialog['skip_next_time'] = not dialog['skip_next_time']
            return
        key = pg.K_y if dialog['button_focus'] == 0 else pg.K_ESCAPE
    if key == pg.K_ESCAPE:
        app.dialog = None
        app.editor.status = 'Cut cancelled' if cut else 'Automation reset cancelled'
    elif key == pg.K_y:
        if target(app) != dialog['target']:
            app.dialog = None
            app.clipboard_feedback('Selection changed; please try again', True)
            return
        if cut and dialog['skip_next_time']:
            try:
                save_preferences({'confirm_cut': False})
            except OSError as exc:
                dialog['error'] = 'Could not save preference: ' + str(exc)
                return
            app.confirm_cut = False
        app.dialog = None
        if cut:
            app.copy_fields(cut=True, confirmed=True)
        else:
            app.editor.reset_automation(selection=True)
            app.clipboard_feedback('Automation reset to instrument defaults')
