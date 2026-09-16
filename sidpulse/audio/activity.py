"""Bounded instrument-use telemetry. Does not measure audio or write SID registers.

IDs are captured at actual triggers, not instrument-memory rows or the UI cursor.
No PCM sample events are emitted: that playback engine is not implemented.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class ActivitySnapshot:
    generation: int = 0
    enabled: bool = False
    active: tuple[int, ...] = ()
    triggers: tuple[tuple[int, int], ...] = ()
    eligible: tuple[int, ...] = ()


class InstrumentActivity:
    def __init__(self):
        self.generation = 0
        self.serial = 0
        self.counts = {}  # (voice, instrument slot) -> most recent trigger serial

    def reset(self):
        self.generation += 1
        self.counts.clear()

    def note_on(self, voice, instrument):
        if type(voice) is not int or voice not in range(3):
            return
        if type(instrument) is not int or not 1 <= instrument <= 99:
            return
        self.serial += 1
        self.counts[(voice, instrument)] = self.serial

    def snapshot(self, programs, registers, muted=(False, False, False), enabled=True):
        counters = {}
        eligible = set()
        for (voice, instrument), serial in self.counts.items():
            counters[instrument] = max(counters.get(instrument, 0), serial)
            if not muted[voice]:
                eligible.add(instrument)
        active = set()
        enabled = bool(enabled and registers[24] & 15)
        if enabled:
            for voice, state in enumerate(programs.voices):
                number = state.instrument_id
                control = registers[voice*7+4]
                if (type(number) is int and 1 <= number <= 99 and state.note is not None and state.gate
                        and control & 0xF0 and not muted[voice]):
                    # Include short ADSR hard-restart preparation in assigned
                    # voice activity; it should not flicker away between notes.
                    active.add(number)
                    eligible.add(number)
        return ActivitySnapshot(self.generation, enabled, tuple(sorted(active)),
                                tuple(sorted(counters.items())), tuple(sorted(eligible)))
