"""PSID v2NG with an executable 6510 player and deduplicated tick programs."""
from copy import deepcopy
from dataclasses import dataclass
import os
import math
from pathlib import Path
import shutil
import struct
import tempfile

from sidpulse.playback.sequencer import Sequencer
from sidpulse.playback.voices import supported
from sidpulse.project.format import validate
from sidpulse.sid.backend_residfp import PAL_CLOCK, CLOCKS

LOAD, INIT, PLAY, DATA, LIMIT = 0x1000, 0x1000, 0x1003, 0x1200, 0xA000
MAX_TICKS=18000  # compilation guard, independent of available C64 RAM


class ExportError(ValueError):
    pass


class ExportMemoryError(ExportError):
    """Exact existing-player memory requirement, not the native project size."""
    def __init__(self, player_bytes, record_bytes, sequence_bytes):
        self.player_bytes = player_bytes
        self.record_bytes = record_bytes
        self.sequence_bytes = sequence_bytes
        self.required_bytes = player_bytes + record_bytes + sequence_bytes
        self.budget_bytes = LIMIT - LOAD
        self.excess_bytes = self.required_bytes - self.budget_bytes
        super().__init__(
            'SID export aborted: project exceeds the memory budget. '
            'Shorten or simplify the project and try again. '
            f'Compiled SID needs {self.required_bytes:,} bytes; '
            f'the $1000..$9FFF memory budget is {self.budget_bytes:,} bytes '
            f'({self.excess_bytes:,} over). Player {player_bytes:,}, '
            f'unique tick records {record_bytes:,}, pointer sequence {sequence_bytes:,}. '
            'The editable .sidpulse is unchanged and may still play in the tracker. '
            'Simplify a separate export copy to preserve your original arrangement. '
            'No notes were dropped.'
        )


@dataclass(frozen=True)
class ExportResult:
    data: bytes
    ticks: int
    unique_records: int
    seconds: float
    max_cycles_bound: int
    warnings: tuple


class RecordingSID:
    sample_rate=48000
    def __init__(self, clock="PAL"):
        self.clock_hz=CLOCKS[clock]
        self.registers=bytearray(25)
        self.events=[]
    def write(self,register,value):
        self.registers[register]=value
        self.events.append((register,value))
    def clock(self,cycles):
        if cycles!=32:raise ExportError('Player only supports the 32-cycle gate settling request')
        self.events.append((25,32))


