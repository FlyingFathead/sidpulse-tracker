from copy import deepcopy

import pygame as pg
import pytest

from sidpulse.app import App
from sidpulse.preferences import BUFFERS, config_path, load_preferences, save_buffer
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


def test_welcome_skip_remembers_first_launch(app):
    assert welcome.first_run()
    welcome.open_dialog(app)
    click(app, 'welcome_button', False)
    assert app.dialog is None and not welcome.first_run() and not app.intro_pending
    assert welcome.marker_path().name == 'first-run.json'


def test_welcome_play_waits_for_audio_then_starts_once(app, monkeypatch):
    app.audio.thread = object()  # simulate startup without creating a device
    welcome.open_dialog(app)
    key(app, pg.K_LEFT)
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
