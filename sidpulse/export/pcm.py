"""Experimental C64 CH1/2 SID + CH3 volume-digi / waveform-DAC compiler.

Music remains a resident, losslessly packed register stream. PCM pitch, trims,
gain and gate effects are baked into deduplicated one-shots on an export copy.
The original host PCM and original SID replay routine are never modified.
"""
from copy import deepcopy
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import struct

from sidpulse.audio.samples import SamplePrograms
from sidpulse.export.psid import ExportError, ExportResult, RecordingSID, MAX_TICKS, _record_song, _memo
from sidpulse.export.squeeze import CleanupStats, SqueezeReport, resolve_options
from sidpulse.export.pcm_squeeze import PCMCandidate, candidates, literal_streams
from sidpulse.export.replay_verify import CycleBudgetError
from sidpulse.playback.sequencer import Sequencer

LOAD, DATA, LIMIT = 0x0801, 0x1800, 0xD000


def dac_levels(model, period):
    """Model-specific silent offset and bipolar headroom, without TRI folding.

    Four-bit amplitudes become oscillator frequency bytes. The waveform DAC
    is captured 24 clocks before the ramp starts again. Keeping that critical
    path fixed lets the NMI use no multiplication, table lookup or shared ZP.
    """
    zero = 0x9e0 if model == '8580' else 0x380
    step = min(zero / 8, (4095 - zero) / 7)
    ceiling = 32767 // (period - 18)  # no MSB crossing before TEST resets the phase
    return bytes(min(ceiling, round((zero + (code - 8) * step) * 8 / (period - 24)))
                 for code in range(16))


class PCMExportFitError(ExportError):
    """An exact memory/timing failure that another encoding may resolve."""


@dataclass(frozen=True)
class PreparedPCM:
    records: list
    clips: dict
    references: dict
    descriptors: bytes
    samples: bytes
    streams: tuple
    seconds: float
    sample_period: int
    warnings: tuple
    source_voice: int
    digi_method: int


