import sys
from copy import deepcopy
from types import SimpleNamespace

import pytest

from sidpulse.__main__ import main
from sidpulse.app import App
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


def test_first_normal_launch_loads_intro_and_remembers_skip(monkeypatch):
    title, dialog, path = launch(monkeypatch, dismiss=True)
    assert title == welcome_song().title and dialog['kind'] == 'welcome'
    assert path is None and not welcome.first_run()
    title, dialog, _ = launch(monkeypatch)
    assert title == 'Untitled' and dialog is None
    title, dialog, _ = launch(monkeypatch, '--welcome')
    assert title == welcome_song().title and dialog['kind'] == 'welcome'


def test_opening_project_and_headless_check_do_not_consume_first_run(monkeypatch, tmp_path):
    project = save(tmp_path / 'my-song.sidpulse', Song(title='My own work'))
    title, dialog, path = launch(monkeypatch, str(project))
    assert title == 'My own work' and path == project and dialog is None
    assert welcome.first_run()
    _, dialog, _ = launch(monkeypatch, '--headless-smoke')
    assert dialog is None and welcome.first_run()


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
    assert welcome.first_run()  # explicit playback does not consume the welcome choice
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
