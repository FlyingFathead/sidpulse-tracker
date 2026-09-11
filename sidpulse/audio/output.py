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
        for i, x in enumerate(samples):
            if self.previous_x is None:
                self.previous_x = x
            y = x - self.previous_x + self.coefficient * self.previous_y
            self.previous_x, self.previous_y = x, y
            self.gain += max(-self.step, min(self.step, self.target - self.gain))
            samples[i] = max(-32768, min(32767, round(y * self.gain)))
        return samples.tobytes()
