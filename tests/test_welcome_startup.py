import json
import sys
from copy import deepcopy
from types import SimpleNamespace

import pytest

from sidpulse.__main__ import main
from sidpulse.app import App
from sidpulse.preferences import config_path, save_preferences
from sidpulse.project.format import save
from sidpulse.song.model import Song, example_song
from sidpulse.song.welcome import welcome_song
from sidpulse.ui import welcome


def launch(monkeypatch, *args, dismiss=False):
    seen = []

    def run(app, **kwargs):
        seen.append((app.editor.song.title, app.dialog, app.path))
        if dismiss and app.dialog and app.dialog.get('kind') == 'welcome':
            welcome.finish(app, False)

    monkeypatch.setattr(App, 'run', run)
    monkeypatch.setattr(sys, 'argv', ['sidpulse', '--silent', *args])
    assert main() == 0
    return seen[0]


def test_default_startup_repeats_splash_and_saves_unchecked_choice(monkeypatch):
    for _ in range(2):
        title, dialog, path = launch(monkeypatch, dismiss=True)
        assert title == 'Autumn at five' and dialog['kind'] == 'welcome'
        assert dialog['focus'] == 0 and dialog['hide_on_startup'] is False
        assert path is None and welcome.show_on_startup()
        assert json.loads(config_path().read_text())['hide_welcome_on_startup'] is False


@pytest.mark.parametrize('config', [
    b'', b'{', b'[]', b'null', b'\xff', b'{}',
    b'{"audio_buffer": 2048}',
    b'{"hide_welcome_on_startup": false}',
    b'{"hide_welcome_on_startup": "true"}',
    b'{"hide_welcome_on_startup": 1}',
    b'{"hide_welcome_on_startup": null}',
])
def test_missing_or_invalid_opt_out_defaults_to_show(monkeypatch, config):
    path = config_path()
    path.parent.mkdir(parents=True)
    path.write_bytes(config)
    title, dialog, _ = launch(monkeypatch)
    assert title == 'Autumn at five' and dialog['kind'] == 'welcome'
    assert dialog['hide_on_startup'] is False


@pytest.mark.parametrize('version', ['0.2.4', '0.2.10'])
def test_legacy_first_run_marker_does_not_hide_splash(monkeypatch, version):
    marker = config_path().with_name('first-run.json')
    marker.parent.mkdir(parents=True)
    marker.write_text(json.dumps({'welcome_seen': True, 'version': version}))
    for _ in range(2):
        title, dialog, _ = launch(monkeypatch, dismiss=True)
        assert title == 'Autumn at five' and dialog['kind'] == 'welcome'
        assert not dialog['hide_on_startup'] and welcome.show_on_startup()
    assert json.loads(marker.read_text())['version'] == version


def test_opt_out_hides_splash_and_force_welcome_preserves_choice(monkeypatch):
    save_preferences({'hide_welcome_on_startup': True})
    title, dialog, _ = launch(monkeypatch)
    assert title == 'Untitled' and dialog is None
    title, dialog, _ = launch(monkeypatch, '--welcome', dismiss=True)
    assert title == 'Autumn at five' and dialog['kind'] == 'welcome'
    assert dialog['hide_on_startup'] is True and not welcome.show_on_startup()


def test_unanswered_welcome_does_not_write_preference(monkeypatch):
    for _ in range(2):
        title, dialog, _ = launch(monkeypatch)
        assert title == 'Autumn at five' and dialog['kind'] == 'welcome'
        assert not config_path().exists()


def test_opening_project_and_headless_check_do_not_change_splash_preference(monkeypatch, tmp_path):
    project = save(tmp_path / 'my-song.sidpulse', Song(title='My own work'))
    title, dialog, path = launch(monkeypatch, str(project))
    assert title == 'My own work' and path == project and dialog is None
    assert welcome.show_on_startup()
    _, dialog, _ = launch(monkeypatch, '--headless-smoke')
    assert dialog is None and welcome.show_on_startup()


def test_stop_cancels_intro_while_audio_starts(monkeypatch):
    app = App(example_song(), audio=False)
    try:
        app.intro_pending = True
        app.panic()
        starts = []
        monkeypatch.setattr(app, 'start_playback', starts.append)
        app.audio.ready = True
        app.sync_audio()
        assert not app.intro_pending and not starts
    finally:
        app.close()


def test_cli_welcome_song_skips_dialog_and_keeps_bundled_file_unsaved(monkeypatch):
    title, dialog, path = launch(monkeypatch, '--play-welcome-song')
    assert title == welcome_song().title and dialog is None and path is None
    assert welcome.show_on_startup()  # explicit playback does not consume the welcome choice
    title, dialog, path = launch(monkeypatch, '--example')
    assert title == example_song().title and dialog is None and path is None


@pytest.mark.parametrize('other', ['--example', '--welcome', 'my-song.sidpulse'])
def test_cli_rejects_conflicting_welcome_song_sources(monkeypatch, other):
    monkeypatch.setattr(sys, 'argv', ['sidpulse', '--play-welcome-song', other])
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 2


@pytest.mark.parametrize('ready', [False, True])
def test_intro_waits_for_startup_notice_and_starts_once(monkeypatch, ready):
    app = App(welcome_song(), audio=False)
    starts = []
    try:
        # Simulate a native worker still starting without opening a real device.
        monkeypatch.setattr(app, 'audio', SimpleNamespace(
            ready=ready, thread=object(), error=None, send=lambda *args: None,
            playback=SimpleNamespace(status='stopped'), close=lambda: None))
        monkeypatch.setattr(app, 'start_playback', starts.append)
        app.notice('Autosave unavailable', 'Choose a writable folder in Settings.')
        welcome.play_intro(app)
        assert app.intro_pending and not starts
        app.audio.ready = True
        app.sync_audio()
        assert app.intro_pending and not starts
        app.dialog = None
        app.sync_audio()
        app.sync_audio()
        assert starts == ['song'] and not app.intro_pending
    finally:
        app.close()


def test_intro_can_start_immediately_and_disabled_audio_stays_editable(monkeypatch):
    app = App(welcome_song(), audio=False)
    starts = []
    try:
        before = deepcopy(app.editor.song)
        monkeypatch.setattr(app, 'start_playback', starts.append)
        welcome.play_intro(app)
        assert not starts and not app.intro_pending
        assert 'Audio is disabled' in app.editor.status and app.editor.song == before
        app.audio.ready = True
        welcome.play_intro(app)
        assert starts == ['song'] and not app.intro_pending
    finally:
        app.close()


def test_recovery_cancels_pending_welcome_playback(monkeypatch, tmp_path):
    app = App(welcome_song(), audio=False)
    starts = []
    try:
        project = save(tmp_path / 'recovery.sidpulse', Song(title='Recovered work'))
        app.dialog = {'recover': (tmp_path / 'old-session.json', {'autosave': str(project)})}
        app.intro_pending = True
        monkeypatch.setattr(app.autosave, 'acknowledge', lambda marker: None)
        monkeypatch.setattr(app, 'start_playback', starts.append)
        app.recover_autosave(True)
        app.audio.ready = True
        app.sync_audio()
        assert app.editor.song.title == 'Recovered work'
        assert not app.intro_pending and not starts
    finally:
        app.close()
