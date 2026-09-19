"""Look ahead to scheduled triggers for a real-SID ADSR hard restart.

The SID rate counter is not reset by a GATE edge. Give a zero-rate release
at least 40 ms before a new attack, using ordinary SID register writes.
The probe advances musical ticks only; it neither renders nor changes a song.
"""
from copy import copy, deepcopy
from dataclasses import replace

from sidpulse.playback.voices import VoicePrograms


class ProbeSID:
    def __init__(self, sid):
        self.registers = bytearray(sid.registers)
        self.sample_rate = sid.sample_rate
        self.clock_hz = getattr(sid, 'clock_hz', 985248)
        self.triggered = set()
        self.last_register = 0

    def write(self, register, value):
        self.registers[register] = value
        self.last_register = register

    def clock(self, cycles):
        # note_on emits its gate-settling token immediately after GATE low.
        if self.last_register in (4, 11, 18):
            self.triggered.add(self.last_register // 7)


def prepare_restarts(seq):
    if all(v.instrument is None or v.restarting for v in seq.programs.voices):
        return
    future = copy(seq)
    future._predicting = True
    future.activity = None  # future loop restarts must never publish real note activity
    future.monitor = None  # lookahead must never change the live preview mute mask
    if seq.restart_loop is not None:
        future.loop_override = seq.restart_loop
    future.sid = ProbeSID(seq.sid)
    future.programs = VoicePrograms(future.sid)
    future.programs.voices = [replace(v, memory=dict(v.memory), envelope=dict(v.envelope)) for v in seq.programs.voices]
    future.filter = deepcopy(seq.filter)
    future.notes, future.instruments = list(seq.notes), list(seq.instruments)
    seen = set()
    lead_frames = seq.sid.sample_rate * 40 // 1000
    for _ in range(8):  # even at tempo 255, five ticks span 40 ms
        future.frames = int(future.next_tick)
        elapsed = future.frames - seq.frames
        future.sid.triggered.clear()
        future._boundary()
        if elapsed >= lead_frames:
            for voice in future.sid.triggered - seen:
                seq.programs.prepare_restart(voice)
            return
        seen.update(future.sid.triggered)
        if future.status != 'playing':
            return
