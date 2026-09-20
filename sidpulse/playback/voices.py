"""SID-native tick programs shared by song playback, keyboard jazz and export.

IT letter meanings are retained. Pitch slide magnitudes are SID frequency
register units (normal/fine x4, extra-fine x1); vibrato depth is 1/16 semitone.
"""
from copy import deepcopy
from dataclasses import dataclass, field, replace
import math

from sidpulse.sid.backend_residfp import frequency, note_on, note_off, PAL_CLOCK
from sidpulse.song.model import OFF, CUT, ENVELOPE_FIELDS


def supported(effect, value):
    if not effect or effect in 'ABCEFGHJT':
        return effect != 'T' or value >= 0x20
    if effect == 'Q':
        return value < 0x10  # gate retrigger only; no fictional per-voice volume
    if effect == 'S':
        return value >> 4 in (0xC, 0xD)
    if effect == 'Z':
        return value in (0x10, 0x11, 0x1F, 0x20, 0x21, 0x2F)
    return False


@dataclass
class Voice:
    note: int | None = None
    instrument: object = None
    age: int = 0
    freq: int = 0
    target: int = 0
    phase: int = 0
    effect: str = ''
    parameter: int = 0
    memory: dict = field(default_factory=dict)
    delayed: object = None
    gate: bool = False
    restarting: bool = False
    instrument_id: int | None = None
    pulse_width: int | None = None
    envelope: dict = field(default_factory=dict)
    arp_override: bool | None = None
    arp_enabled: bool = True
    waveform_override: int | None = None
    sync_override: bool | None = None
    ring_override: bool | None = None


