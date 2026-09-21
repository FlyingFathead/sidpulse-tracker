"""Reset user preferences after confirmation and a successful output switch."""
import pygame as pg

from sidpulse import preferences
from sidpulse.recovery import preferences as recovery_preferences


def open_dialog(app):
    app.confirm_action(
        'Reset all settings to defaults?',
        'Restore user preferences, including appearance, audio, autosave and display options? '
        'Songs, instruments, patterns, presets and existing recovery files are kept.',
        lambda: begin(app))
    app.dialog.update(kind='reset_settings_confirm', button_focus=1)


def begin(app):
    if app.audio.error:
        # Broken audio must not prevent resetting the saved device preference.
        if commit(app):
            app.notice('Settings reset', 'User preferences have been reset. Audio is unavailable in this session; '
                       'restart SIDpulse Tracker to try the default output.')
        return
    if app.audio.thread is not None and not app.audio.ready:
        app.notice('Settings were not reset', app.audio.error or 'Audio is not ready. Try again shortly.')
        return
    if app.audio.thread is None:
        commit(app)
        return
    app.settings_reset_pending = {
        'id': app.audio.request('output', preferences.DEFAULT_BUFFER, None),
        'previous': (app.audio.buffer_frames, app.audio.output_device),
    }
    app.dialog = {'kind': 'reset_settings_pending', 'title': 'Resetting settings',
                  'message': 'Applying the default audio output and buffer...', 'button_focus': 0}


def cancel(app):
    pending = app.settings_reset_pending
    if pending and not pending.get('rollback'):
        pending.update(id=app.audio.request('output', *pending['previous']), rollback=True)
    app.dialog = None
    app.editor.status = 'Settings reset cancelled'


def sync(app):
    pending = app.settings_reset_pending
    if not pending:
        return
    if not pending.get('rollback') and (not app.dialog or app.dialog.get('kind') != 'reset_settings_pending'):
        # A quit/recovery dialog must not accidentally approve an in-flight reset.
        pending.update(id=app.audio.request('output', *pending['previous']), rollback=True)
    if app.audio.error:
        app.settings_reset_pending = None
        app.notice('Settings were not reset', app.audio.error)
        return
    result = app.audio.output_result
    if not result or result[0] != pending['id']:
        return
    if pending.get('rollback'):
        app.settings_reset_pending = None
        error = pending.get('error', '')
        if not result[1]:
            error += ('; ' if error else '') + 'Could not restore audio output: ' + result[2]
        if error:
            app.notice('Settings were not reset', error)
        return
    if not result[1]:
        app.settings_reset_pending = None
        app.notice('Settings were not reset', result[2])
        return
    if commit(app):
        app.settings_reset_pending = None
    else:
        pending.update(id=app.audio.request('output', *pending['previous']), rollback=True,
                       error=app.dialog['message'])
        app.dialog = {'kind': 'reset_settings_pending', 'title': 'Settings were not reset',
                      'message': 'Restoring the previous audio output...', 'button_focus': 0}


def commit(app):
    # Complete outstanding recovery writes before changing their destination.
    app.autosave.flush()
    try:
        preferences.reset_preferences()
    except OSError as exc:
        app.notice('Settings were not reset', str(exc))
        return False
    app.audio_buffer = preferences.DEFAULT_BUFFER
    app.audio_output_device = None
    app.audio_underrun_detection = True
    app.audio_warning = ''
    app.audio_warning_until = 0.0
    app.last_audio_gaps = app.audio.underruns
    app.last_audio_late_callbacks = app.audio.late_callbacks
    app.appearance = preferences.load_appearance()
    app.file_browser_show_modified = True
    app.restart_on_f5 = False
    app.pattern_clipboard_buttons = True
    app.pattern_fit_three = True
    app.confirm_cut = True
    app.instrument_monitor_buttons = True
    app.sample_auto_squeeze = True
    app.sample_normalize_before = True
    app.sample_normalize_after = False
    app.editor.centered = True
    app.automation_display = 2
    app.send_instrument_monitor()
    app.control_panel_visible = None  # Responsive default: collapsed on narrow windows.
    app.control_focus = False
    app.channel_visualizers = True
    app.keyboard_mapping = 'modern'
    app.helper_strip = True
    app.zoom = 1.0
    app.autosave.apply_settings(recovery_preferences())
    app.dialog = None
    app.editor.status = 'User settings reset to defaults'
    if app.fullscreen:
        try:
            app.screen = pg.display.set_mode(app.window_size, pg.RESIZABLE)
            app.fullscreen = False
        except pg.error as exc:
            app.notice('Settings reset', 'Preferences were reset; could not leave fullscreen: ' + str(exc))
    return True
