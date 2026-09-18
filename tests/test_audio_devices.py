"""Device routing, preference transactions and real spawned SDL integration."""
from array import array
from copy import deepcopy
import json
import math
import time

import pygame as pg
import pytest

from sidpulse.app import App
from sidpulse.audio.engine import AudioEngine
from sidpulse.audio import routing
from sidpulse.audio.stream import PCMStream
from sidpulse.preferences import config_path, load_audio_output_device, save_preferences
from sidpulse.song.model import example_song
from sidpulse.ui import audio_buffer as dialog


def wait(predicate, timeout=8):
    end = time.monotonic() + timeout
    while not predicate():
        assert time.monotonic() < end, 'Audio operation timed out'
        time.sleep(.005)


@pytest.mark.parametrize('value,expected', [(None, None), ('Speakers', 'Speakers'),
    ('Ääni / USB', 'Ääni / USB'), ('  exact SDL name  ', '  exact SDL name  '),
    ('', None), (' ', None), (False, None), (1, None), ([], None), ({}, None), ('bad\x00name', None)])
def test_saved_device_validation_and_unicode(value, expected):
    save_preferences({'audio_output_device': value})
    assert load_audio_output_device() == expected


def test_old_config_migrates_to_system_default():
    assert load_audio_output_device() is None
    save_preferences({'audio_buffer': 4096})
    assert load_audio_output_device() is None
    assert json.loads(config_path().read_text()) == {'audio_buffer': 4096}


def test_device_enumeration_initializes_playback_only(monkeypatch):
    import pygame._sdl2 as sdl
    calls = []
    monkeypatch.setattr(sdl, 'init_subsystem', lambda flag: calls.append(('init', flag)))
    monkeypatch.setattr(sdl, 'get_audio_device_names', lambda capture: calls.append(('list', capture)) or ['USB', 'HDMI', 'USB'])
    assert routing.output_devices() == ('USB', 'HDMI')
    assert calls == [('init', sdl.INIT_AUDIO), ('list', False)]


@pytest.fixture
def fake_outputs(monkeypatch):
    devices = ['Speakers', 'HDMI', 'Ääni / USB']
    fail = set()
    opened = []
    class Stream(PCMStream):
        def __init__(self, frames, device_name=None):
            super().__init__(frames, open_device=False, device_name=device_name)
            self.open_output()
        def open_output(self):
            if self.device_name in fail:
                raise OSError('Device busy')
            self.device = object()
            self.last_callback = None
            opened.append(self.device_name)
        def close(self): self.device = None
        def pause(self): self.paused = True
        def unpause(self): self.paused = False
        def write(self, pcm):
            device, self.device = self.device, None
            super().write(pcm)
            self.device = device
    monkeypatch.setattr(routing, 'output_devices', lambda: tuple(devices))
    monkeypatch.setattr(routing.AudioOutput, '_new', staticmethod(lambda frames, name: Stream(frames, name)))
    return devices, fail, opened


def test_missing_saved_device_falls_back_without_overwriting_config(fake_outputs):
    save_preferences({'audio_output_device': 'Missing'})
    output = routing.AudioOutput(2048, load_audio_output_device())
    assert output.device_name is None and 'Saved output unavailable' in output.notice
    assert load_audio_output_device() == 'Missing'


def test_device_open_failure_restores_original_pcm_queue_and_diagnostics(fake_outputs):
    _, fail, _ = fake_outputs
    output = routing.AudioOutput(2048, 'Speakers')
    old = output.channel
    old.write(b'\x12\x34' * 2048)
    old.write(b'\x56\x78' * 2048)
    old.gaps, old.missing_frames = 3, 100
    fail.add('HDMI')
    with pytest.raises(OSError, match='busy'):
        output.switch(4096, 'HDMI')
    assert output.channel is old and old.device is not None
    assert output.device_name == 'Speakers' and old.frames == 2048
    assert old.gaps == 3 and old.missing_frames == 100
    buffer = bytearray(4096)
    old.callback(None, buffer)
    assert buffer == b'\x12\x34' * 2048


