"""Continuous SDL PCM output with a bounded two-block reserve.

A device callback consumes samples directly. No mixer Sound boundaries or
per-Sound completion callbacks participate in musical timing.
"""
from collections import deque
from time import perf_counter
from sidpulse.audio.device import pause_device, close_device, _pause_function


class PCMStream:
    def __init__(self, frames, open_device=True, device_name=None):
        self.frames = frames
        self.blocks = deque()
        self.current = b''
        self.offset = 0
        self.priming = True
        self.paused = False
        self.expect_audio = False
        self.gaps = self.missing_frames = 0
        self.in_gap = False
        self.device = None
        self.callback_error = None
        self.callback_count = self.late_callbacks = 0
        self.max_callback_interval = 0.0
        self.last_callback = None
        self.device_name = device_name
        if open_device:
            self.open_output()

    def open_output(self):
        """Reattach a closed stream without changing queued PCM or pause state."""
        _pause_function()  # validate the safe control path before opening SDL
        from pygame._sdl2 import AudioDevice, AUDIO_S16, init_subsystem, INIT_AUDIO
        init_subsystem(INIT_AUDIO)
        self.device = AudioDevice(self.device_name, False, 48000, AUDIO_S16, 1,
                                  self.frames, 0, self.callback)
        self.last_callback = None
        if not self.priming and not self.paused:
            pause_device(self.device, False)

    def callback(self, device, stream):
        try:
            now = perf_counter()
            if self.expect_audio and not self.paused and not self.priming:
                if self.last_callback is not None:
                    interval = now - self.last_callback
                    self.max_callback_interval = max(self.max_callback_interval, interval)
                    self.late_callbacks += int(interval > self.frames / 48000 * 1.5)
                self.last_callback = now
                self.callback_count += 1
            else:
                self.last_callback = None
            self._fill(stream)
        except Exception as exc:
            # An SDL callback exception otherwise only reaches a disappearing
            # console. Silence its buffer and persist the complete traceback.
            from sidpulse.diagnostics import record_exception
            if self.callback_error is None:
                self.callback_error = exc
                record_exception('Audio callback failed', exc)
            memoryview(stream).cast('B')[:] = bytes(len(stream))

    def _fill(self, stream):
        target = memoryview(stream).cast('B')
        written = 0
        while written < len(target):
            if self.offset == len(self.current):
                try:
                    self.current = self.blocks.popleft()
                    self.offset = 0
                except IndexError:
                    target[written:] = bytes(len(target)-written)
                    if not self.priming and not self.paused and self.expect_audio:
                        self.gaps += int(not self.in_gap)
                        self.missing_frames += (len(target)-written)//2
                        self.in_gap = True
                    return
            count = min(len(target)-written, len(self.current)-self.offset)
            target[written:written+count] = self.current[self.offset:self.offset+count]
            written += count
            self.offset += count
            self.in_gap = False

    def needs_block(self):
        return len(self.blocks) < 2

    def write(self, pcm):
        if len(pcm) != self.frames * 2:
            raise ValueError('PCM block must match the selected audio buffer')
        self.blocks.append(pcm)
        if self.priming and len(self.blocks) >= 2:
            self.priming = False
            if self.device and not self.paused:
                pause_device(self.device, False)

    def stop(self):
        if self.device:
            pause_device(self.device, True)
        self.blocks.clear()
        self.current = b''
        self.offset = 0
        self.priming = True
        self.in_gap = False
        self.paused = False
        self.last_callback = None

    def pause(self):
        self.paused = True
        self.last_callback = None
        if self.device:
            pause_device(self.device, True)

    def unpause(self):
        self.paused = False
        if self.device and not self.priming:
            pause_device(self.device, False)

    def reset_stats(self):
        self.gaps = self.missing_frames = 0
        self.in_gap = False
        self.callback_count = self.late_callbacks = 0
        self.max_callback_interval = 0.0
        self.last_callback = None

    def close(self):
        if self.device:
            close_device(self.device)
            self.device = None