class VoicePrograms:
    def __init__(self, sid, activity=None, monitor=None):
        self.sid = sid
        self.activity = activity
        self.monitor = monitor
        self.voices = [Voice() for _ in range(3)]

    def frequency(self, note):
        return frequency(note, getattr(self.sid,"clock_hz",PAL_CLOCK))

    def write(self, register, value):
        value = int(value)
        if self.sid.registers[register] != value:
            self.sid.write(register, value)

    def trigger(self, voice, note, inst, instrument_id=None):
        v = self.voices[voice]
        # A transport/loop reset replaces Voice objects, but the chip may
        # already hold the settled zero envelope from startup or lookahead.
        base = voice * 7
        prepared = v.restarting or self.sid.registers[base + 5:base + 7] == bytes(2)
        v.note, v.instrument, v.age = note, deepcopy(inst), 0
        v.instrument_id = instrument_id
        if self.monitor is not None:
            self.monitor(voice, instrument_id)
        v.freq = v.target = self.frequency(note)
        v.phase, v.gate = 0, True
        v.restarting = False
        v.arp_enabled = inst.arpeggio_enabled if v.arp_override is None else v.arp_override
        pitch = (inst.arpeggio[0] if v.arp_enabled and inst.arpeggio else 0) + (inst.pitch_sequence[0] if inst.pitch_sequence_enabled and inst.pitch_sequence else 0)
        initial = replace(inst, waveform=inst.wave_sequence[0] if inst.wave_sequence_enabled and inst.wave_sequence else inst.waveform,
                          pulse_width=inst.pulse_width if v.pulse_width is None else v.pulse_width,
                          **v.envelope)
        if not inst.sample_override:
            if v.waveform_override is not None:initial.waveform = v.waveform_override
            if v.sync_override is not None:initial.sync = v.sync_override
            if v.ring_override is not None:initial.ring = v.ring_override
        note_on(self.sid, voice, note+pitch, initial, hard_restart=prepared)
        if self.activity is not None:
            self.activity.note_on(voice, instrument_id)

    def prepare_restart(self, voice):
        v = self.voices[voice]
        if v.instrument is None or v.restarting:
            return
        v.restarting = True
        base = voice * 7
        self.write(base + 4, self.sid.registers[base + 4] & 0xFE)
        self.write(base + 5, 0)
        self.write(base + 6, 0)

    def release(self, voice, cut=False):
        v = self.voices[voice]
        note_off(self.sid, voice, cut)
        v.gate = False
        if cut:
            v.note = None

    def row(self, voice, cell, inst, instrument_id=None):
        v = self.voices[voice]
        if cell.waveform is not None:
            v.waveform_override = None if cell.waveform == -1 else cell.waveform
        if cell.effect == 'Z' and cell.parameter in (0x10, 0x11, 0x1F, 0x20, 0x21, 0x2F):
            field = 'sync_override' if cell.parameter >> 4 == 1 else 'ring_override'
            mode = cell.parameter & 15
            setattr(v, field, None if mode == 15 else bool(mode))
        if cell.arp_mode is not None:
            v.arp_override = None if cell.arp_mode == -1 else bool(cell.arp_mode)
            active = v.instrument or inst
            v.arp_enabled = active.arpeggio_enabled if v.arp_override is None else v.arp_override
        if cell.pulse_width is not None:
            v.pulse_width = None if cell.pulse_width == -1 else cell.pulse_width
        for field in ENVELOPE_FIELDS:
            value = getattr(cell, field)
            if value == -1:
                v.envelope.pop(field, None)
            elif value is not None:
                v.envelope[field] = value
        if any(getattr(cell, field) is not None for field in ENVELOPE_FIELDS):
            self.write_envelope(voice)
        effect, value = cell.effect, cell.parameter or 0
        if effect in ('E','F','G','H','J','Q'):
            previous = v.memory.get(effect,0)
            if effect == 'H':
                value = (value & 0xF0 or previous & 0xF0) | (value & 15 or previous & 15)
            elif value == 0:
                value = previous
            v.memory[effect] = value
        v.effect, v.parameter, v.delayed = effect, value, None
        if effect == 'S' and value >> 4 == 0xD and value & 15:
            v.delayed = (cell.note,deepcopy(inst),instrument_id)
            return
        if cell.note == OFF:
            self.release(voice)
        elif cell.note == CUT:
            self.release(voice,True)
        elif cell.note is not None:
            if effect == 'G' and v.note is not None and v.gate:
                v.target = self.frequency(cell.note)  # no gate/instrument restart
            else:
                self.trigger(voice,cell.note,inst,instrument_id)

    def write_envelope(self, voice):
        v = self.voices[voice]
        if v.instrument is None or v.restarting:
            return
        a, d, s, r = (v.envelope.get(field, getattr(v.instrument, field)) for field in ENVELOPE_FIELDS)
        self.write(voice * 7 + 5, a << 4 | d)
        self.write(voice * 7 + 6, s << 4 | r)

    def tick(self, tick):
        for voice,v in enumerate(self.voices):
            effect,value=v.effect,v.parameter
            hi,lo=value>>4,value&15
            if effect=='S' and hi==0xD and tick==lo and v.delayed:
                note,inst,instrument_id=v.delayed
                if note==OFF:self.release(voice)
                elif note==CUT:self.release(voice,True)
                elif note is not None:self.trigger(voice,note,inst,instrument_id)
                v.delayed=None
            if effect=='S' and hi==0xC and tick==lo:
                self.release(voice,True)
            if v.note is None or v.instrument is None:
                continue
            inst=v.instrument
            retrigger=(lo if effect=='Q' and hi==0 else 0)
            if v.gate and ((retrigger and tick>0 and tick%retrigger==0) or
                           (inst.retrigger_enabled and inst.retrigger and v.age>=inst.retrigger)):
                self.trigger(voice,v.note,inst,v.instrument_id)
            if inst.gate_enabled and inst.gate_ticks and v.age>=inst.gate_ticks and v.gate:
                self.release(voice)
            if effect in ('E','F'):
                amount = lo*(1 if hi==0xE else 4) if hi in (0xE,0xF) and tick==0 else (value*4 if hi<0xE and tick>0 else 0)
                v.freq=max(0,min(65535,v.freq+amount*(1 if effect=='F' else -1)))
            elif effect=='G' and tick>0:
                amount=value*4
                v.freq=min(v.target,v.freq+amount) if v.freq<v.target else max(v.target,v.freq-amount)
            pitch=inst.arpeggio[(v.age//inst.arp_speed)%len(inst.arpeggio)] if v.arp_enabled and inst.arpeggio else 0
            if effect=='J' and value and v.arp_override is not False:
                pitch=(0,hi,lo)[tick%3]  # row command replaces instrument arp
            if inst.pitch_sequence_enabled and inst.pitch_sequence:
                pitch+=inst.pitch_sequence[min(v.age,len(inst.pitch_sequence)-1)]
            speed,depth=(hi,lo) if effect=='H' else (inst.vibrato_speed,inst.vibrato_depth) if inst.vibrato_enabled else (0,0)
            if (effect=='H' or v.age>=inst.vibrato_delay) and speed and depth:
                pitch += math.sin(v.phase*math.tau/256)*depth/16
                v.phase=(v.phase+speed*4)%256
            freq=max(0,min(65535,round(v.freq*2**(pitch/12))))
            base=voice*7
            self.write(base,freq&255);self.write(base+1,freq>>8)
            wave=inst.wave_sequence[min(v.age,len(inst.wave_sequence)-1)] if inst.wave_sequence_enabled and inst.wave_sequence else inst.waveform
            sync,ring=inst.sync,inst.ring
            if not inst.sample_override:
                if v.waveform_override is not None:wave=v.waveform_override
                if v.sync_override is not None:sync=v.sync_override
                if v.ring_override is not None:ring=v.ring_override
            control=wave|(2 if sync else 0)|(4 if ring else 0)|int(v.gate and not v.restarting)
            self.write(base+4,control)
            phase=v.age%(4*inst.pulse_rate)
            # Triangle starts at centre, then rises/falls smoothly.
            triangle=(phase if phase<=inst.pulse_rate else 2*inst.pulse_rate-phase if phase<=3*inst.pulse_rate else phase-4*inst.pulse_rate)/inst.pulse_rate
            pw_base = inst.pulse_width if v.pulse_width is None else v.pulse_width
            pw=max(0,min(4095,round(pw_base+(inst.pulse_depth*triangle if inst.pulse_enabled else 0))))
            self.write(base+2,pw&255);self.write(base+3,pw>>8)
            v.age+=1


class Audition(VoicePrograms):
    """Free keyboard notes use the same instrument programs at song-tempo ticks."""
    def __init__(self,sid,tempo=125,activity=None,monitor=None):
        super().__init__(sid,activity,monitor)
        self.tempo=tempo
        self.remaining=0
        self.fraction=0.0

    def render(self,frames):
        out=bytearray()
        while frames:
            if not self.remaining:
                self.tick(0)
                self.fraction += self.sid.sample_rate*2.5/self.tempo
                self.remaining=int(self.fraction)
                self.fraction -= self.remaining
            count=min(frames,self.remaining)
            out.extend(self.sid.render(count))
            self.remaining-=count;frames-=count
        return bytes(out)
