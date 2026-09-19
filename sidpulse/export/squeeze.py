"""Export-only song squeezer; never modifies the editable document or preview."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, fields
from pathlib import Path
import struct
import hashlib
import json

from .stream_packer import PackedStreams, StreamReader, pack_streams, verify_streams

COMPACT_PRG_LOAD = 0x09B4
COMPACT_PRG_WRAPPER = COMPACT_PRG_LOAD - 0x0801
LEGACY_PRG_WRAPPER = 0x1000 - 0x0801
SQUEEZER_VERSIONS = (202, 201, 2, 1)


def squeezer_version_label(version):
    return {1: '1.0', 2: '2.0', 201: '2.0.1', 202: '2.0.2'}[version]


@dataclass(frozen=True)
class SqueezeOptions:
    enabled: bool = True
    patterns: bool = True
    instruments: bool = True
    unused: bool = True
    streams: bool = True
    version: int = 202

    def __post_init__(self):
        if any(type(getattr(self, field.name)) is not bool for field in fields(self) if field.name!='version'):
            raise ValueError('Squeeze options must be true or false')
        if type(self.version) is not int or self.version not in SQUEEZER_VERSIONS:
            raise ValueError('Squeezer version must be 1, 2, 201 or 202')


@dataclass(frozen=True)
class CleanupStats:
    duplicate_patterns: int = 0
    duplicate_instruments: int = 0
    unused_patterns: int = 0
    unused_instruments: int = 0
    unused_samples: int = 0


@dataclass(frozen=True)
class SqueezeReport:
    enabled: bool
    algorithm: str
    original_payload_bytes: int
    payload_bytes: int
    player_bytes: int
    song_data_bytes: int
    zero_page_bytes: int
    stack_bytes: int
    cleanup: CleanupStats
    fallback_reason: str = ''
    wrapper_bytes: int = 0
    original_wrapper_bytes: int = 0
    verified_calls: int = 0
    verified_max_cycles: int = 0
    phrase_blocks: int = 0
    repeated_blocks: int = 0
    squeezer_version: int = 1

    @property
    def saved_bytes(self) -> int:
        return self.original_payload_bytes + self.original_wrapper_bytes - self.payload_bytes - self.wrapper_bytes

    @property
    def resident_bytes(self) -> int:
        """Loaded code/data, embedded state, wrapper, zero page and call stack."""
        return self.payload_bytes + self.wrapper_bytes + self.zero_page_bytes + self.stack_bytes

    @property
    def original_resident_bytes(self) -> int:
        return self.original_payload_bytes + self.original_wrapper_bytes + 4 + (7 if self.original_wrapper_bytes else 2)

    def summary(self) -> str:
        state = self.algorithm if self.enabled else 'Squeeze off / legacy player'
        return (f'{state}: {self.resident_bytes:,} bytes resident RAM '
                f'({self.player_bytes:,} player/state, {self.song_data_bytes:,} song, '
                f'{self.wrapper_bytes:,} wrapper, {self.zero_page_bytes} zero page, '
                f'{self.stack_bytes} stack); {self.saved_bytes:,} output bytes saved.')


def resolve_options(value: SqueezeOptions | bool | None) -> SqueezeOptions:
    if value is None:
        return SqueezeOptions()
    if type(value) is bool:
        return SqueezeOptions(enabled=value)
    if not isinstance(value, SqueezeOptions):
        raise TypeError('squeeze must be a bool or SqueezeOptions')
    return value


def _key(value):
    if hasattr(value, '__dataclass_fields__'):
        return tuple((f.name, _key(getattr(value, f.name))) for f in fields(value) if f.name != 'name')
    if isinstance(value, dict):
        return tuple(sorted((key, _key(item)) for key, item in value.items()))
    if isinstance(value, (tuple, list)):
        return tuple(map(_key, value))
    return value


def prepare_song(source, options: SqueezeOptions):
    """Conservative source normalization on an isolated copy.

    Order *positions* are never renumbered: Bxx/Cxx still address the same
    playlist. The initial implicit instrument is retained even when there is
    no explicit cell reference. This matters for instrument-memory semantics.
    The current model has no PCM trigger, so the complete PCM bank is unused.
    """
    song = deepcopy(source)
    counts = dict.fromkeys(CleanupStats.__dataclass_fields__, 0)
    if not options.enabled:
        return song, CleanupStats()
    if options.unused:
        keep = set(song.orders)
        counts['unused_patterns'] = len(song.patterns.keys() - keep)
        song.patterns = {key: value for key, value in song.patterns.items() if key in keep}
        used = {cell.instrument for pat in song.patterns.values() for row in pat.rows
                for cell in row if cell.instrument is not None}
        if song.instruments:
            used.add(min(song.instruments))  # implicit starting instrument
        counts['unused_instruments'] = len(song.instruments.keys() - used)
        song.instruments = {key: value for key, value in song.instruments.items() if key in used}
        counts['unused_samples'] = len(song.samples)
        song.samples = {}
    if options.instruments:
        canonical, aliases, bank = {}, {}, {}
        for number, instrument in sorted(song.instruments.items()):
            key = _key(instrument)
            if key not in canonical:
                canonical[key] = number
                bank[number] = instrument
            aliases[number] = canonical[key]
        counts['duplicate_instruments'] = len(song.instruments) - len(bank)
        song.instruments = bank
        for pattern in song.patterns.values():
            for row in pattern.rows:
                for cell in row:
                    if cell.instrument in aliases:
                        cell.instrument = aliases[cell.instrument]
    if options.patterns:
        canonical, aliases, bank = {}, {}, {}
        for number, pattern in sorted(song.patterns.items()):
            key = _key(pattern)
            if key not in canonical:
                canonical[key] = number
                bank[number] = pattern
            aliases[number] = canonical[key]
        counts['duplicate_patterns'] = len(song.patterns) - len(bank)
        song.patterns = bank
        song.orders = [aliases[number] for number in song.orders]
    return song, CleanupStats(**counts)


# Single stream: register/value pairs, plus explicit non-register commands.
TICK, END, TIMER, SILENT = 26, 27, 28, 29


def make_streams(records: list[bytes], lanes: bool) -> tuple[bytes, ...]:
    """Split the exact executed trace, not visually similar editor patterns.

    Four voice/global streams carry bytes; the fifth stream preserves their
    interleaving, every tick boundary and all CIA periods/slow-tick holds.
    An independent voice's repeated phrases can be reused even when other
    voices differ. Nothing is reordered and no duplicate SID write is dropped.
    """
    streams = [bytearray() for _ in range(5 if lanes else 1)]
    conductor = streams[-1]
    previous = None
    empty = 0

    def flush_empty():
        nonlocal empty
        while empty:
            count = min(empty, 255)
            if count == 1:
                conductor.append(0 if lanes else TICK)
            else:
                conductor.extend((3 if lanes else SILENT, count))
            empty -= count

    for record in records:
        timing, events = record[:3], record[4:]
        if timing != previous:
            flush_empty()
            conductor.append(2 if lanes else TIMER)
            conductor.extend(timing)
            previous = timing
        if not events:
            empty += 1
            continue
        flush_empty()
        if not lanes:
            for register, value in zip(events[::2], events[1::2]):
                conductor.append(register)
                if register != 25:
                    conductor.append(value)
            conductor.append(TICK)
            continue
        runs = []
        previous_lane = 0
        for register, value in zip(events[::2], events[1::2]):
            lane = previous_lane if register == 25 else min(register // 7, 3)
            offset = 7 if register == 25 else register - lane * 7
            streams[lane].append(offset)
            if register != 25:
                streams[lane].append(value)
            if runs and runs[-1][0] == lane and runs[-1][1] < 63:
                runs[-1][1] += 1
            else:
                runs.append([lane, 1])
            previous_lane = lane
        conductor.extend(count * 4 + lane for lane, count in runs)
        conductor.append(0)
    flush_empty()
    conductor.append(1 if lanes else END)
    return tuple(bytes(stream) for stream in streams)


@dataclass(frozen=True)
class StreamCandidate:
    mode: str
    packed: PackedStreams
    player: bytes
    cycles_bound: int
    safe_timing: bool
    load: int
    gap_address: int = 0
    optimized: bool = False
    zero_page_bytes: int = 2
    stack_bytes: int = 4
    optimizer_version: int = 1

    @property
    def data_bytes(self):
        return len(self.packed.data)

    @property
    def size(self):
        return len(self.player) + len(self.packed.data)

    def image(self, loop: bool) -> bytes:
        player = bytearray(self.player)
        data_address = self.load + len(player)
        # Fixed ABI: the two entry JMPs are followed by stream start words and
        # the loop flag. No full-song work area is allocated or initialized.
        for index, offset in enumerate(self.packed.starts):
            struct.pack_into('<H', player, 6 + index * 2, data_address + offset)
        player[6 + 2 * len(self.packed.starts)] = int(loop)
        return bytes(player) + self.packed.link(data_address)


def verify_candidate(packed: PackedStreams, records: list[bytes], lanes: bool, *, registers: bool = False, reader_type=StreamReader) -> tuple[int, bool]:
    """Decode the entire candidate and compare every timed, ordered write.

    CPU bounds include cold packet setup on the actual stream boundaries,
    decoder dispatch, SID writes, delay tokens and init/loop reset overhead.
    They are deliberately conservative; tests also execute the actual 6510.
    """
    reader = reader_type(packed)
    conductor = 25 if registers else 4 if lanes else 0
    timing, events = None, bytearray()
    tick, maximum, safe = 0, 0, True
    overhead = 1900 if registers else 700

    def finish_tick():
        nonlocal tick, maximum, safe, overhead
        if tick >= len(records) or timing is None:
            raise ValueError('Squeezed replay changed song length/timing')
        actual = timing + bytes([len(events) // 2]) + bytes(events)
        if actual != records[tick]:
            raise ValueError(f'Squeezed replay changed SID events at tick {tick}')
        bound = reader.cycles + overhead
        maximum = max(maximum, bound)
        safe &= bound < int.from_bytes(timing[:2], 'little')
        reader.cycles, overhead = 0, 700
        events.clear()
        tick += 1

    while True:
        command = reader.read(conductor)
        overhead += 60
        if command == (1 if lanes else END):
            if tick != len(records) or events:
                raise ValueError('Squeezed replay ended at a different boundary')
            return max(maximum, reader.cycles + overhead), safe
        if command == (2 if lanes else TIMER):
            timing = bytes(reader.read(conductor) for _ in range(3))
            overhead += 180
        elif command == (0 if lanes else TICK):
            finish_tick()
        elif command == (3 if lanes else SILENT):
            count = reader.read(conductor)
            if not count or events:
                raise ValueError('Invalid silent-tick run')
            for _ in range(count):
                finish_tick()
        elif lanes:
            voice, count = command & 3, command >> 2
            overhead += 70
            for _ in range(count):
                register = reader.read(voice)
                overhead += 70
                if register == 7:
                    events.extend((25, 32))
                    overhead += 40
                else:
                    if register > (3 if voice == 3 else 6):
                        raise ValueError('Invalid voice-relative register')
                    events.extend((voice * 7 + register, reader.read(voice)))
        elif command == 25:
            events.extend((25, 32))
            overhead += 40
        elif command < 25:
            events.extend((command, reader.read(command if registers else conductor)))
        else:
            raise ValueError('Invalid squeezed replay command')


def stream_candidates(records: list[bytes], load: int = 0x1000):
    if load not in (0x1000, COMPACT_PRG_LOAD):
        raise ValueError('No bundled squeezed player for this load address')
    assets = Path(__file__).resolve().parents[1] / 'assets'
    for lanes in (False, True):
        streams = make_streams(records, lanes)
        mode = 'lanes' if lanes else 'single'
        suffix = '-prg' if load == COMPACT_PRG_LOAD else ''
        name = f'squeeze-{mode}{suffix}'
        player = (assets / f'{name}.bin').read_bytes()
        info = json.loads((assets / 'replay-players.json').read_text())[name]
        if hashlib.sha256(player).hexdigest() != info['sha256']:
            raise ValueError('Invalid bundled stream player image')
        # Compare actual complete packet costs, not a guessed pattern length.
        encodings = sorted((pack_streams(streams, size) for size in (4, 8, 16, 32, 64)),
                           key=lambda packed: (len(packed.data), packed.minimum_match))
        smallest = None
        for packed in encodings:
            verify_streams(packed, streams)
            cycles, safe = verify_candidate(packed, records, lanes)
            candidate = StreamCandidate(mode, packed, player, cycles, safe, load, info['gap'])
            if smallest is None:
                smallest = candidate
            if safe:
                # A slightly larger layout can decode faster: try it before
                # abandoning resident packing for the legacy player.
                yield candidate
                break
        else:
            yield smallest


def make_register_streams(records: list[bytes]) -> tuple[bytes, ...]:
    """Factor values independently, retain all write order/timing in a conductor.

    This is a finer-grained alternative to voice phrases, not a change to the
    SID's shared controls. Register values never run on an independent clock.
    Every deliberate repeated write and gate-settling token remains present.
    """
    streams = [bytearray() for _ in range(26)]
    conductor = streams[-1]
    previous = None
    empty = 0

    def flush_empty():
        nonlocal empty
        while empty:
            count = min(empty, 255)
            conductor.extend((SILENT, count) if count > 1 else (TICK,))
            empty -= count

    for record in records:
        timing = record[:3]
        if timing != previous:
            flush_empty()
            conductor.append(TIMER)
            conductor.extend(timing)
            previous = timing
        if not record[3]:
            empty += 1
            continue
        flush_empty()
        for register, value in zip(record[4::2], record[5::2]):
            conductor.append(register)
            if register != 25:
                streams[register].append(value)
        conductor.append(TICK)
    flush_empty()
    conductor.append(END)
    return tuple(bytes(stream) for stream in streams)


def optimized_stream_candidates(records: list[bytes], load: int = 0x1000):
    """Cost the prior layouts and static phrase-bank refinement side by side."""
    from .phrase_optimizer import optimize_bank
    if load not in (0x1000, COMPACT_PRG_LOAD):
        raise ValueError('No bundled stream player for this load address')
    assets = Path(__file__).resolve().parents[1] / 'assets'
    manifest = json.loads((assets / 'replay-players.json').read_text())
    for mode in ('single', 'lanes', 'registers'):
        streams = (make_register_streams(records) if mode == 'registers'
                   else make_streams(records, mode == 'lanes'))
        suffix = '-prg' if load == COMPACT_PRG_LOAD else ''
        name = f'squeeze-{mode}{suffix}'
        player = (assets / f'{name}.bin').read_bytes()
        info = manifest[name]
        if len(player) != info['size'] or hashlib.sha256(player).hexdigest() != info['sha256']:
            raise ValueError('Invalid bundled stream player image')
        seeds = sorted((pack_streams(streams, size) for size in (4, 8, 16, 32, 64)),
                       key=lambda packed: (len(packed.data), packed.minimum_match))
        alternatives = [(packed, False) for packed in seeds]
        # Refining the two best seeds keeps host work bounded. Other literal-bank
        # orderings remain possible future improvements, not an optimality claim.
        alternatives.extend((optimize_bank(streams, packed), True) for packed in seeds[:2])
        seen = set()
        for packed, optimized in sorted(alternatives, key=lambda item: (len(item[0].data), item[1])):
            signature = (packed.data, packed.starts, tuple(packed.references.items()))
            if signature in seen:
                continue
            seen.add(signature)
            verify_streams(packed, streams)
            cycles, safe = verify_candidate(packed, records, mode == 'lanes', registers=mode == 'registers')
            yield StreamCandidate(mode, packed, player, cycles, safe, load, info['gap'], optimized)