def test_successful_switch_preserves_paused_state_and_session_counters(fake_outputs):
    output = routing.AudioOutput(2048, 'Speakers')
    output.channel.pause()
    output.channel.gaps, output.channel.missing_frames = 2, 64
    output.channel.late_callbacks = 7
    output.switch(4096, 'HDMI')
    assert output.channel.frames == 4096 and output.channel.paused
    assert output.device_name == 'HDMI'
    assert (output.channel.gaps, output.channel.missing_frames, output.channel.late_callbacks) == (2, 64, 7)


@pytest.mark.parametrize('paused', [False, True])
def test_test_arpeggio_restores_exact_unconsumed_song_pcm_and_pause(fake_outputs, paused):
    output = routing.AudioOutput(2048, 'Speakers')
    original = output.channel
    original.write(b'\x12\x34' * 2048)
    original.write(b'\x56\x78' * 2048)
    original.callback(None, bytearray(42))
    original.paused = paused
    before = (tuple(original.blocks), original.current, original.offset, original.priming)
    output.start_test(512, 'HDMI')
    assert output.testing and output.test_stream.frames == 512
    for _ in range(300):
        output.pump_test()
        if not output.testing:
            break
        if not output.test_stream.priming:
            output.test_stream.callback(None, bytearray(1024))
    assert not output.testing and output.channel is original
    assert output.device_name == 'Speakers' and original.paused is paused
    assert (tuple(original.blocks), original.current, original.offset, original.priming) == before


def test_cancel_and_unplug_restore_default_without_losing_queued_audio(fake_outputs):
    _, fail, _ = fake_outputs
    output = routing.AudioOutput(2048, 'Speakers')
    old = output.channel
    old.write(b'\x01\x00' * 2048)
    output.start_test(2048, 'HDMI')
    fail.add('Speakers')
    output.stop_test()
    assert output.channel is old and old.device is not None
    assert output.device_name is None and old.device_name is None
    assert list(old.blocks) == [b'\x01\x00' * 2048]
    assert 'system default' in output.notice


def test_enumeration_failure_keeps_default_available(fake_outputs, monkeypatch):
    def broken(): raise OSError('Unavailable device list')
    monkeypatch.setattr(routing, 'output_devices', broken)
    output = routing.AudioOutput(2048)
    assert output.device_name is None and 'Cannot list outputs' in output.list_error


def test_diagnostic_tone_starvation_contributes_to_session_counters(fake_outputs):
    output = routing.AudioOutput(2048)
    output.start_test(512, 'HDMI')
    output.pump_test()
    output.pump_test()
    test = output.test_stream
    for _ in range(4):
        test.callback(None, bytearray(1024))
    assert test.gaps == 1 and test.missing_frames == 1024
    output.stop_test()
    assert output.channel.gaps == 1 and output.channel.missing_frames == 1024


def test_arpeggio_pitch_level_duration_and_faded_edges():
    samples = array('h', routing.test_arpeggio())
    assert len(samples) == 52800 and max(map(abs, samples)) <= 4096
    assert samples[-4800:] == array('h', [0] * 4800)
    for n, note in enumerate((60, 64, 67, 72)):
        tone = samples[n * 12000:(n + 1) * 12000]
        assert tone[0] == tone[-1] == 0
        crossings = sum(a <= 0 < b for a, b in zip(tone[384:-385], tone[385:-384]))
        measured = crossings * 48000 / (12000 - 769)
        expected = 440 * 2 ** ((note - 69) / 12)
        assert measured == pytest.approx(expected, abs=5)


@pytest.fixture
def app():
    value = App(audio=False)
    value.audio.output_devices = ('Speakers', 'HDMI', 'Ääni / USB')
    yield value
    value.audio.thread = None
    value.close()


