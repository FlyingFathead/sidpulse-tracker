"""Output changes and temporary test audio, owned only by the audio worker."""
from array import array
import math
from functools import lru_cache

from sidpulse.preferences import BUFFERS, valid_output_device


def output_devices():
    from pygame._sdl2 import get_audio_device_names, init_subsystem, INIT_AUDIO
    init_subsystem(INIT_AUDIO)
    return tuple(dict.fromkeys(get_audio_device_names(False)))


@lru_cache(maxsize=1)
def test_arpeggio():
    """A quiet C-E-G-C diagnostic, sample-clocked with 8 ms edge fades.

    This does not touch SID registers, project instruments or the sequencer.
    The final silent tail lets the final note reach the output before restoring.
    """
    samples = array('h')
    duration, fade = 12000, 384
    for note in (60, 64, 67, 72):
        frequency = 440 * 2 ** ((note - 69) / 12)
        for i in range(duration):
            envelope = min(1., i / fade, (duration - 1 - i) / fade)
            samples.append(round(4096 * envelope * math.sin(2 * math.pi * frequency * i / 48000)))
    samples.extend([0] * 4800)
    return samples.tobytes()


class AudioOutput:
    def __init__(self, frames, device_name=None):
        self.devices = ()
        self.notice = ''
        self.list_error = ''
        self.saved = None
        self.test_pcm = b''
        self.test_offset = 0
        self.test_stream = None
        test_arpeggio()  # prepare once before any live callback; testing never synthesizes in it
        self.refresh()
        self.device_name = device_name
        try:
            self.validate(frames, device_name)
            self.channel = self._new(frames, device_name)
        except Exception as exc:
            if device_name is None:
                raise
            self.device_name = None
            self.channel = self._new(frames, None)
            self.notice = f'Saved output unavailable; using system default: {exc}'

    @staticmethod
    def _new(frames, name):
        from sidpulse.audio.stream import PCMStream
        return PCMStream(frames) if name is None else PCMStream(frames, device_name=name)

    def refresh(self):
        try:
            self.devices = output_devices()
            self.list_error = ''
        except Exception as exc:
            self.list_error = f'Cannot list outputs: {exc}'

    def validate(self, frames, name):
        if frames not in BUFFERS or not valid_output_device(name):
            raise ValueError('Invalid audio output settings')
        if name is not None:
            self.refresh()
            if name not in self.devices:
                raise ValueError(f'Output unavailable: {name}')

    @property
    def testing(self):
        return self.saved is not None

    def _restore(self, channel, name):
        self.channel, self.device_name = channel, name
        try:
            channel.open_output()
        except Exception:
            if name is None:
                raise
            channel.device_name = None
            channel.open_output()
            self.device_name = None
            self.notice = 'Previous output unavailable; using system default.'

    def switch(self, frames, name):
        self.stop_test()
        self.validate(frames, name)
        if (frames, name) == (self.channel.frames, self.device_name):
            return
        old, previous = self.channel, self.device_name
        old.close()  # retain the old queue until opening the replacement succeeds
        try:
            new = self._new(frames, name)
        except Exception:
            self._restore(old, previous)
            raise
        # Counters describe the session, including before a device change.
        for key in ('gaps', 'missing_frames', 'callback_count', 'late_callbacks',
                    'max_callback_interval'):
            setattr(new, key, getattr(old, key))
        if old.paused:
            new.pause()
        self.channel, self.device_name = new, name
        self.notice = ''

    def start_test(self, frames, name):
        self.stop_test()
        self.validate(frames, name)
        pcm = test_arpeggio()
        old, previous = self.channel, self.device_name
        old.close()
        try:
            test = self._new(frames, name)
        except Exception:
            self._restore(old, previous)
            raise
        self.saved = (old, previous)
        self.test_stream = test
        test.expect_audio = True
        self.test_pcm, self.test_offset = pcm, 0
        # Only the diagnostic stream advances. The live SID and queued PCM wait.

    def pump_test(self):
        if not self.testing:
            return False
        test = self.test_stream
        if test.callback_error is not None:
            self.stop_test()
            raise RuntimeError('Test audio callback failed')
        if self.test_offset < len(self.test_pcm) and test.needs_block():
            size = test.frames * 2
            block = self.test_pcm[self.test_offset:self.test_offset + size]
            self.test_offset += len(block)
            test.write(block.ljust(size, b'\x00'))
            if self.test_offset == len(self.test_pcm):
                # The final padded/silent tail is an intentional end, not starvation.
                test.expect_audio = False
        elif self.test_offset >= len(self.test_pcm) and not test.blocks and test.offset == len(test.current):
            self.stop_test()
        return True

    def stop_test(self):
        if self.saved is None:
            return
        self.test_stream.close()
        old, name = self.saved
        for key in ('gaps', 'missing_frames', 'callback_count', 'late_callbacks'):
            setattr(old, key, getattr(old, key) + getattr(self.test_stream, key))
        old.max_callback_interval = max(old.max_callback_interval, self.test_stream.max_callback_interval)
        self.saved = None
        self.test_stream = None
        self.test_pcm = b''
        self._restore(old, name)

    def close(self):
        # Shutdown must not reopen an output just to close it again.
        if self.test_stream is not None:
            self.test_stream.close()
        self.channel.close()