def compile_song(song):
    """Compile a finite order traversal; source remains unmodified.

    Backward Bxx traversal is deliberately rejected in this first compiler.
    Whole-song repetition is available through export_config.loop instead.
    """
    validate(song)
    if not song.instruments:
        raise ExportError('The instrument bank is empty. Add instruments before PSID export; save the editable .sidpulse project at any time.')
    song=deepcopy(song)
    warnings=[]
    if song.macros or song.filter_programs or any(i.macros for i in song.instruments.values()):
        raise ExportError('Unimplemented extension macro data: retain .sidpulse; use the F4 instrument programs for export')
    for pid,pat in song.patterns.items():
        if pid not in song.orders:continue
        for r,row in enumerate(pat.rows):
            for v,cell in enumerate(row):
                if cell.instrument is not None and cell.instrument not in song.instruments:
                    raise ExportError(f'Pattern {pid:02X}, row {r:03d}, CH {v+1}: instrument {cell.instrument:02d} is empty. Add that instrument before PSID export.')
                if not supported(cell.effect,cell.parameter or 0):
                    raise ExportError(f'Pattern {pid:02X}, row {r:03d}, CH {v+1}: {cell.effect}{cell.parameter or 0:02X} is not supported by PSID export')
    if song.samples:
        warnings.append('PCM bank retained in the project; samples are not referenced or played by this SID-only version.')
    unknown=set(song.export_config)-{'loop','released','load_address'}
    if unknown:raise ExportError('Unsupported export settings: '+', '.join(sorted(unknown)))
    if song.export_config.get('load_address',LOAD)!=LOAD:
        raise ExportError('This player currently loads at $1000; relocatable output is a later milestone')
    loop=song.export_config.get('loop',True)
    if type(loop) is not bool:raise ExportError('export_config.loop must be true or false')
    sid=RecordingSID(song.clock);seq=Sequencer(sid);seq.start(song,loop=False)
    seq.restart_loop = loop
    records=[];seen_rows=set();seconds=0;max_cycles=0
    while len(records)<MAX_TICKS:
        seq._boundary()  # same boundary routine as PCM playback, without rendering samples
        if seq.status=='playing' and seq.tick==0:
            position=(seq.order,seq.row)
            if position in seen_rows:
                raise ExportError(f'Playback revisits order {seq.order:02X}, row {seq.row:03d}. Use a finite order list and export_config.loop for whole-song looping.')
            seen_rows.add(position)
        total=round(sid.clock_hz*2.5/seq.tempo)
        calls=math.ceil(total/65536)
        period=round(total/calls)-1
        if len(sid.events)>125:raise ExportError('Too many SID writes in one tick')
        bound=400+90*len(sid.events)
        if bound>=period:raise ExportError('SID tick exceeds the conservative C64 cycle budget')
        max_cycles=max(max_cycles,bound)
        if seq.status!='playing':
            if not loop:
                records.append(struct.pack('<HBB',period,calls-1,len(sid.events))+bytes(x for pair in sid.events for x in pair))
            break
        records.append(struct.pack('<HBB',period,calls-1,len(sid.events))+bytes(x for pair in sid.events for x in pair))
        sid.events.clear()
        seconds+=2.5/seq.tempo
        seq.frames=int(seq.next_tick)
    else:
        raise ExportError('Compilation exceeded 18,000 ticks; shorten the arrangement')
    player=bytearray((Path(__file__).resolve().parents[1]/'assets/player.bin').read_bytes())
    if len(player)!=DATA-LOAD:raise ExportError('Invalid bundled player image')
    # Preflight the complete requirement before assigning 16-bit addresses.
    # The player and record layout are unchanged, including every repeated write.
    unique_records = dict.fromkeys(records)
    record_bytes = sum(map(len, unique_records))
    sequence_bytes = 2 * (len(records) + 1)
    if len(player) + record_bytes + sequence_bytes > LIMIT - LOAD:
        raise ExportMemoryError(len(player), record_bytes, sequence_bytes)
    addresses={};payload=bytearray();order=[]
    for record in records:
        if record not in addresses:
            address=DATA+len(payload)
            addresses[record]=address;payload.extend(record)
        order.append(addresses[record])
    sequence=DATA+len(payload)
    payload.extend(struct.pack('<'+'H'*(len(order)+1),*order,0))
    struct.pack_into('<HH',player,0x1F0,sequence,sequence if loop else 0)
    def title(text,label):
        if not isinstance(text,str):raise ExportError(f'{label} must be text')
        encoded=text.encode('cp1252',errors='replace')
        if len(encoded)>32 or encoded.decode('cp1252')!=text:
            warnings.append(f'PSID {label} shortened/substituted to fit 32 CP1252 bytes; native text is intact.')
        return encoded[:32].ljust(32,b'\0')
    # PAL flag bit 2; preferred chip bits 4..5. Speed bit0 selects CIA1 timer.
    flags=(4 if song.clock=='PAL' else 8)|(16 if song.sid_model=='6581' else 32)
    header=struct.pack('>4s7HI',b'PSID',2,124,LOAD,INIT,PLAY,1,1,1)
    header+=title(song.title,'title')+title(song.author,'author')+title(song.export_config.get('released','2026 SIDpulse'),'released')
    header+=struct.pack('>H4B',flags,0,0,0,0)
    return ExportResult(header+player+payload,len(records),len(addresses),seconds,max_cycles,tuple(warnings))


def save_export(path,result,*,suffix='.sid'):
    if suffix not in ('.sid', '.prg'):
        raise ValueError('Choose .sid or .prg export')
    path=Path(path).expanduser().with_suffix(suffix)
    path.parent.mkdir(parents=True,exist_ok=True)
    fd,temp=tempfile.mkstemp(prefix='.'+path.name+'.',suffix='.tmp',dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as f:
            f.write(result.data);f.flush();os.fsync(f.fileno())
        if path.exists():shutil.copy2(path,path.with_suffix(suffix+'.bak'))
        os.replace(temp,path)
    finally:
        if os.path.exists(temp):os.unlink(temp)
    return path