def test_defaults_cancel_save_and_roundtrip_preserve_other_preferences_and_song(app):
    save_preferences({'theme': 'Charcoal crimson', 'audio_buffer': 4096,
                      'audio_output_device': 'HDMI', 'audio_underrun_detection': False})
    app.audio_buffer = 4096
    app.audio_output_device = 'HDMI'
    app.audio_underrun_detection = False
    song = deepcopy(app.editor.song)
    before = config_path().read_bytes()
    dialog.open_dialog(app)
    dialog.activate(app, 'defaults')
    assert app.dialog['device'] is None and app.dialog['detection'] is True
    assert config_path().read_bytes() == before and app.audio_output_device == 'HDMI'
    dialog.activate(app, 'cancel')
    assert config_path().read_bytes() == before
    dialog.open_dialog(app)
    dialog.activate(app, 'defaults')
    dialog.activate(app, 'ok')
    saved = json.loads(config_path().read_text())
    assert saved['audio_buffer'] == 2048 and saved['audio_output_device'] is None
    assert saved['audio_underrun_detection'] is True and saved['theme'] == 'Charcoal crimson'
    assert app.editor.song == song


def test_device_picker_mouse_keyboard_and_refresh_are_staged(app, monkeypatch):
    sent = []
    monkeypatch.setattr(app.audio, 'send', lambda *args: sent.append(args))
    dialog.open_dialog(app)
    app.renderer.render(app)
    rect = next(r for r, action, _ in app.renderer.hits if action == 'audio_device')
    dialog.handle_event(app, pg.event.Event(pg.MOUSEBUTTONDOWN, button=1, pos=rect.center))
    app.renderer.render(app)
    rect = next(r for r, action, value in app.renderer.hits if action == 'audio_choice' and value == 'HDMI')
    dialog.handle_event(app, pg.event.Event(pg.MOUSEBUTTONDOWN, button=1, pos=rect.center))
    assert app.dialog['device'] == 'HDMI' and not app.dialog['picker']
    dialog.handle_event(app, pg.event.Event(pg.KEYDOWN, key=pg.K_RIGHT, mod=0))
    assert app.dialog['device'] == 'Ääni / USB'
    dialog.activate(app, 'refresh')
    assert not config_path().exists() and sent.count(('refresh_outputs',)) == 2


def prepare_async(app, monkeypatch):
    sent = []
    monkeypatch.setattr(app.audio, 'send', lambda *args: sent.append(args))
    app.audio.thread = object()
    app.audio.ready = True
    dialog.open_dialog(app)
    app.dialog['device'] = 'HDMI'
    dialog.activate(app, 'ok')
    return sent, app.dialog['pending']['id']


def test_save_waits_for_ack_and_rejection_never_persists(app, monkeypatch):
    sent, request = prepare_async(app, monkeypatch)
    assert not config_path().exists() and app.audio_output_device is None
    app.audio.output_result = (request - 1, True, '')
    dialog.sync(app)
    assert app.dialog['pending'] is not None
    app.audio.output_result = (request, False, 'Device busy')
    dialog.sync(app)
    assert 'busy' in app.dialog['error'] and not config_path().exists()
    dialog.activate(app, 'ok')
    request = app.dialog['pending']['id']
    app.audio.output_result = (request, True, '')
    dialog.sync(app)
    assert app.dialog is None and load_audio_output_device() == 'HDMI'


def test_save_error_rolls_back_output_and_cancel_does_not_save(app, monkeypatch):
    sent, request = prepare_async(app, monkeypatch)
    def fail(updates): raise OSError('Read-only preferences')
    monkeypatch.setattr('sidpulse.app.save_preferences', fail)
    app.audio.output_result = (request, True, '')
    dialog.sync(app)
    assert app.dialog['pending']['rollback'] and 'Read-only' in app.dialog['error']
    assert sent[-1][0] == 'output' and sent[-1][2:] == (2048, None)
    assert app.audio_output_device is None and not config_path().exists()
    dialog.activate(app, 'cancel')
    assert app.dialog is None


def test_cancel_during_pending_apply_enqueues_restore_and_never_saves(app, monkeypatch):
    sent, request = prepare_async(app, monkeypatch)
    dialog.activate(app, 'cancel')
    assert app.dialog is None and not config_path().exists()
    assert sent[-1][0] == 'output' and sent[-1][2:] == (2048, None)


