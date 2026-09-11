from copy import deepcopy
from array import array
import pygame as pg
import pytest
from sidpulse.app import App
from sidpulse.sid.backend_residfp import ReSIDfpBackend, note_on, set_filter
from sidpulse.song.model import Song, Instrument


@pytest.mark.parametrize('voice', [0, 1, 2])
def test_only_the_playing_voice_moves_its_scope(voice):
    sid = ReSIDfpBackend(voice_scopes=True)
    set_filter(sid, Song().filter)
    sid.render(48000)
    note_on(sid, voice, 48, Instrument(waveform=32, attack=0, decay=0, sustain=15, release=0))
    sid.render(4800)
    traces = sid.voice_scopes.snapshot()
    for index, values in enumerate(traces):
        span = max(values) - min(values)
        assert span > .05 if index == voice else span < .001
    sid.set_clock('NTSC')
    sid.set_model('6581')
    assert sid.voice_scopes is not None
    sid.enable_scopes(False)
    assert sid.voice_scopes is None


def test_scopes_do_not_change_audible_pcm():
    blocks = []
    for enabled in (False, True):
        sid = ReSIDfpBackend(voice_scopes=enabled)
        set_filter(sid, Song().filter)
        sid.render(48000)
        for voice, wave in enumerate((16, 32, 128)):
            note_on(sid, voice, 36 + voice * 12, Instrument(waveform=wave))
        blocks.append(array('h', sid.render(4800)))
    # Native 8580 analog noise differs between fresh chips, even with scopes
    # disabled on both. Scope PCM must never enter the audible mix.
    assert len(blocks[0]) == len(blocks[1]) == 4800
    assert max(abs(a-b) for a,b in zip(*blocks)) <= 8


def test_playback_page_requests_scopes_and_keeps_buttons_separate(monkeypatch):
    app = App(audio=False)
    try:
        commands = []
        monkeypatch.setattr(app.audio, 'send', lambda *args: commands.append(args))
        before = deepcopy(app.editor.song)
        app.change_page('info');app.sync_audio();app.renderer.render(app)
        scopes = [r for r,a,v in app.renderer.hits if a == 'voice_scope']
        buttons = [r for r,a,v in app.renderer.hits if a in ('mute','solo')]
        assert len(scopes) == 3
        assert all(not scope.colliderect(button) for scope in scopes for button in buttons)
        assert app.screen.get_rect().contains(scopes[-1])
        app.change_page('pattern');app.sync_audio()
        assert [cmd for cmd in commands if cmd[0] == 'scopes'] == [('scopes', True), ('scopes', False)]
        assert app.editor.song == before
    finally:
        app.close()
