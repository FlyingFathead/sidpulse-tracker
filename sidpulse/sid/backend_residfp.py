"""Only this adapter depends on pyresidfp's pinned native extension API."""
from array import array
from collections import deque
import math

PAL_CLOCK = 985248
NTSC_CLOCK = 1022727
CLOCKS = {"PAL": PAL_CLOCK, "NTSC": NTSC_CLOCK}
SAMPLE_RATE = 48000


def frequency(note, clock_hz=PAL_CLOCK):
    # C-0 = 16.3516 Hz, A-4 = 440 Hz. PAL SID accumulator is 24 bits.
    hz = 440.0 * 2.0 ** ((note - 57) / 12)
    return min(65535, max(0, round(hz * (1 << 24) / clock_hz)))


class ReSIDfpBackend:
    def __init__(self, model="8580", sample_rate=SAMPLE_RATE, clock="PAL", voice_scopes=False):
        from pyresidfp._pyresidfp import ChipModel, SamplingMethod, SID
        self.models = {"6581": ChipModel.MOS6581, "8580": ChipModel.MOS8580}
        self.sample_rate = sample_rate
        self.clock_name = clock
        self.clock_hz = CLOCKS[clock]
        self.chip = SID(self.models[model], SamplingMethod.RESAMPLE, float(self.clock_hz), float(sample_rate))
        self.pending = deque()
        self.pending_frames = 0
        self.pending_offset = 0
        self.model = model
        self.registers = bytearray(25)
        self.muted = (False, False, False)
        self.voice_scopes = None
        if voice_scopes:
            self.enable_scopes(True)

    def enable_scopes(self, enabled):
        if enabled:
            from sidpulse.audio.scopes import VoiceScopes
            self.voice_scopes = VoiceScopes(self.model, self.clock_hz)
            self.voice_scopes.clock(self.clock_hz // 20)
            for register, value in enumerate(self.registers):
                self.voice_scopes.write(register, value)
        else:
            self.voice_scopes = None

    def reset(self):
        self.chip.reset()
        self.pending.clear()
        self.pending_frames = self.pending_offset = 0
        self.registers[:] = bytes(25)
        if self.voice_scopes is not None:
            self.voice_scopes.reset()

    def set_model(self, model):
        if model != self.model:
            self.chip.chip_model = self.models[model]
            self.model = model
            if self.voice_scopes is not None:
                self.voice_scopes.set_model(self.models[model])
            self.reset()

    def set_clock(self, clock):
        if clock != self.clock_name:
            model, rate, muted = self.model, self.sample_rate, self.muted
            self.__init__(model, rate, clock, voice_scopes=self.voice_scopes is not None)
            self.set_muted(muted)

    def write(self, register, value):
        if not 0 <= register < 25 or not 0 <= value <= 255:
            raise ValueError("SID writes need register 0..24 and byte 0..255")
        self.chip.write(register, value)
        self.registers[register] = value
        if self.voice_scopes is not None:
            self.voice_scopes.write(register, value)

    def set_muted(self, muted):
        """Preview-only waveform disconnect; keep GATE, phase and shadow writes.

        pyresidfp applies its mute mask on control-register writes, so rewrite
        the saved control immediately. No song/export register is modified.
        """
        if len(muted) != 3:
            raise ValueError("One SID has exactly three voices")
        self.muted = tuple(bool(value) for value in muted)
        for voice, enabled in enumerate(self.muted):
            self.chip.mute(voice, enabled)
            self.chip.write(voice * 7 + 4, self.registers[voice * 7 + 4])

    def clock(self, cycles):
        samples = self.chip.clock(cycles)
        if samples:
            self.pending.append(array('h', samples).tobytes())
            self.pending_frames += len(samples)
        if self.voice_scopes is not None:
            self.voice_scopes.clock(cycles)

    def render(self, frames):
        if not 0 <= frames <= self.sample_rate * 10:
            raise ValueError("Render in chunks of up to ten seconds")
        while self.pending_frames < frames:
            cycles = max(1, math.ceil((frames - self.pending_frames) * self.clock_hz / self.sample_rate))
            self.clock(cycles)
        # Native-endian signed int16, matching SDL AUDIO_S16SYS.
        # Copy contiguous blocks instead of a Python deque operation per sample.
        remaining = frames * 2
        out = bytearray()
        while remaining:
            block = self.pending[0]
            count = min(remaining, len(block) - self.pending_offset)
            out.extend(memoryview(block)[self.pending_offset:self.pending_offset + count])
            remaining -= count
            self.pending_offset += count
            if self.pending_offset == len(block):
                self.pending.popleft()
                self.pending_offset = 0
        self.pending_frames -= frames
        return bytes(out)


def set_filter(sid, state):
    sid.write(21, state.cutoff & 7)
    sid.write(22, state.cutoff >> 3)
    sid.write(23, state.resonance << 4 | state.routing)
    sid.write(24, state.mode | state.volume)


def note_on(sid, voice, note, instrument, hard_restart=False):
    base = voice * 7
    # Prepared registers also survive an order-list loop's logical reset.
    hard_restart = hard_restart or (sid.registers[base + 5] == 0 and sid.registers[base + 6] == 0)
    control = instrument.control
    sid.write(base + 4, control)
    # Let the native chip observe GATE low before retriggering it. Preserve
    # the samples from these cycles; no UI timer participates in this delay.
    sid.clock(32)
    freq = frequency(note, getattr(sid,"clock_hz",PAL_CLOCK))
    sid.write(base, freq & 255)
    sid.write(base + 1, freq >> 8)
    sid.write(base + 2, instrument.pulse_width & 255)
    sid.write(base + 3, instrument.pulse_width >> 8)
    if not hard_restart:
        sid.write(base + 5, instrument.attack << 4 | instrument.decay)
    sid.write(base + 4, control | 1)
    # Let the gate pipeline enter attack before restoring the release rate.
    sid.clock(32)
    if hard_restart:
        # Keep the prepared zero rates through the native GATE pipeline.
        # Restoring a slower release before this edge can reintroduce a wrap.
        sid.write(base + 5, instrument.attack << 4 | instrument.decay)
    sid.write(base + 6, instrument.sustain << 4 | instrument.release)


def note_off(sid, voice, cut=False):
    register = voice * 7 + 4
    # Cut disconnects all oscillator waveforms; off uses the SID release.
    sid.write(register, 0 if cut else sid.registers[register] & 0xFE)