def test_test_uses_draft_output_and_buffer_and_cancel_stops_it(app, monkeypatch):
    sent = []
    monkeypatch.setattr(app.audio, 'send', lambda *args: sent.append(args))
    app.audio.ready = True
    dialog.open_dialog(app)
    app.dialog.update(device='HDMI', index=1)
    dialog.activate(app, 'test')
    assert sent[-1][0] == 'test_output' and sent[-1][2:] == (512, 'HDMI')
    assert not config_path().exists() and app.audio_output_device is None
    dialog.activate(app, 'cancel')
    assert sent[-1] == ('stop_test',)


@pytest.mark.parametrize('size,zoom', [((480, 360), 3), ((1280, 900), 1), ((800, 600), .5)])
def test_all_controls_and_picker_fit_and_do_not_overlap(app, size, zoom):
    app.zoom = zoom
    app.handle(pg.event.Event(pg.VIDEORESIZE, w=size[0], h=size[1]))
    dialog.open_dialog(app)
    app.renderer.render(app)
    hits = app.renderer.hits
    assert all(app.screen.get_rect().contains(rect) for rect, _, _ in hits)
    for i, (rect, action, _) in enumerate(hits):
        assert all(not rect.colliderect(other) for other, _, _ in hits[i + 1:]), action
    app.dialog['picker'] = True
    app.renderer.render(app)
    assert all(app.screen.get_rect().contains(rect) for rect, _, _ in app.renderer.hits)


def test_spawned_named_device_test_pause_restore_and_failure_recovery():
    import multiprocessing as mp
    initial = {p.pid for p in mp.active_children()}
    song = example_song()
    engine = AudioEngine(song)
    try:
        wait(lambda: engine.ready or engine.error)
        assert engine.ready and not engine.error
        assert engine.output_devices
        name = engine.output_devices[0]
        request = engine.request('output', 2048, name)
        wait(lambda: engine.output_result and engine.output_result[0] == request)
        assert engine.output_result[1] and engine.output_device == name
        engine.send('play', song, 'song', 0, 0, None)
        wait(lambda: engine.playback.frames > 4096)
        request = engine.request('test_output', 512, name)
        wait(lambda: engine.test_active)
        before = engine.playback.frames
        time.sleep(.2)
        assert engine.playback.frames == before and engine.test_active
        wait(lambda: not engine.test_active)
        wait(lambda: engine.playback.frames > before)
        assert engine.output_device == name and engine.buffer_frames == 2048
        engine.send('pause')
        wait(lambda: engine.playback.status == 'paused')
        before = engine.playback.frames
        request = engine.request('test_output', 8192, None)
        wait(lambda: engine.test_active)
        engine.send('stop_test')
        wait(lambda: not engine.test_active)
        time.sleep(.08)
        assert engine.playback.frames == before and engine.playback.status == 'paused'
        request = engine.request('output', 4096, 'not a real output')
        wait(lambda: engine.output_result and engine.output_result[0] == request)
        assert not engine.output_result[1] and engine.output_device == name
        assert engine.buffer_frames == 2048 and engine.ready and not engine.error
        engine.send('pause')
        wait(lambda: engine.playback.frames > before)
    finally:
        engine.close()
    assert not engine.thread.is_alive()
    assert {p.pid for p in mp.active_children()} == initial


def test_real_app_saves_confirmed_selection_and_reloads_on_next_start():
    app = App(audio=True)
    try:
        wait(lambda: app.audio.ready or app.audio.error)
        assert not app.audio.error
        song = deepcopy(app.editor.song)
        name = app.audio.output_devices[0]
        dialog.open_dialog(app)
        app.dialog['device'] = name
        app.dialog['detection'] = False
        dialog.activate(app, 'ok')
        def applied():
            app.sync_audio()
            return app.dialog is None
        wait(applied)
        assert load_audio_output_device() == name
        assert app.audio.output_device == name and not app.audio_underrun_detection
        assert app.editor.song == song
    finally:
        app.close()
    app = App(audio=True)
    try:
        wait(lambda: app.audio.ready or app.audio.error)
        assert app.audio.output_device == name and app.audio_output_device == name
        assert not app.audio_underrun_detection and not app.audio.error
        app.audio.request('test_output', 2048, name)
        wait(lambda: app.audio.test_active)
    finally:
        app.close()  # shutdown during a tone must close both streams, without reopening
    assert not app.audio.thread.is_alive()
