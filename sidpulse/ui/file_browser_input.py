"""SDL adapter for the shared file browser. Text is accepted via TEXTINPUT only."""
import pygame as pg


def handle_event(app, event):
    """True when consumed; False lets global UI commands handle the event."""
    b = app.browser
    if event.type == pg.TEXTINPUT:
        if b.field is not None:
            b.field.insert(event.text)
            b.error = ''
            app.file_status()
        return True
    if event.type == pg.TEXTEDITING:
        # SDL owns composition; only committed TEXTINPUT mutates the filename.
        return True
    if event.type == pg.MOUSEWHEEL:
        if pg.key.get_mods() & pg.KMOD_CTRL:
            return False  # keep the global UI zoom shortcut
        b.move(-event.y * 3)
        b.focus = 'list'
        app.sync_file_text_input()
        return True
    if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
        for rect, action, value in reversed(app.renderer.hits):
            if not rect.collidepoint(event.pos):
                continue
            if action == 'file':
                b.index, b.focus = value, 'list'
                if b.selected is not None and not b.selected.is_dir():
                    b.set_name(b.selected.name)
                if getattr(event, 'clicks', 1) >= 2:
                    app.select_file()
            elif action in ('filename', 'file_directory'):
                b.focus = 'name' if action == 'filename' else 'directory'
                pad = max(2, app.renderer.cw // 3)
                col = round((event.pos[0] - rect.left - pad) / max(1, app.renderer.cw))
                b.field.click(col, bool(pg.key.get_mods() & pg.KMOD_SHIFT))
            elif action == 'file_submit':
                app.submit_file()
            elif action == 'file_cancel':
                app.cancel_browser()
            elif action == 'file_parent':
                app.file_navigate(b.directory.parent)
            elif action == 'file_refresh':
                app.refresh_files()
            else:
                return False
            app.sync_file_text_input()
            return True
        return False
    if event.type != pg.KEYDOWN:
        return False
    key, mod = event.key, event.mod
    ctrl, alt, shift = bool(mod & pg.KMOD_CTRL), bool(mod & pg.KMOD_ALT), bool(mod & pg.KMOD_SHIFT)
    if key == pg.K_ESCAPE:
        app.cancel_browser()
    elif key == pg.K_TAB:
        b.tab(shift)
    elif ctrl and not alt and key == pg.K_l:
        b.focus = 'directory'
        b.location.select_all()
    elif alt and key in (pg.K_UP, pg.K_BACKSPACE):
        app.file_navigate(b.directory.parent)
    elif key == pg.K_RETURN and not (ctrl or alt):
        if b.focus == 'list':
            app.select_file()
        elif b.focus == 'directory':
            b.enter_directory()
            app.file_status()
        elif b.focus == 'cancel':
            app.cancel_browser()
        else:
            app.submit_file()
    elif not alt and (key == pg.K_F10 or ctrl and key in (pg.K_s, pg.K_w)):
        if b.mode == 'save':
            if shift:
                app.prompt_filename()
            else:
                app.submit_file()
        else:
            app.browse('save')
    elif b.field is not None:
        field = b.field
        if key in (pg.K_LEFT, pg.K_RIGHT):
            field.move(-1 if key == pg.K_LEFT else 1, select=shift, word=ctrl and not alt)
        elif key in (pg.K_HOME, pg.K_END):
            field.move_to(0 if key == pg.K_HOME else len(field.text), shift)
        elif key in (pg.K_BACKSPACE, pg.K_DELETE):
            field.delete(backwards=key == pg.K_BACKSPACE, word=ctrl and not alt)
        elif ctrl and not alt and key == pg.K_a:
            field.select_all()
        elif ctrl and not alt and key in (pg.K_c, pg.K_x, pg.K_v):
            try:
                if key == pg.K_v:
                    field.insert(pg.scrap.get_text())
                elif field.selected_text:
                    pg.scrap.put_text(field.selected_text)
                    if key == pg.K_x:
                        field.delete()
            except (pg.error, OSError) as exc:
                b.error = 'Clipboard unavailable: ' + str(exc)
                app.file_status()
        elif key == pg.K_F8:
            return False  # panic is always available
        elif ctrl and alt and not mod & (pg.KMOD_RALT | pg.KMOD_MODE) and key in (
                pg.K_RETURN, pg.K_EQUALS, pg.K_PLUS, pg.K_KP_PLUS, pg.K_MINUS, pg.K_KP_MINUS, pg.K_0):
            return False  # explicit window/zoom controls, not printable AltGr input
        elif key in (pg.K_F1, pg.K_F2, pg.K_F3, pg.K_F4, pg.K_F9, pg.K_F10, pg.K_F11, pg.K_F12):
            return False
        # All printable KEYDOWNs, including AltGr, wait for Unicode TEXTINPUT.
        # Ctrl+S/W is handled above against the visible filename, never the old name.
    elif b.focus == 'list':
        if key in (pg.K_UP, pg.K_DOWN, pg.K_PAGEUP, pg.K_PAGEDOWN):
            b.move({pg.K_UP: -1, pg.K_DOWN: 1, pg.K_PAGEUP: -b.visible_rows,
                    pg.K_PAGEDOWN: b.visible_rows}[key])
        elif key in (pg.K_HOME, pg.K_END):
            b.index = 0 if key == pg.K_HOME else max(0, len(b.entries) - 1)
        elif key == pg.K_BACKSPACE:
            app.file_navigate(b.directory.parent)
        elif key == pg.K_SPACE:
            app.prompt_filename()
        else:
            return False
    elif b.focus in ('action', 'cancel') and key in (pg.K_LEFT, pg.K_RIGHT):
        b.focus = 'cancel' if b.focus == 'action' else 'action'
    else:
        return False
    app.sync_file_text_input()
    return True
