"""Deterministic tracker transport. Rendering PCM advances time; UI frames don't.

Voice/instrument programs and shared filter rows use the same register path
as PSID compilation. Unsupported row commands remain stored and reported.
"""
from copy import deepcopy
from dataclasses import dataclass
from fractions import Fraction

from sidpulse.sid.backend_residfp import note_on, note_off, set_filter
from sidpulse.song.model import OFF, CUT
from sidpulse.playback.voices import VoicePrograms, supported


@dataclass(frozen=True)
class PlaybackState:
    status: str = 'stopped'
    mode: str = 'song'
    order: int = 0
    pattern: int = 0
    row: int = 0
    tick: int = 0
    speed: int = 6
    tempo: int = 125
    frames: int = 0
    loops: int = 0
    notes: tuple = (None, None, None)
    instruments: tuple = (1, 1, 1)
    warning: str = ''


class Sequencer:
    def __init__(self, sid, activity=None):
        self.sid = sid
        self.activity = activity
        self.programs = VoicePrograms(sid, self.activity)
        self.filter = None
        self.filter_slide = 0
        self.song = None
        self.pending_song = None
        self.status = 'stopped'
        self.mode = 'song'
        self.loop_override = None
        self.restart_loop = None
        self._predicting = False
        self.order = self.pattern = self.row = self.tick = self.frames = self.loops = 0
        self.speed, self.tempo = 6, 125
        self.notes = [None] * 3
        self.instruments = [1] * 3
        self.warning = ''
        self.next_tick = Fraction(0)
        self.jump_order = self.break_row = None

    @property
    def state(self):
        return PlaybackState(self.status, self.mode, self.order, self.pattern, self.row,
                             self.tick, self.speed, self.tempo, self.frames, self.loops,
                             tuple(self.notes), tuple(self.instruments), self.warning)

    def start(self, song, mode='song', order=0, row=0, pattern=None, loop=None):
        self.loop_override = loop
        for voice in range(3):
            note_off(self.sid, voice, cut=True)
        self.programs = VoicePrograms(self.sid, self.activity)
        self.filter = deepcopy(song.filter)
        self.filter_slide = 0
        set_filter(self.sid,self.filter)
        self.song, self.pending_song = song, None  # caller owns an isolated snapshot
        self.mode = mode
        self.order = max(0, min(order, len(song.orders) - 1))
        self.pattern = song.orders[self.order] if pattern is None else pattern
        if self.pattern not in song.patterns:
            self.pattern = song.orders[self.order]
        self.row = max(0, min(row, len(song.patterns[self.pattern].rows) - 1))
        self.speed, self.tempo = song.speed, song.tempo
        self.tick = self.frames = self.loops = 0
        self.next_tick = Fraction(0)
        self.jump_order = self.break_row = None
        self.notes = [None] * 3
        self.instruments = [min(song.instruments, default=1)] * 3
        self.warning = ''
        self.status = 'playing'

    def stop(self):
        self.status = 'stopped'
        for voice in range(3):
            note_off(self.sid, voice, cut=True)
        self.notes = [None] * 3

    def pause(self):
        if self.status == 'playing':
            self.status = 'paused'
        elif self.status == 'paused':
            self.status = 'playing'

    def update_song(self, song):
        self.pending_song = song

    def _apply_update(self):
        if self.pending_song is None:
            return
        new, self.pending_song = self.pending_song, None
        if new.speed != self.song.speed:
            self.speed = new.speed
        if new.tempo != self.song.tempo:
            self.tempo = new.tempo
        if new.filter != self.song.filter:
            self.filter=deepcopy(new.filter)
            set_filter(self.sid,self.filter)
        self.song = new
        self.order = min(self.order, len(new.orders) - 1)
        if self.mode == 'song' or self.pattern not in new.patterns:
            self.pattern = new.orders[self.order]
        self.row = min(self.row, len(new.patterns[self.pattern].rows) - 1)

    def _row_start(self):
        self._apply_update()
        self.jump_order = self.break_row = None
        cells = self.song.patterns[self.pattern].rows[self.row]
        for voice, cell in enumerate(cells):
            if cell.instrument is not None:
                self.instruments[voice] = cell.instrument
            instrument = self.song.instruments.get(self.instruments[voice])
            if instrument is None:
                from sidpulse.playback.voices import Voice
                self.programs.release(voice, cut=True)
                self.programs.voices[voice] = Voice()
            else:
                self.programs.row(voice, cell, instrument, self.instruments[voice])
            if cell.note in (OFF,CUT):
                self.notes[voice] = None
            elif cell.note is not None:
                self.notes[voice] = cell.note
            effect, value = cell.effect, cell.parameter or 0
            if effect == 'A':
                if value:
                    self.speed = value
            elif effect == 'B':
                self.jump_order = value
            elif effect == 'C':
                self.break_row = value
            elif effect == 'T' and value >= 0x20:
                self.tempo = value
            elif not supported(effect,value):
                self.warning = f'{effect}{value:02X} stored but not executed in this build'

        control=self.song.patterns[self.pattern].controls.get(self.row)
        if control:
            for key in ("cutoff","resonance","routing","mode","volume"):
                value=getattr(control,key)
                if value is not None:setattr(self.filter,key,value)
            if control.slide is not None:self.filter_slide=control.slide
            set_filter(self.sid,self.filter)

    def _advance_row(self):
        if self.mode == 'pattern':
            if self.jump_order is not None or self.break_row is not None:
                self.row = self.break_row or 0
                self.loops += 1
            else:
                self.row += 1
                if self.row >= len(self.song.patterns[self.pattern].rows):
                    self.row = 0
                    self.loops += 1
        elif self.jump_order is not None or self.break_row is not None:
            self.order = self.jump_order if self.jump_order is not None else self.order + 1
            self.row = self.break_row or 0
        else:
            self.row += 1
            if self.row >= len(self.song.patterns[self.pattern].rows):
                self.row = 0
                self.order += 1
        if self.mode == 'song':
            # Use a loop edit received during the final row at this boundary,
            # before _row_start applies other queued changes. One-pass overrides win.
            boundary_song = self.pending_song if self.pending_song is not None else self.song
            if self.order >= len(self.song.orders) and (boundary_song.export_config.get("loop",True) if self.loop_override is None else self.loop_override):
                # Restart musical state, preserving elapsed sample time. This is
                # the same initialization record replayed by the exported loop.
                elapsed, loops, boundary = self.frames, self.loops+1, self.next_tick
                self.start(boundary_song, loop=self.loop_override)
                self.frames, self.loops, self.next_tick = elapsed, loops, boundary
                return
            if self.order >= len(self.song.orders):
                self.order = len(self.song.orders) - 1
                self.pattern = self.song.orders[self.order]
                self.row = len(self.song.patterns[self.pattern].rows) - 1
                self.stop()
                return
            self.pattern = self.song.orders[self.order]
        if self.row >= len(self.song.patterns[self.pattern].rows):
            self.row = 0

    def _boundary(self):
        if self.frames:
            self.tick += 1
            if self.tick >= self.speed:
                self.tick = 0
                self._advance_row()
        if self.status != 'playing':
            return
        if self.tick == 0:
            self._row_start()
        self.programs.tick(self.tick)
        if self.filter_slide:
            self.filter.cutoff=max(0,min(2047,self.filter.cutoff+self.filter_slide))
            self.programs.write(21,self.filter.cutoff&7)
            self.programs.write(22,self.filter.cutoff>>3)
        # Accumulate fractions, never round each tick independently.
        self.next_tick += Fraction(self.sid.sample_rate * 5, self.tempo * 2)
        if not self._predicting:
            from sidpulse.playback.restart import prepare_restarts
            prepare_restarts(self)

    def render(self, frames):
        if self.status == 'paused':
            return bytes(frames * 2)  # no SID or tracker clock advance
        out = bytearray()
        while frames:
            if self.status != 'playing':
                out.extend(self.sid.render(frames))
                break
            if self.frames >= int(self.next_tick):
                self._boundary()
                if self.status != 'playing':
                    continue
            count = min(frames, int(self.next_tick) - self.frames)
            out.extend(self.sid.render(count))
            self.frames += count
            frames -= count
        # Publish state at an exact boundary without depending on next UI/chunk.
        if self.status == 'playing' and self.frames >= int(self.next_tick):
            self._boundary()
        return bytes(out)
