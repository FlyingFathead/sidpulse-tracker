"""Audio-clocked row automation recording, bounded to one pattern pass.

The UI sends slider values; the sequencer records every row it actually visits.
Only immutable snapshots cross to the UI. Lookahead never invokes this recorder.
"""
from dataclasses import dataclass
from sidpulse.playback.automation_parameters import PARAMETERS


@dataclass(frozen=True)
class PulseSnapshot:
    token: int
    pattern: int
    voice: int
    rows: tuple
    done: bool = False
    cancelled: bool = False
    reason: str = ''
    field: str = 'pulse_width'


class PulseRecording:
    def __init__(self, seq, token, voice, value, field='pulse_width'):
        self.field = field
        self.maximum = PARAMETERS[field][2]
        self.token, self.voice = token, voice
        self.pattern, self.order, self.loops = seq.pattern, seq.order, seq.loops
        self.value = max(0, min(self.maximum, int(value)))
        self.rows, self.before = {}, {}
        program = seq.programs.voices[voice]
        self.previous_override = program.pulse_width if field == 'pulse_width' else program.envelope.get(field)
        self.last_row = None
        self.done = False
        self.snapshot = PulseSnapshot(token, self.pattern, voice, (), field=field)
        if seq.status != 'playing':
            self.finish(seq, reason='Playback is not running')
        else:
            self.sample(seq)

    def publish(self, cancelled=False, reason=''):
        self.snapshot = PulseSnapshot(self.token, self.pattern, self.voice,
                                      tuple(self.rows.items()), self.done, cancelled, reason, self.field)

    def apply_override(self, seq, value):
        program = seq.programs.voices[self.voice]
        if self.field == 'pulse_width':
            program.pulse_width = value
        else:
            if value is None:program.envelope.pop(self.field, None)
            else:program.envelope[self.field] = value
            seq.programs.write_envelope(self.voice)

    def sample(self, seq, value=None, row_start=False):
        if self.done:
            return
        if seq.status != 'playing':
            self.finish(seq, reason='Playback stopped or paused')
            return
        if (seq.pattern, seq.order, seq.loops) != (self.pattern, self.order, self.loops) or (
                row_start and seq.frames > 0 and self.last_row is not None and seq.row <= self.last_row):
            self.finish(seq, reason='Pattern pass complete')
            return
        if value is not None:
            self.value = max(0, min(self.maximum, int(value)))
        cell = seq.song.patterns[self.pattern].rows[seq.row][self.voice]
        self.before.setdefault(seq.row, getattr(cell, self.field))
        changed = self.rows.get(seq.row) != self.value
        self.rows[seq.row] = self.value
        setattr(cell, self.field, self.value)
        self.apply_override(seq, self.value)
        self.last_row = seq.row
        if changed:
            self.publish()

    def finish(self, seq, cancel=False, reason='Touch released'):
        if self.done:
            return
        self.done = True
        if cancel:
            pattern = seq.song.patterns.get(self.pattern)
            if pattern:
                for row, value in self.before.items():
                    if row < len(pattern.rows):
                        setattr(pattern.rows[row][self.voice], self.field, value)
            self.apply_override(seq, self.previous_override)
        self.publish(cancel, reason)
