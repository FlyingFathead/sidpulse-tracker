"""Isolated native voice monitors; these never feed the audible output.

The public pyresidfp API exposes only mixed PCM. Three display-only native
copies receive the SID register/cycle stream and isolate one voice each.
They sample at 12 kHz without the shared filter, only while Info is visible.
"""
from collections import deque


class VoiceScopes:
    def __init__(self, model, clock_hz):
        from pyresidfp._pyresidfp import SID, ChipModel, SamplingMethod
        chip_model = ChipModel.MOS6581 if model == '6581' else ChipModel.MOS8580
        self.chips = [SID(chip_model, SamplingMethod.DECIMATE, float(clock_hz), 12000.0)
                      for _ in range(3)]
        self.samples = [deque(maxlen=256) for _ in range(3)]
        for voice, chip in enumerate(self.chips):
            chip.enable_filter(False)
            for other in range(3):
                chip.mute(other, other != voice)

    def reset(self):
        for voice, chip in enumerate(self.chips):
            chip.reset()
            chip.enable_filter(False)
            for other in range(3):
                chip.mute(other, other != voice)
            self.samples[voice].clear()

    def set_model(self, model):
        for chip in self.chips:
            chip.chip_model = model

    def write(self, register, value):
        if register in (21, 22, 23):
            return  # raw voice monitors precede the shared filter
        if register == 24:
            value &= 15
        for voice, chip in enumerate(self.chips):
            isolated = value
            if register < 21 and register // 7 != voice:
                # Keep source oscillators running for sync/ring modulation,
                # but prevent other envelopes' analog DAC offsets leaking
                # into this voice's monitor, even with waveform mute applied.
                if register % 7 == 4:
                    isolated &= ~1
                elif register % 7 in (5, 6):
                    isolated = 0
            chip.write(register, isolated)

    def clock(self, cycles):
        for chip, samples in zip(self.chips, self.samples):
            samples.extend(chip.clock(cycles))

    def snapshot(self):
        result = []
        for samples in self.samples:
            if not samples:
                result.append((0.0,) * 128)
                continue
            values = tuple(samples)
            mean = sum(values) / len(values)
            result.append(tuple(max(-1., min(1., (v - mean) / 8192))
                                for v in values[::max(1, len(values) // 128)]))
        return tuple(result)
