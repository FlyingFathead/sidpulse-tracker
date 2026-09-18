"""PCM equivalence, independent starvation detection and process lifecycle."""
from array import array
from collections import deque
import random
import time

import pytest

from sidpulse.audio.output import OutputConditioner
from sidpulse.audio.stream import PCMStream
from sidpulse.sid.backend_residfp import ReSIDfpBackend


class OriginalConditioner(OutputConditioner):
    """Unmodified 0.2.21 algorithm, retained as an independent numerical oracle."""
    def process(self, pcm):
        samples = array('h', pcm)
        for i, x in enumerate(samples):
            if self.previous_x is None:
                self.previous_x = x
            y = x - self.previous_x + self.coefficient * self.previous_y
            self.previous_x, self.previous_y = x, y
            self.gain += max(-self.step, min(self.step, self.target - self.gain))
            samples[i] = max(-32768, min(32767, round(y * self.gain)))
        return samples.tobytes()


@pytest.mark.parametrize('frames', [1, 17, 256, 512, 1024, 2048, 4096, 8192])
def test_conditioner_matches_original_bits_across_ramps_clipping_and_dc(frames):
    rng = random.Random(222)
    original, optimized = OriginalConditioner(), OutputConditioner()
    for target in (0., 1., 1., 0., .35, 1., 0., 0.):
        original.target = optimized.target = target
        for form in ('random', 'dc', 'alternating'):
            samples = array('h', (rng.randint(-32768, 32767) if form == 'random'
                                 else 20000 if form == 'dc'
                                 else -32768 if i % 2 else 32767 for i in range(frames)))
            assert optimized.process(samples.tobytes()) == original.process(samples.tobytes())
            assert (optimized.previous_x, optimized.previous_y, optimized.gain) == (
                original.previous_x, original.previous_y, original.gain)
    assert optimized.process(b'') == original.process(b'') == b''


def test_native_block_fifo_preserves_gate_cycle_samples_and_resets():
    class Chip:
        def __init__(self): self.next = 0
        def clock(self, cycles):
            count = cycles // 20
            values = [((self.next+i) % 65536)-32768 for i in range(count)]
            self.next += count
            return values
        def reset(self): self.next = 0
    sid = ReSIDfpBackend.__new__(ReSIDfpBackend)
    sid.chip=Chip(); sid.pending=deque(); sid.pending_frames=sid.pending_offset=0
    sid.sample_rate=48000; sid.clock_hz=960000; sid.voice_scopes=None; sid.registers=bytearray(25)
    expected = 0
    for frames in (0,1,17,2048,3,512,8192,1):
        sid.clock(32); sid.clock(32)  # samples created by gate transitions
        result = array('h',sid.render(frames))
        assert result.tolist() == [((expected+i)%65536)-32768 for i in range(frames)]
        expected += frames
    sid.reset()
    assert sid.pending_frames == sid.pending_offset == 0 and not sid.pending
    assert array('h',sid.render(1)).tolist() == [-32768]


def test_callback_delay_is_visible_even_when_pcm_queue_is_full(monkeypatch):
    import sidpulse.audio.stream as module
    stream = PCMStream(2048, open_device=False)
    stream.expect_audio = True
    for _ in range(3): stream.write(bytes(4096))
    timestamps=iter((1.,1.14))
    monkeypatch.setattr(module,'perf_counter',lambda:next(timestamps))
    stream.callback(None,bytearray(4096)); stream.callback(None,bytearray(4096))
    assert stream.gaps == stream.missing_frames == 0
    assert stream.late_callbacks == 1 and stream.callback_count == 2
    assert stream.max_callback_interval == pytest.approx(.14)
    stream.reset_stats()
    assert stream.callback_count == stream.late_callbacks == stream.max_callback_interval == 0


def test_forced_starvation_counts_frames_and_episode_then_recovers():
    stream=PCMStream(2048,open_device=False);stream.expect_audio=True
    for _ in range(2):stream.write(b'\x01\x00'*2048)
    target=bytearray(4096)
    for _ in range(5):stream.callback(None,target)
    assert stream.gaps==1 and stream.missing_frames==6144 and target==bytes(4096)
    stream.write(b'\x02\x00'*2048);stream.callback(None,target)
    assert target==b'\x02\x00'*2048
    stream.callback(None,target)
    assert stream.gaps==2 and stream.missing_frames==8192


def test_process_audio_start_stop_and_no_orphan():
    import multiprocessing as mp
    from sidpulse.audio.engine import AudioEngine
    from sidpulse.song.model import example_song
    initial={p.pid for p in mp.active_children()}
    song=example_song();engine=AudioEngine(song)
    try:
        deadline=time.monotonic()+8
        while not engine.ready and not engine.error and time.monotonic()<deadline:time.sleep(.005)
        assert engine.ready and engine.error is None
        engine.send('play',song,'song',0,0,None)
        while engine.callback_count<5 and not engine.error and time.monotonic()<deadline:time.sleep(.005)
        assert engine.callback_count>=5 and engine.playback.frames>0
        assert engine.error is None
    finally:engine.close()
    assert not engine.thread.is_alive()
    assert {p.pid for p in mp.active_children()} == initial


def test_real_sdl_starvation_is_reported_when_renderer_is_deliberately_stalled(monkeypatch):
    from threading import Thread
    from sidpulse.audio.engine import AudioEngine
    from sidpulse.song.model import example_song
    original = ReSIDfpBackend.render
    calls = 0
    def stalled(self, frames):
        nonlocal calls
        calls += 1
        if calls == 30:
            time.sleep(.25)  # release the GIL so SDL drains the actual queue
        return original(self, frames)
    monkeypatch.setattr(ReSIDfpBackend, 'render', stalled)
    song=example_song();engine=AudioEngine(song,enabled=False)
    # Direct worker is intentional: inject a render failure inside its process.
    engine.thread=Thread(target=engine._run,daemon=True);engine.thread.start()
    try:
        deadline=time.monotonic()+8
        while not engine.ready and not engine.error and time.monotonic()<deadline:time.sleep(.005)
        assert engine.ready
        engine.send('play',song,'song',0,0,None)
        while engine.missing_frames==0 and not engine.error and time.monotonic()<deadline:time.sleep(.005)
        assert engine.underruns>0 and engine.missing_frames>0
        assert engine.error is None
    finally:engine.close()
