"""Optional host PCM instruments. Pure SID songs keep the original render path."""
from dataclasses import replace

from sidpulse.playback.voices import VoicePrograms, Audition


def enabled(song):
    return any(inst.sample_override for inst in song.instruments.values())


def programs(sid, song, activity=None, monitor=None):
    if enabled(song):
        return SamplePrograms(sid, activity, monitor, samples=song.samples)
    return VoicePrograms(sid, activity, monitor)


def audition(sid, song, activity=None, monitor=None):
    if enabled(song):
        return SampleAudition(sid, song.tempo, activity, monitor, samples=song.samples)
    return Audition(sid, song.tempo, activity, monitor)


class SamplePrograms(VoicePrograms):
    def __init__(self, sid, activity=None, monitor=None, *, samples=None):
        super().__init__(sid, activity, monitor)
        import numpy as np
        self.np = np
        self.samples = samples or {}
        self.pcm = [None] * 3
        self.cache = {}
        self.positions = {}

    def trigger(self, voice, note, inst, instrument_id=None):
        self.pcm[voice] = None
        if inst.sample_override:
            from sidpulse.audio.media import sample_data, sample_bounds
            source = self.samples.get(str(inst.sample_slot), self.samples.get(inst.sample_slot))
            # An unassigned/missing override is silent, never a surprise SID fallback.
            if source is None:
                self.release(voice, cut=True)
                return
            key = inst.sample_slot
            cached = self.cache.get(key)
            if cached is None or cached[0] is not source:
                start, end = sample_bounds(source)
                data = self.np.frombuffer(sample_data(source), '<i2')[start:end].astype(self.np.float64)
                cached = self.cache[key] = (source, data)
            self.pcm[voice] = dict(data=cached[1], position=0., step=1.,
                                   rate=source['sample_rate'], root=source.get('root_note', 48),
                                   gain=inst.sample_gain / 100)
            # Keep tick pitch/arp/vibrato/retrigger semantics but disconnect the
            # SID oscillator; ADSR and filter intentionally do not shape host PCM.
            inst = replace(inst, waveform=0, wave_sequence_enabled=False, sync=False, ring=False)
        super().trigger(voice, note, inst, instrument_id)
        self._pitch(voice)

    def _pitch(self, voice):
        state = self.pcm[voice]
        if state is not None:
            regs = self.sid.registers
            freq = regs[voice * 7] | regs[voice * 7 + 1] << 8
            state['step'] = state['rate'] / self.sid.sample_rate * freq / max(1, self.frequency(state['root']))

    def tick(self, tick):
        super().tick(tick)
        for voice in range(3):
            self._pitch(voice)

    def prepare_restart(self, voice):
        # SID envelope lookahead must not prematurely stop a PCM one-shot.
        if self.pcm[voice] is None:
            super().prepare_restart(voice)

    def release(self, voice, cut=False):
        self.pcm[voice] = None
        super().release(voice, cut)

    def render(self, frames):
        raw = self.sid.render(frames)
        if not any(state is not None for state in self.pcm):
            return raw
        np = self.np
        mixed = np.frombuffer(raw, np.int16).astype(np.float64)
        offsets = self.positions.get(frames)
        if offsets is None:
            if len(self.positions) >= 32:
                self.positions.clear()
            offsets = self.positions[frames] = np.arange(frames, dtype=np.float64)
        muted = getattr(self.sid, 'muted', (False,) * 3)
        volume = (self.sid.registers[24] & 15) / 15
        for voice, state in enumerate(self.pcm):
            if state is None:
                continue
            positions = state['position'] + offsets * state['step']
            count = int(np.searchsorted(positions, len(state['data']), side='left'))
            if count and not muted[voice]:
                points = positions[:count]
                indexes = points.astype(np.intp)
                fraction = points - indexes
                values = state['data'][indexes]
                following = state['data'][np.minimum(indexes + 1, len(state['data']) - 1)]
                mixed[:count] += (values + (following - values) * fraction) * state['gain'] * volume
            state['position'] += frames * state['step']
            if state['position'] >= len(state['data']):
                self.pcm[voice] = None
        return np.clip(np.rint(mixed), -32768, 32767).astype(np.int16).tobytes()


class SampleAudition(SamplePrograms, Audition):
    def __init__(self, sid, tempo=125, activity=None, monitor=None, *, samples=None):
        # Explicit initialization avoids Audition's different positional signature.
        VoicePrograms.__init__(self, sid, activity, monitor)
        import numpy as np
        self.np, self.samples = np, samples or {}
        self.pcm, self.cache, self.positions = [None] * 3, {}, {}
        self.tempo, self.remaining, self.fraction = tempo, 0, 0.

    def render(self, frames):
        out = bytearray()
        while frames:
            if not self.remaining:
                self.tick(0)
                self.fraction += self.sid.sample_rate * 2.5 / self.tempo
                self.remaining = int(self.fraction)
                self.fraction -= self.remaining
            count = min(frames, self.remaining)
            out.extend(SamplePrograms.render(self, count))
            self.remaining -= count
            frames -= count
        return bytes(out)