class PCMRecorder(RecordingSID):
    def __init__(self, clock, rate):
        super().__init__(clock)
        self.sample_rate = rate
        self.pcm_mode = False
        self.sample_voice = None
        self.last_register = 0

    def write(self, register, value):
        self.registers[register] = value
        self.last_register = register
        if not (self.pcm_mode and register < 21 and register // 7 == self.sample_voice):
            self.events.append((register, value & ~(1 << self.sample_voice)
                                if self.pcm_mode and register == 23 else value))

    def clock(self, cycles):
        if not (self.pcm_mode and self.last_register == self.sample_voice * 7 + 4):
            super().clock(cycles)

    def render(self, frames):
        return bytes(frames * 2)


class PCMPrograms(SamplePrograms):
    def __init__(self, sid, samples):
        super().__init__(sid, samples=samples)
        self.segment = None
        self.segments = []

    def trigger(self, voice, note, inst, instrument_id=None):
        if inst.sample_override:
            if self.sid.sample_voice is None:
                self.sid.sample_voice = voice
            elif voice != self.sid.sample_voice:
                raise ExportError('C64 PCM notes use more than one tracker channel '
                                  f'(CH{self.sid.sample_voice+1} and CH{voice+1}). '
                                  'This routine has one PCM voice on hardware CH3. '
                                  'Keep sample notes on one tracker channel for automatic export remapping. '
                                  'Host playback and WAV/MP3 support samples on all channels.')
        if voice == self.sid.sample_voice:
            self.segment = None
            if inst.sample_override:
                self.sid.pcm_mode = True
                self.segment = []
                self.segments.append(self.segment)
                self.sid.events.append((30, self.segment))
                self.sid.events.append((23, self.sid.registers[23] & ~(1 << voice)))
            elif self.sid.pcm_mode:
                self.sid.events.append((31, 0))
                self.sid.pcm_mode = False
                self.sid.events.append((23, self.sid.registers[23]))
        super().trigger(voice, note, inst, instrument_id)

    def release(self, voice, cut=False):
        if voice == self.sid.sample_voice and self.sid.pcm_mode:
            self.sid.events.append((31, 0))
            self.segment = None
        super().release(voice, cut)

    def capture(self, frames):
        if self.sid.sample_voice is None:
            return
        voice = self.sid.sample_voice
        state = self.pcm[voice]
        if state is None or self.segment is None:
            return
        np = self.np
        points = state['position'] + np.arange(frames) * state['step']
        count = int(np.searchsorted(points, len(state['data']), side='left'))
        if count:
            indexes = points[:count].astype(np.intp)
            fraction = points[:count] - indexes
            data = state['data']
            values = data[indexes] + (data[np.minimum(indexes+1, len(data)-1)]-data[indexes])*fraction
            # Song volume is applied by D418 once, to the complete SID mix.
            codes = np.clip(np.floor((values * state['gain'] + 32768) / 4096), 0, 15)
            self.segment.append(codes.astype(np.uint8).tobytes())
        state['position'] += frames * state['step']
        if state['position'] >= len(state['data']):
            self.pcm[voice] = None


def record_pcm(source, progress=None):
    from sidpulse.audio.media import sample_data, squeeze_sample
    # Use the original compiler's validation of macros, effects, jumps and config.
    check = deepcopy(source)
    for inst in check.instruments.values():
        inst.sample_override = False
    _, _, _, _, warnings = _record_song(check, progress=progress)
    song = deepcopy(source)
    sid = PCMRecorder(song.clock, 4000)
    sample_period = round(sid.clock_hz / 4000)
    sid.sample_rate = round(sid.clock_hz / sample_period)
    used = {inst.sample_slot for inst in song.instruments.values() if inst.sample_override}
    for slot in used:
        key = str(slot) if str(slot) in song.samples else slot
        if key not in song.samples:
            raise ExportError(f'Sample slot {slot:02d} is empty. Assign PCM before C64 export.')
        sample_data(song.samples[key])
        sample = squeeze_sample(song.samples[key], sid.sample_rate, 16)
        sample.pop('original', None)
        song.samples[key] = sample
    seq = Sequencer(sid)
    seq.start(song, loop=False)
    seq.restart_loop = song.export_config.get('loop', True)
    seq.programs = PCMPrograms(sid, song.samples)
    records, seconds = [], 0.
    for tick in range(MAX_TICKS):
        if progress and tick % 128 == 0:
            progress('Preparing C64 PCM...', f'{tick:,} ticks; baking CH3 samples at {sid.sample_rate:,} Hz.')
        seq._boundary()
        total = round(sid.clock_hz * 2.5 / seq.tempo)
        calls = math.ceil(total / 65536)
        period = round(total / calls)-1
        if seq.status != 'playing':
            if not song.export_config.get('loop', True):
                records.append((period, calls-1, tuple(sid.events)))
            break
        records.append((period, calls-1, tuple(sid.events)))
        sid.events.clear()
        frames = int(seq.next_tick)-seq.frames
        seq.programs.capture(frames)
        seq.frames = int(seq.next_tick)
        seconds += 2.5 / seq.tempo
    else:
        raise ExportError('C64 PCM compilation exceeded 18,000 ticks.')
    source_voice = sid.sample_voice if sid.sample_voice is not None else 2
    # Rotate physical SID voices only after sequencing the original channel
    # order. This preserves global-effect precedence and instrument memory.
    # A cyclic rotation also preserves SID ring/sync relationships.
    rotation = (2-source_voice) % 3
    def mapped(register, value):
        if register < 21:
            register = ((register//7+rotation) % 3)*7 + register % 7
        elif register == 23:
            value = (value & ~7) | sum(((value >> v) & 1) << ((v+rotation) % 3) for v in range(3))
        return register, value
    records = [(period, idle, tuple(mapped(r, v) for r, v in events)) for period, idle, events in records]
    return records, seq.programs.segments, seconds, sample_period, warnings, source_voice


def prepare_pcm(song, progress=None, *, digi_method=1):
    if type(digi_method) is not int or digi_method not in (1, 2):
        raise ValueError('DIGI method must be 1 or 2')
    records, segments, seconds, sample_period, warnings, source_voice = record_pcm(song, progress)
    clips, references = {}, {}
    for segment in segments:
        codes = b''.join(segment) or b'\x08'
        if len(codes) > 65535:
            raise ExportError('A C64 PCM one-shot exceeds 65,535 samples. Trim it or raise its note.')
        if codes not in clips:
            clips[codes] = len(clips)
        references[id(segment)] = DATA + clips[codes]*4
    descriptors, samples = bytearray(), bytearray()
    levels = dac_levels(song.sid_model, sample_period)
    for codes in clips:
        address = DATA + len(clips)*4 + len(samples)
        needed = (len(codes)+1)//2 if digi_method == 1 else len(codes)+2
        if address + needed > LIMIT:
            raise ExportError('C64 PCM samples exceed RAM. Trim samples or use fewer pitches.')
        descriptors.extend(struct.pack('<HH', address, len(codes)))
        if digi_method == 1:
            padded = codes + b'\x08' if len(codes) & 1 else codes
            samples.extend(lo | hi << 4 for lo, hi in zip(padded[::2], padded[1::2]))
        else:
            # A midpoint frame is captured before the sentinel ends the timer.
            samples.extend(levels[code] for code in codes)
            samples.extend((levels[8], 255))
    streams = [bytearray() for _ in range(28)]
    previous = None
    for period, idle, events in records:
        if previous != (period, idle):
            streams[27].extend((28, period & 255, period >> 8, idle))
            previous = (period, idle)
        for register, value in events:
            streams[27].append(register)
            if register < 25:
                streams[register].append(value)
            elif register == 30:
                pointer = references[id(value)]
                streams[25].append(pointer & 255)
                streams[26].append(pointer >> 8)
        streams[27].append(26)
    streams[27].append(27)
    streams = tuple(map(bytes, streams))
    return PreparedPCM(records, clips, references, bytes(descriptors), bytes(samples), streams,
                       seconds, sample_period, tuple(warnings), source_voice, digi_method)


def player_image(decoder, digi_method=1):
    assets = Path(__file__).resolve().parents[1]/'assets'
    name = ('pcm-volume-player' if digi_method == 1 else 'pcm-player') + ('' if decoder == 'plain' else '-'+decoder)
    image = (assets/(name+'.bin')).read_bytes()
    metadata = json.loads((assets/(name+'.json')).read_text())
    if hashlib.sha256(image).hexdigest() != metadata['sha256']:
        raise ExportError('Bundled C64 PCM player checksum failed. Reinstall or rebuild the player.')
    if len(image) != DATA-LOAD:
        raise ExportError('Invalid PCM player footprint. Rebuild the bundled players.')
    return image, metadata['labels']


def link_pcm(song, prepared, candidate, kind, cache):
    packed = candidate.packed
    player, labels = _memo(cache, ('pcm-player', prepared.digi_method, candidate.decoder),
                          lambda: player_image(candidate.decoder, prepared.digi_method))
    image = bytearray(player)
    stream_address = DATA + len(prepared.descriptors) + len(prepared.samples)
    struct.pack_into('<'+'H'*28, image, labels['starts']-LOAD,
                     *(stream_address + start for start in packed.starts))
    struct.pack_into('<H', image, labels['sample_period']-LOAD, prepared.sample_period-1)
    if prepared.digi_method == 2:
        image[labels['neutral_level']-LOAD] = dac_levels(song.sid_model, prepared.sample_period)[8]
        image[labels['midpoint_delay']+1-LOAD] = 5 if song.clock == 'PAL' else 0
        image[labels['stabilize_sub']+1-LOAD] = 11 + (256-prepared.sample_period)//2
        image[labels['initial_volume']-LOAD] = song.filter.mode | song.filter.volume
    image[labels['loop_song']-LOAD] = int(song.export_config.get('loop', True))
    image[labels['target_pal']-LOAD] = int(song.clock == 'PAL')
    image[labels['rsid_mode']-LOAD] = int(kind == 'sid')
    image[labels['source_channel_text']-LOAD] = ord('1') + prepared.source_voice
    if candidate.decoder == 'indexed':
        for index, (count, offset) in enumerate(packed.dictionary):
            address = stream_address + offset
            image[labels['dictionary_length']-LOAD+index] = count
            image[labels['dictionary_lo']-LOAD+index] = address & 255
            image[labels['dictionary_hi']-LOAD+index] = address >> 8
    image.extend(prepared.descriptors + prepared.samples + packed.link(stream_address))
    return bytes(image), labels


def compile_pcm(song, *, kind='sid', progress=None, squeeze=None, _comparison_cache=None):
    if kind not in ('sid', 'prg'):
        raise ValueError('PCM export target must be SID or PRG')
    options = resolve_options(squeeze)
    cache = _comparison_cache if _comparison_cache is not None else {}
    method = options.digi_method
    prepared = _memo(cache, ('pcm-prepared', method),
                     lambda: prepare_pcm(song, progress, digi_method=method))
    if prepared.source_voice != 2 and not options.pcm_auto_remap:
        raise ExportError(f'PCM notes play on CH{prepared.source_voice+1}. Enable Auto-remap PCM to CH3 '
                          'or move those notes to CH3 before C64 export. No file was written.')
    literal = _memo(cache, 'pcm-literal', lambda: literal_streams(prepared.streams))
    packing = options.enabled and options.streams
    pool = (list(candidates(prepared.streams, options.version, cache, progress)) if packing else
            [PCMCandidate(literal, algorithm='uncompressed music')])
    # The literal baseline is also a timing fallback. It never substitutes a
    # different sample renderer, omits a note, or changes the sample quality.
    if packing:
        pool.append(PCMCandidate(literal, algorithm='literal timing fallback'))
    pool.sort(key=lambda c: len(c.packed.data))
    selected, last_error = None, ''
    from sidpulse.export.pcm_verify import verify_pcm
    for candidate in pool:
        if selected and len(candidate.packed.data) > len(selected[0].packed.data):
            break
        size = DATA-LOAD + len(prepared.descriptors) + len(prepared.samples) + len(candidate.packed.data)
        if LOAD+size > LIMIT:
            if not last_error:
                last_error = (f'C64 PCM-enhanced replay needs at least {size:,} bytes; RAM budget is {LIMIT-LOAD:,}. '
                              f'Samples {len(prepared.samples):,}, descriptors {len(prepared.descriptors):,}, '
                              f'music {len(candidate.packed.data):,}. Trim samples or reduce sample pitches. '
                              'No notes were dropped.')
            continue
        def checked():
            image, labels = link_pcm(song, prepared, candidate, kind, cache)
            try:
                verification = verify_pcm(image, labels, prepared.records, prepared.references,
                                          prepared.clips, prepared.sample_period,
                                          dac_levels(song.sid_model, prepared.sample_period), progress,
                                          digi_method=method)
            except CycleBudgetError as exc:
                return str(exc)
            return image, labels, verification
        verified = _memo(cache, ('pcm-verified', method, kind, candidate.key), checked)
        if isinstance(verified, str):
            last_error = verified
            continue
        image, labels, verification = verified
        if selected is None or verification.measured_max_cycles < selected[3].measured_max_cycles:
            selected = candidate, image, labels, verification
    if selected is None:
        raise PCMExportFitError(last_error or 'No PCM squeezer candidate fits the C64 memory/timing budget.')
    candidate, image, labels, verification = selected
    warnings = [w for w in prepared.warnings if 'Unused PCM bank' not in w]
    warnings.extend((
        f'Experimental DIGI method #{method}: CH1/2 SID + CH3 '
        f'{"volume digis" if method == 1 else "waveform DAC"}, {song.clock}, {song.sid_model}, ~4 kHz / 4-bit. '
        'CH3 returns to synthesis for ordinary notes. One tracker channel can contain PCM notes.',
        'Channel mapping: '+', '.join(f'tracker CH{v+1} -> C64 CH{(v+2-prepared.source_voice)%3+1}'
                                     for v in range(3))+'. The editable project is unchanged.',
        ('Display and sprite enable registers are preserved. Volume digis modulate the whole SID mix; '
         'VIC DMA can introduce sample jitter. The verified music budget covers a standard screen without sprite DMA. '
         if method == 1 else 'The display and sprites are disabled during replay to stabilize the DAC. ') +
        'Match the selected SID model; '
        'levels and distortion vary between chips. Physical C64 listening still needs hardware testing.',
        f'{len(prepared.clips)} unique sample renders, {len(prepared.samples):,} sample bytes '
        f'({"two 4-bit frames per byte" if method == 1 else "one byte per 4-bit frame plus tails"}). '
        'CIA1 timer A, CIA2 timer A/NMI, CH3, $F8/$F9 and RAM $0801..$CFFF are owned during replay.',
    ))
    report = SqueezeReport(options.enabled, f'PCM-enhanced / DIGI #{method} / '+candidate.algorithm,
                           DATA-LOAD + len(literal.data) + len(prepared.descriptors)+len(prepared.samples), len(image),
                           DATA-LOAD, len(image)-(DATA-LOAD), 2, verification.stack_bytes, CleanupStats(),
                           verified_calls=verification.calls, verified_max_cycles=verification.measured_max_cycles,
                           fallback_reason=f'PCM NMI <= {verification.nmi_cycles} CPU cycles; '
                           f'{prepared.sample_period} cycles per sample. Display {"on" if method == 1 else "off"}; '
                           'music bound includes PCM and scheduling reserve.',
                           squeezer_version=options.version,
                           pcm_source_channel=prepared.source_voice+1,
                           digi_method=method,
                           phrase_blocks=len(getattr(candidate.packed, 'phrases', {})))
    if kind == 'prg':
        data = struct.pack('<H', LOAD) + image
    else:
        def title(text):
            return str(text).encode('cp1252', errors='replace')[:32].ljust(32, b'\0')
        flags = (4 if song.clock == 'PAL' else 8) | (16 if song.sid_model == '6581' else 32)
        header = struct.pack('>4s7HI', b'RSID', 2, 124, 0, labels['entry'], 0, 1, 1, 0)
        header += title(song.title) + title(song.author) + title(song.export_config.get('released', '2026 SIDpulse'))
        header += struct.pack('>H4B', flags, 0, 0, 0, 0)
        data = header + struct.pack('<H', LOAD) + image
    return ExportResult(bytes(data), len(prepared.records), len(prepared.clips), prepared.seconds,
                        verification.max_cycles, tuple(warnings), report)
