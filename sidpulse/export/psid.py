"""PSID v2NG with legacy or losslessly squeezed resident 6510 playback."""
from copy import deepcopy
from dataclasses import dataclass
import os
import math
from pathlib import Path
import shutil
import struct
import tempfile
from typing import Callable

from sidpulse.export.squeeze import (SqueezeOptions, SqueezeReport, resolve_options,
                                     prepare_song, optimized_stream_candidates, COMPACT_PRG_LOAD,
                                     COMPACT_PRG_WRAPPER, LEGACY_PRG_WRAPPER)
from sidpulse.export.channel_phrases import channel_candidates
from sidpulse.export.replay_verify import verify_replay, CycleBudgetError, VerificationError
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
    def __init__(self, player_bytes, record_bytes, sequence_bytes, *, load=LOAD):
        self.player_bytes = player_bytes
        self.record_bytes = record_bytes
        self.sequence_bytes = sequence_bytes
        self.required_bytes = player_bytes + record_bytes + sequence_bytes
        self.budget_bytes = LIMIT - load
        self.excess_bytes = self.required_bytes - self.budget_bytes
        super().__init__(
            'SID export aborted: project exceeds the memory budget. '
            'Shorten or simplify the project and try again. '
            f'Compiled SID needs {self.required_bytes:,} bytes; '
            f'the ${load:04X}..$9FFF memory budget is {self.budget_bytes:,} bytes '
            f'({self.excess_bytes:,} over). Player {player_bytes:,}, '
            f'song data {record_bytes:,}, sequence {sequence_bytes:,}. '
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
    squeeze_report: SqueezeReport | None = None


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


def _record_song(song, *, progress=None, phase="Recording playback..."):
    """Compile a finite order traversal; source remains unmodified.

    Backward Bxx traversal is deliberately rejected in this first compiler.
    Whole-song repetition is available through export_config.loop instead.
    """
    validate(song)
    if not song.instruments:
        raise ExportError('The instrument bank is empty. Add instruments before PSID export; save the editable .sidpulse project at any time.')
    song=deepcopy(song)
    from sidpulse.project.format import compatibility_warnings
    warnings=list(compatibility_warnings(song))
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
        if progress is not None and len(records) % 128 == 0:
            progress(phase, f"{len(records):,} musical ticks processed.")
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
    return song, records, seconds, max_cycles, warnings


def _legacy_image(records, loop):
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
    return bytes(player + payload)


def _memo(cache, key, build):
    """Reuse work only within one isolated, same-song comparison request."""
    if cache is None:
        return build()
    if key not in cache:
        cache[key] = build()
    return cache[key]


def compile_song(song, *, squeeze: SqueezeOptions | bool | None = None, _prg=False, _comparison_cache=None,
                 progress: Callable[[str, str], None] | None = None):
    """Compile without changing the song. Squeezing defaults ON for SID/PRG.

    The legacy player is retained byte-for-byte as the opt-out and as a
    size/cycle fallback. The choice uses code, state, packed data, scratch
    space and (for PRG) the wrapper, not compressed data size alone.
    """
    if progress is not None:
        progress("Pre-analyzing...", "Validating the song and preparing the export copy.")
    validate(song)
    options = resolve_options(squeeze)
    source = song
    source_had_samples = bool(song.samples)
    prepared, cleanup = _memo(_comparison_cache, 'prepared', lambda: prepare_song(song, options))
    def record_checked():
        recorded = _record_song(prepared, progress=progress)
        if options.enabled and any(vars(cleanup).values()):
            reference = _record_song(source, progress=progress, phase="Checking source preservation...")
            if recorded[1:3] != reference[1:3]:
                raise ExportError('Squeeze cleanup changed original playback; no export written')
        return recorded
    song, records, seconds, max_cycles, warnings = _memo(_comparison_cache, 'recorded', record_checked)
    warnings = list(warnings)
    if source_had_samples and not song.samples:
        warnings.append("Unused PCM bank omitted from export; the editable project is intact. "
                        "PCM/sample playback is not implemented in this SID-only version.")
    loop = song.export_config.get("loop", True)
    unique_records = dict.fromkeys(records)
    record_bytes = sum(map(len, unique_records))
    sequence_bytes = 2 * (len(records) + 1)
    legacy_size = DATA - LOAD + record_bytes + sequence_bytes
    load = LOAD
    candidate = None
    reason = ""
    verified = None
    if options.enabled and options.streams:
        target_load = COMPACT_PRG_LOAD if _prg else LOAD
        try:
            if progress is not None:
                progress("Squeezing song...", "Packing repeated voice, register and timing streams.")
            candidates = list(_memo(_comparison_cache, 'v1', lambda: list(optimized_stream_candidates(records, target_load))))
            if options.version in (2,201,202):
                from sidpulse.export.squeeze_v2 import additional_candidates
                if progress is not None:
                    progress('SQUEEZER v2.0...', 'Joining overlapping phrases; retaining v1.0 fallback encodings.')
                candidates.extend(_memo(_comparison_cache, 'v2', lambda: list(additional_candidates(records, tuple(candidates)))))
            if options.version in (201,202):
                from sidpulse.export.squeeze_v201 import additional_candidates
                if progress is not None:
                    progress('SQUEEZER v2.0.1...', 'Sharing packet phrases and repeat counts; retaining earlier encodings.')
                candidates.extend(_memo(_comparison_cache, 'v201', lambda: list(additional_candidates(records, tuple(candidates)))))
            if options.version==202:
                from sidpulse.export.squeeze_v202 import additional_candidates
                if progress is not None:
                    progress('SQUEEZER v2.0.2...', 'Indexing shared literal blocks and phrases; retaining earlier layouts.')
                candidates.extend(_memo(_comparison_cache, 'v202', lambda: list(additional_candidates(records, tuple(candidates)))))
            if progress is not None:
                progress("Squeezing song...", "Finding reusable channel phrases and repeat counts.")
            candidates.extend(_memo(_comparison_cache, 'channels', lambda: channel_candidates(records, loop, target_load)))
        except (ValueError, KeyError) as exc:
            raise ExportError('Squeeze construction failed; no export written: ' + str(exc)) from exc
        wrapper = COMPACT_PRG_WRAPPER if _prg else 0
        original_wrapper = LEGACY_PRG_WRAPPER if _prg else 0
        original_extra = 11 if _prg else 6
        def cost(item):
            extra = max(4, item.zero_page_bytes) + max(7, item.stack_bytes + 3) if _prg else item.zero_page_bytes + item.stack_bytes
            return (item.size + wrapper + extra, item.size + wrapper, item.cycles_bound, item.mode)
        oversized = None
        for item in sorted(candidates, key=cost):
            if (item.size + wrapper >= legacy_size + original_wrapper
                    or cost(item)[0] > legacy_size + original_wrapper + original_extra):
                continue
            if not item.safe_timing:
                reason = 'A compact layout exceeded the conservative per-tick CPU budget.'
                continue
            if item.load + item.size > LIMIT:
                if oversized is None:
                    oversized = item
                continue
            try:
                if progress is not None:
                    progress("Verifying playback...", f"{item.mode}: checking {len(records):,} musical ticks and loop behavior.")
                checked = _memo(_comparison_cache, ('verified', id(item)),
                                lambda: verify_replay(item.image(loop), len(item.player), records, loop,
                                                      gap_address=item.gap_address, load=item.load))
            except CycleBudgetError as exc:
                reason = 'A compact layout exceeded the replay CPU budget: ' + str(exc)
                continue
            except VerificationError as exc:
                raise ExportError('Squeeze replay verification failed; no export written: ' + str(exc)) from exc
            candidate, verified = item, checked
            break
        if candidate is None and oversized is not None and legacy_size > LIMIT - LOAD:
            raise ExportMemoryError(len(oversized.player), oversized.data_bytes, 0, load=oversized.load)
        if candidate is None and not reason:
            reason = 'The legacy representation is smaller including decoder/scratch overhead.'
    elif options.enabled:
        reason = 'Resident stream packing is disabled; existing tick-record encoding retained.'
    if progress is not None:
        progress("Preparing export...", "Building the selected player and song image.")
    if candidate is not None:
        load = candidate.load
        payload = candidate.image(loop)
        max_cycles = max(candidate.cycles_bound, verified.max_cycles)
        labels = {'lanes': 'Independent voice streams', 'single': 'Shared event stream',
                  'registers': 'Independent register-value streams'}
        algorithm = labels.get(candidate.mode, candidate.mode)
        if getattr(candidate, 'optimized', False):
            algorithm += (' / SQUEEZER v2.0.2 indexed blocks and phrases' if candidate.optimizer_version==202
                          else ' / SQUEEZER v2.0.1 shared phrases' if candidate.optimizer_version==201
                          else ' / SQUEEZER v2.0 phrase bank' if candidate.optimizer_version==2
                          else ' / cost-optimized phrase bank')
        report = SqueezeReport(True, algorithm, legacy_size, len(payload), len(candidate.player),
                               candidate.data_bytes, candidate.zero_page_bytes, verified.stack_bytes, cleanup,
                               verified_calls=verified.calls, verified_max_cycles=verified.measured_max_cycles,
                               phrase_blocks=(len(candidate.packed.phrases) if getattr(candidate, 'optimizer_version', 1) in (201,202) else getattr(candidate, 'blocks', 0)),
                               repeated_blocks=getattr(candidate, 'repeated_blocks', 0),
                               squeezer_version=options.version)
    else:
        payload = _legacy_image(records, loop)
        report = SqueezeReport(options.enabled, 'Legacy tick records', legacy_size, len(payload),
                               DATA - LOAD, record_bytes + sequence_bytes, 4, 2, cleanup, reason,
                               squeezer_version=options.version)
    def title(text,label):
        if not isinstance(text,str):raise ExportError(f'{label} must be text')
        encoded=text.encode('cp1252',errors='replace')
        if len(encoded)>32 or encoded.decode('cp1252')!=text:
            warnings.append(f'PSID {label} shortened/substituted to fit 32 CP1252 bytes; native text is intact.')
        return encoded[:32].ljust(32,b'\0')
    # PAL flag bit 2; preferred chip bits 4..5. Speed bit0 selects CIA1 timer.
    flags=(4 if song.clock=='PAL' else 8)|(16 if song.sid_model=='6581' else 32)
    header=struct.pack('>4s7HI',b'PSID',2,124,load,load,load + 3,1,1,1)
    header+=title(song.title,'title')+title(song.author,'author')+title(song.export_config.get('released','2026 SIDpulse'),'released')
    header+=struct.pack('>H4B',flags,0,0,0,0)
    return ExportResult(header+payload,len(records),len(unique_records),seconds,max_cycles,tuple(warnings),report)


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
