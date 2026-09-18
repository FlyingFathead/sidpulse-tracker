"""Host PCM conditioning only; never modifies stored or emulated SID registers."""
from array import array
import math


class OutputConditioner:
    def __init__(self, sample_rate=48000):
        self.coefficient = math.exp(-2 * math.pi * 5 / sample_rate)
        self.previous_x = None
        self.previous_y = 0.0
        self.gain = 0.0
        self.target = 0.0
        self.step = 1 / (sample_rate * .005)  # 5 ms transport ramp, not a per-note fade

    def process(self, pcm):
        samples = array('h', pcm)
        # Keep the exact recurrence and rounding, but avoid repeated attribute
        # lookups and four Python min/max calls for every sample.
        previous_x, previous_y = self.previous_x, self.previous_y
        gain, target, step = self.gain, self.target, self.step
        coefficient = self.coefficient
        for i, x in enumerate(samples):
            if previous_x is None:
                previous_x = x
            y = x - previous_x + coefficient * previous_y
            previous_x, previous_y = x, y
            if gain != target:
                delta = target - gain
                gain += -step if delta < -step else step if delta > step else delta
            value = round(y * gain)
            samples[i] = -32768 if value < -32768 else 32767 if value > 32767 else value
        self.previous_x, self.previous_y, self.gain = previous_x, previous_y, gain
        return samples.tobytes()
