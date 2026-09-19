from copy import deepcopy
import json

import pygame as pg
import pytest

from sidpulse.app import App
from sidpulse import preferences
from sidpulse.ui import settings_reset, welcome
from sidpulse.ui.dialogs import focus, choices
from sidpulse.ui.keyboard import Command
from sidpulse.ui.menus import menu_items
from sidpulse.export.squeeze import SqueezeOptions


def key(app, code):
    app.handle(pg.event.Event(pg.KEYDOWN, key=code, scancode=0, mod=0, unicode=''))


@pytest.fixture
def app(tmp_path):
    preferences.save_preferences({'audio_buffer': 4096, 'audio_output_device': 'Old output',
        'audio_underrun_detection': False, 'theme': 'High contrast', 'font_size': 22,
        'font_bold': False, 'colors': {'TEXT': [1, 2, 3]}, 'restart_on_f5': True,
        'file_browser_show_modified': False, 'pattern_clipboard_buttons': False,
        'control_panel_visible': True, 'channel_visualizers': False,
        'hide_welcome_on_startup': True, 'export_squeeze': {'enabled': False},
        'autosave_enabled': False, 'autosave_minutes': 17, 'autosave_directory': str(tmp_path / 'copies')})
    result = App(audio=False, size=(960, 540))
    yield result
    result.audio.thread = None
    result.close()


@pytest.mark.parametrize('cancel_by', ['enter', 'escape', 'mouse'])
def test_reset_is_last_settings_item_cancel_default_and_never_writes_on_cancel(app, cancel_by):
    assert menu_items('Settings Menu')[-1].command == 'reset_settings'
    original = preferences.config_path().read_bytes()
    app.execute(Command('reset_settings'))
    assert choices(app.dialog)[focus(app.dialog)][1] == pg.K_ESCAPE
    if cancel_by == 'mouse':
        app.renderer.render(app)
        rect = next(r for r,a,v in app.renderer.hits if a == 'dialog_button' and v == pg.K_ESCAPE)
        app.handle(pg.event.Event(pg.MOUSEBUTTONDOWN, button=1, pos=rect.center))
    else:
        key(app, pg.K_RETURN if cancel_by == 'enter' else pg.K_ESCAPE)
    assert app.dialog is None and preferences.config_path().read_bytes() == original
    assert app.audio_buffer == 4096 and app.restart_on_f5


def test_confirm_applies_defaults_preserves_song_history_presets_and_recovery_files(app, tmp_path):
    app.editor.edit('Example edit', [(('tempo',), 141)])
    app.editor.song.instruments[1].attack = 7
    original = deepcopy(app.editor.song)
    revision = app.editor.history.revision
    preset = preferences.config_path().parent / 'presets' / 'my-instrument.json'
    preset.parent.mkdir(); preset.write_text('saved preset')
    recovery = app.autosave.directory / 'saved.sidpulse'
    recovery.parent.mkdir(); recovery.write_text('previous recovery')
    app.execute(Command('reset_settings'))
    key(app, pg.K_LEFT); key(app, pg.K_RETURN)
    assert app.dialog is None and json.loads(preferences.config_path().read_text()) == {}
    assert app.audio_buffer == 2048 and app.audio_output_device is None and app.audio_underrun_detection
    assert app.appearance == preferences.APPEARANCE and not app.restart_on_f5
    assert app.file_browser_show_modified and app.channel_visualizers and app.pattern_clipboard_buttons
    assert app.control_panel_visible is None and app.autosave.enabled and app.autosave.minutes == 5
    assert welcome.show_on_startup() and preferences.load_squeeze_options() == SqueezeOptions()
    assert app.editor.song == original and app.editor.history.revision == revision and app.editor.dirty
    assert preset.read_text() == 'saved preset' and recovery.read_text() == 'previous recovery'
    assert preferences.load_appearance() == app.appearance
    assert preferences.load_channel_visualizers() and preferences.load_control_panel_visibility() is None


def simulate_worker(app, monkeypatch):
    app.audio.thread = object(); app.audio.ready = True
    app.audio.buffer_frames = 4096; app.audio.output_device = 'Old output'
    requests = []
    monkeypatch.setattr(app.audio, 'send', lambda *args: requests.append(args))
    return requests


def test_unavailable_audio_can_still_reset_bad_saved_configuration(app):
    app.audio.error = 'Audio initialization failed'
    settings_reset.begin(app)
    assert app.audio_output_device is None and preferences.load_audio_output_device() is None
    assert 'restart SIDpulse' in app.dialog['message'] and app.audio_buffer == 2048


def test_reset_waits_for_audio_acknowledgement_before_saving(app, monkeypatch):
    requests = simulate_worker(app, monkeypatch)
    settings_reset.begin(app)
    request = app.settings_reset_pending['id']
    assert requests[-1] == ('output', request, 2048, None)
    app.audio.output_result = (request - 1, True, '')
    app.sync_audio()
    assert app.audio_buffer == 4096 and preferences.load_preferences() == 4096
    app.audio.output_result = (request, True, '')
    app.sync_audio()
    assert app.settings_reset_pending is None and app.dialog is None
    assert app.audio_buffer == 2048 and preferences.load_preferences() == 2048


def test_cancelling_pending_audio_switch_restores_output_and_preserves_preferences(app, monkeypatch):
    requests = simulate_worker(app, monkeypatch)
    original = preferences.config_path().read_bytes()
    settings_reset.begin(app)
    old_request = app.settings_reset_pending['id']
    key(app, pg.K_ESCAPE)
    restore = app.settings_reset_pending['id']
    assert requests[-1] == ('output', restore, 4096, 'Old output')
    app.audio.output_result = (old_request, True, '')
    app.sync_audio()
    assert preferences.config_path().read_bytes() == original
    app.audio.output_result = (restore, True, '')
    app.sync_audio()
    assert app.settings_reset_pending is None and app.dialog is None
    assert app.audio_buffer == 4096 and preferences.config_path().read_bytes() == original


def test_failed_audio_switch_does_not_reset_any_preferences(app, monkeypatch):
    simulate_worker(app, monkeypatch)
    original = preferences.config_path().read_bytes()
    settings_reset.begin(app)
    app.audio.output_result = (app.settings_reset_pending['id'], False, 'Output unavailable')
    app.sync_audio()
    assert app.settings_reset_pending is None and 'Output unavailable' in app.dialog['message']
    assert app.audio_buffer == 4096 and preferences.config_path().read_bytes() == original


def test_failed_atomic_write_preserves_file_and_ui_and_restores_audio(app, monkeypatch):
    requests = simulate_worker(app, monkeypatch)
    original = preferences.config_path().read_bytes()
    def fail(*args):
        raise OSError('Read-only preferences')
    monkeypatch.setattr(preferences.os, 'replace', fail)
    settings_reset.begin(app)
    app.audio.output_result = (app.settings_reset_pending['id'], True, '')
    app.sync_audio()
    assert app.settings_reset_pending['rollback']
    restore = app.settings_reset_pending['id']
    assert requests[-1] == ('output', restore, 4096, 'Old output')
    assert app.audio_buffer == 4096 and app.appearance['theme'] == 'High contrast'
    assert preferences.config_path().read_bytes() == original
    assert not list(preferences.config_path().parent.glob('*.tmp'))
    app.audio.output_result = (restore, True, '')
    app.sync_audio()
    assert app.settings_reset_pending is None and 'Read-only' in app.dialog['message']
