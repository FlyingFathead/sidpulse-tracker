"""Lossless tracker document. Note 0 is C-0, not MIDI note zero."""
from dataclasses import dataclass, field


OFF, CUT = -1, -2
NOTE_NAMES = ("C-", "C#", "D-", "D#", "E-", "F-", "F#", "G-", "G#", "A-", "A#", "B-")
INSTRUMENT_PROGRAMS = ("arpeggio", "wave_sequence", "pitch_sequence", "pulse", "vibrato", "gate", "retrigger")


def note_name(note):
    if note is None:
        return "..."
    if note == OFF:
        return "==="
    if note == CUT:
        return "^^^"
    return f"{NOTE_NAMES[note % 12]}{note // 12}"


@dataclass
class Cell:
    note: int | None = None
    instrument: int | None = None
    effect: str = ""
    parameter: int | None = None


@dataclass
class ControlCell:
    # None means keep the running value. This is the one shared SID filter.
    cutoff: int | None = None
    resonance: int | None = None
    routing: int | None = None
    mode: int | None = None
    volume: int | None = None
    slide: int | None = None  # signed cutoff units per tick, persistent


@dataclass
class Pattern:
    name: str = "Untitled pattern"
    rows: list[list[Cell]] = field(default_factory=lambda: [[Cell() for _ in range(3)] for _ in range(64)])

    controls: dict[int, ControlCell] = field(default_factory=dict)


@dataclass
class Instrument:
    name: str = "Pulse lead"
    waveform: int = 0x40
    attack: int = 0
    decay: int = 8
    sustain: int = 12
    release: int = 5
    pulse_width: int = 0x800
    sync: bool = False
    ring: bool = False
    arpeggio: list[int] = field(default_factory=list)
    arp_speed: int = 1
    wave_sequence: list[int] = field(default_factory=list)
    pitch_sequence: list[int] = field(default_factory=list)
    pulse_depth: int = 0
    pulse_rate: int = 16
    vibrato_speed: int = 0
    vibrato_depth: int = 0
    vibrato_delay: int = 0
    gate_ticks: int = 0
    retrigger: int = 0
    # Extension data remain lossless; unknown programs are not silently exported.
    macros: dict = field(default_factory=dict)

    # Bypass switches preserve every parameter/table for later re-enabling.
    # True defaults preserve the sound of projects/presets saved before switches.
    arpeggio_enabled: bool = True
    wave_sequence_enabled: bool = True
    pitch_sequence_enabled: bool = True
    pulse_enabled: bool = True
    vibrato_enabled: bool = True
    gate_enabled: bool = True
    retrigger_enabled: bool = True

    @property
    def control(self):
        return self.waveform | (2 if self.sync else 0) | (4 if self.ring else 0)


@dataclass
class Filter:
    cutoff: int = 0x400
    resonance: int = 0
    routing: int = 0
    mode: int = 0x10
    volume: int = 15


@dataclass
class Song:
    title: str = "Untitled"
    author: str = ""
    comments: str = ""
    sid_model: str = "8580"
    clock: str = "PAL"
    speed: int = 6
    tempo: int = 125
    patterns: dict[int, Pattern] = field(default_factory=lambda: {0: Pattern()})
    orders: list[int] = field(default_factory=lambda: [0])
    instruments: dict[int, Instrument] = field(default_factory=lambda: {
        1: Instrument(),
        2: Instrument("Saw bass", 0x20, 0, 9, 9, 3),
        3: Instrument("Triangle bell", 0x10, 0, 10, 0, 8),
        4: Instrument("Noise percussion", 0x80, 0, 6, 0, 2),
    })
    samples: dict = field(default_factory=dict)
    macros: dict = field(default_factory=dict)
    filter_programs: dict = field(default_factory=dict)
    filter: Filter = field(default_factory=Filter)
    export_config: dict = field(default_factory=lambda: {"loop": True})


def example_song():
    """Original three-voice arrangement: 12 orders, eight reusable patterns."""
    song = Song(title="First light / After the reset", author="Harry Horsperg / SIDpulse",
                comments="First light, reimagined for one SID.\n"
                         "12 orders: opening, theme, lift, breakdown, return and ending.\n"
                         "Voice 1: clocked chord arps and singing pulse lead.\n"
                         "Voice 2: short saw bass through the shared filter.\n"
                         "Voice 3: triangle kick, noise snare and tight hats, time-shared.\n"
                         "F4 edits the instrument programs; Ctrl+Shift+F2 edits filter rows.\n"
                         "All musical data and these notes stay in the .sidpulse source.",
                speed=6, tempo=125, filter=Filter(0x280,9,2,0x10,15),
                export_config={"released":"2026 SIDpulse First light", "loop":True})
    from sidpulse.song.presets import first_light_instruments
    song.instruments = first_light_instruments()
    names=["Opening / A minor","Opening / F major","Theme / A minor","Theme / F major",
           "Lift / C major","Answer / G major","Breakdown / A minor","Last light"]
    song.patterns={i:Pattern(name,[[Cell() for _ in range(3)] for _ in range(32)]) for i,name in enumerate(names)}
    for number,root in enumerate([33,29,33,29,36,31,33,33]):
        pat=song.patterns[number]
        minor=number in (0,2,6,7)
        arp=1 if minor else 3
        intro=number<2
        for step,row in enumerate(range(0,32,4)):
            if number==6:
                pat.rows[row][0]=Cell(root+12+(0,7,12,7)[step%4],9)
            elif number>=4 and number!=7:
                melody=(12,19,24,22,19,16 if not minor else 15,14,19)
                pat.rows[row][0]=Cell(root+melody[step],8,'H',0x34)
            else:
                pat.rows[row][0]=Cell(root+12+(12 if step in (3,7) else 0),arp)
                if not intro and step==6:
                    pat.rows[row][0].effect='J';pat.rows[row][0].parameter=0x37 if minor else 0x47
        for row in (0,6,8,14,16,22,24,30):
            pat.rows[row][1]=Cell(root-12+(12 if row in (6,14,22,30) else 0),2)
        if number==6:
            for row in (0,16):pat.rows[row][2]=Cell(36,4)
        else:
            for row in range(0,32,2):
                inst=4 if row%8==0 else 5 if row%8==4 else 7 if row==30 else 6
                if intro and row%4:continue
                pat.rows[row][2]=Cell(36 if inst==4 else 48 if inst==5 else 78,inst)
            if number in (3,5):
                pat.rows[28][2]=Cell(48,5,'Q',0x03)
                pat.rows[30][2]=Cell(48,5,'Q',0x02)
        low=0x130 if intro or number==6 else 0x280
        pat.controls={0:ControlCell(low,9,2,0x10,15,0),8:ControlCell(slide=9),
                      16:ControlCell(slide=-5),24:ControlCell(slide=0)}
    ending=song.patterns[7]
    for row in range(16,32):ending.rows[row]=[Cell() for _ in range(3)]
    ending.rows[16]=[Cell(57,9),Cell(21,2),Cell(36,4)]
    ending.controls[16]=ControlCell(cutoff=0x480,slide=-10)
    ending.controls[24]=ControlCell(slide=0,volume=10)
    ending.controls[28]=ControlCell(volume=5)
    ending.controls[31]=ControlCell(volume=0)
    song.orders=[0,1,2,3,4,5,2,3,6,4,5,7]
    return song
