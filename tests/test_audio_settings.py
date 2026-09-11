import json
from copy import deepcopy

import pygame as pg
import pytest

from sidpulse.app import App
from sidpulse.preferences import BUFFERS, config_path, load_preferences, save_buffer, save_preferences
from sidpulse.ui.keyboard import Command
from sidpulse.ui.audio_buffer import open_dialog
from sidpulse.ui import welcome


def key(app, code, mod=0):
    app.handle(pg.event.Event(pg.KEYDOWN, key=code, scancode=0, mod=mod, unicode=''))


@pytest.fixture
def app():
    result = App(audio=False)
    yield result
    result.close()


def click(app, action, value=None):
    app.renderer.render(app)
    rect = next(r for r, a, v in app.renderer.hits if a == action and v == value)
    app.handle(pg.event.Event(pg.MOUSEBUTTONDOWN, button=1, pos=rect.center))


def test_default_buffer_and_saved_override(app):
    assert app.audio_buffer == app.audio.buffer_frames == load_preferences() == 1024
    save_buffer(4096)
    assert load_preferences() == 4096


def test_slider_draft_cancel_and_apply_do_not_change_song(app, monkeypatch):
    before = deepcopy(app.editor.song)
    sent = []
    monkeypatch.setattr(app.audio, 'send', lambda *args: sent.append(args))
    app.execute(Command('audio_settings'))
    app.renderer.render(app)
    track = next(r for r, a, _ in app.renderer.hits if a == 'buffer_slider')
    app.handle(pg.event.Event(pg.MOUSEBUTTONDOWN, button=1, pos=track.midleft))
    app.handle(pg.event.Event(pg.MOUSEMOTION, pos=(track.right + 100, track.centery)))
    app.handle(pg.event.Event(pg.MOUSEBUTTONUP, button=1, pos=(track.right + 100, track.centery)))
    assert BUFFERS[app.dialog['index']] == 8192
    assert app.audio_buffer == 1024 and not config_path().exists()
    click(app, 'buffer_button', 'cancel')
    assert app.dialog is None and app.audio_buffer == 1024
    open_dialog(app)
    key(app, pg.K_RIGHT)
    click(app, 'buffer_button', 'ok')
    assert app.dialog is None and app.audio_buffer == load_preferences() == 2048
    assert [message for message in sent if message[0] == 'buffer'] == [('buffer', 2048)]
    assert app.editor.song == before


def test_slider_keyboard_focus_and_preference_failure(app, monkeypatch):
    open_dialog(app)
    key(app, pg.K_END)
    key(app, pg.K_TAB)
    key(app, pg.K_RIGHT)
    key(app, pg.K_RETURN)  # focused Cancel
    assert app.dialog is None and app.audio_buffer == 1024
    open_dialog(app)
    key(app, pg.K_HOME)
    def fail(value):
        raise OSError('Read-only preferences')
    monkeypatch.setattr('sidpulse.app.save_buffer', fail)
    key(app, pg.K_RETURN)
    assert 'Read-only preferences' in app.dialog['error']
    assert app.audio_buffer == 1024
    key(app, pg.K_ESCAPE)
    assert app.dialog is None


@pytest.mark.parametrize('size,zoom', [((1280, 900), 1), ((480, 360), 3), ((800, 600), .5)])
def test_modal_controls_fit_after_resizing(app, size, zoom):
    app.zoom = zoom
    for opener in (open_dialog, welcome.open_dialog):
        opener(app)
        app.handle(pg.event.Event(pg.VIDEORESIZE, w=size[0], h=size[1]))
        app.renderer.render(app)
        assert len([a for _, a, _ in app.renderer.hits if a.endswith('_button')]) == 2
        for rect, _, _ in app.renderer.hits:
            assert app.screen.get_rect().contains(rect)


def test_welcome_ok_defaults_to_no_playback_and_repeats(app, monkeypatch):
    starts = []
    monkeypatch.setattr(app, 'start_playback', starts.append)
    welcome.open_dialog(app)
    key(app, pg.K_RETURN)
    assert app.dialog is None and welcome.show_on_startup()
    assert not starts and not app.intro_pending
    assert json.loads(config_path().read_text())['hide_welcome_on_startup'] is False


@pytest.mark.parametrize('play', [False, True])
def test_checkbox_persists_both_values_and_preserves_other_preferences(app, monkeypatch, play):
    save_preferences({'audio_buffer': 4096, 'restart_on_f5': True})
    starts = []
    monkeypatch.setattr(app, 'start_playback', starts.append)
    app.audio.ready = True
    for hide in (True, False):
        welcome.open_dialog(app)
        click(app, 'welcome_checkbox')
        assert app.dialog['hide_on_startup'] is hide
        click(app, 'welcome_button', play)
        assert app.dialog is None and welcome.show_on_startup() is not hide
        stored = json.loads(config_path().read_text())
        assert stored['hide_welcome_on_startup'] is hide
        assert stored['audio_buffer'] == 4096 and stored['restart_on_f5'] is True
    assert starts == (['song', 'song'] if play else [])


def test_checkbox_keyboard_focus_space_toggle_and_escape(app):
    welcome.open_dialog(app)
    key(app, pg.K_TAB, pg.KMOD_SHIFT)  # OK -> checkbox
    assert app.dialog['focus'] == 2
    key(app, pg.K_SPACE)
    assert app.dialog['hide_on_startup'] and not config_path().exists()
    key(app, pg.K_TAB)  # checkbox -> OK
    key(app, pg.K_ESCAPE)  # dismiss without playback and save draft
    assert app.dialog is None and not welcome.show_on_startup() and not app.intro_pending


def test_checkbox_save_error_keeps_playback_behind_notice(app, monkeypatch):
    starts = []
    def fail(updates):
        raise OSError('Read-only preferences')
    monkeypatch.setattr(welcome, 'save_preferences', fail)
    monkeypatch.setattr(app, 'start_playback', starts.append)
    app.audio.ready = True
    welcome.open_dialog(app)
    click(app, 'welcome_checkbox')
    click(app, 'welcome_button', True)
    assert app.dialog['kind'] == 'notice' and 'Read-only' in app.dialog['message']
    app.sync_audio()
    assert not starts and welcome.show_on_startup()
    key(app, pg.K_RETURN)
    app.sync_audio()
    assert starts == ['song'] and not app.intro_pending


def test_welcome_play_waits_for_audio_then_starts_once(app, monkeypatch):
    app.audio.thread = object()  # simulate startup without creating a device
    welcome.open_dialog(app)
    key(app, pg.K_RIGHT)
    key(app, pg.K_RETURN)
    assert app.intro_pending and app.dialog is None
    starts = []
    monkeypatch.setattr(app, 'start_playback', starts.append)
    app.audio.ready = True
    app.sync_audio()
    app.sync_audio()
    assert starts == ['song'] and not app.intro_pending
    app.audio.thread = None


def test_f12_buffer_click_opens_slider(app):
    app.change_page('settings')
    app.property_index = 13
    click(app, 'setting_edit', 13)
    assert app.dialog['kind'] == 'audio_buffer' and 'text' not in app.dialog
