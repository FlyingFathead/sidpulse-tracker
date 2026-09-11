from array import array
from copy import deepcopy
import time
import pytest

from sidpulse.audio.engine import AudioEngine, VoiceAllocator
from sidpulse.sid.backend_residfp import ReSIDfpBackend, frequency, note_off, note_on, set_filter
from sidpulse.song.model import Instrument, Song


@pytest.mark.parametrize("model", ["6581", "8580"])
@pytest.mark.parametrize("wave", [16, 32, 64, 128])
def test_real_native_sid_generates_pcm(model, wave):
    sid = ReSIDfpBackend(model)
    song = Song()
    set_filter(sid, song.filter)
    inst = Instrument(waveform=wave)
    note_on(sid, 0, 48, inst)
    pcm = sid.render(4800)
    samples = array("h")
    samples.frombytes(pcm)
    assert len(samples) == 4800
    assert max(samples) - min(samples) > 500
    assert sid.registers[4] & 1
    note_off(sid, 0)
    assert not sid.registers[4] & 1
    assert sid.registers[4] & 0xF0 == wave
    note_off(sid, 0, cut=True)
    assert sid.registers[4] == 0


def test_sid_registers_and_exact_render_lengths():
    sid = ReSIDfpBackend()
    inst = Instrument(attack=2, decay=5, sustain=10, release=4, pulse_width=0xABC)
    note_on(sid, 2, 57, inst)
    assert frequency(57) == 7493
    assert sid.registers[19:21] == bytes([0x25, 0xA4])
    assert sid.registers[16:18] == bytes([0xBC, 0x0A])
    for frames in (1, 17, 512, 4096, 3, 4800):
        assert len(sid.render(frames)) == frames * 2
    sid.set_model("6581")
    assert sid.registers == bytes(25)


def test_stolen_voice_release_cannot_stop_new_note():
    allocator = VoiceAllocator()
    assert [allocator.acquire(k) for k in "abc"] == [0, 1, 2]
    assert allocator.acquire("d") == 0
    assert allocator.release("a") is None
    assert allocator.release("d") == 0


def test_fixed_pattern_voice_replaces_only_that_voice():
    allocator = VoiceAllocator()
    assert allocator.acquire("left", 0) == 0
    assert allocator.acquire("right", 2) == 2
    assert allocator.acquire("replacement", 2) == 2
    assert allocator.release("right") is None
    assert allocator.release("left") == 0
    assert allocator.release("replacement") == 2


@pytest.mark.parametrize("model", ["6581", "8580"])
def test_monitor_mute_changes_native_pcm_without_rewriting_song_registers(model):
    sid = ReSIDfpBackend(model)
    set_filter(sid, Song().filter)
    note_on(sid, 2, 48, Instrument())
    sid.render(4800)
    before = bytes(sid.registers)
    sid.set_muted((False, False, True))
    sid.render(48000)  # settle the native analog/DC transient after waveform disconnection
    quiet = array("h", sid.render(4800))
    assert max(quiet) - min(quiet) < 50
    assert bytes(sid.registers) == before
    sid.set_muted((False, False, False))
    audible = array("h", sid.render(4800))
    assert max(audible) - min(audible) > 500
    assert bytes(sid.registers) == before


def test_audio_worker_and_meter_continue_without_ui():
    engine = AudioEngine(Song())
    try:
        deadline = time.monotonic() + 3
        while not engine.ready and not engine.error and time.monotonic() < deadline:
            time.sleep(.01)
        assert engine.error is None
        assert engine.ready
        engine.send("on", 29, 48, Instrument())
        deadline = time.monotonic() + 1
        while engine.peak < .01 and time.monotonic() < deadline:
            time.sleep(.01)
        assert engine.active
        assert engine.peak > .01 and engine.rms > 0
        assert len(set(engine.waveform)) > 1
        engine.send("panic")
        deadline = time.monotonic() + 1
        while engine.active and time.monotonic() < deadline:
            time.sleep(.01)
        assert not engine.active
    finally:
        engine.close()
    assert not engine.thread.is_alive()
