"""Resident per-channel event phrases with counted repetitions and templates.

The conductor retains every tick's ordered voice/global runs. Pattern boundaries
are absent from the storage identity, so a repeated bass/drum part remains
shareable underneath a changing lead. No editable source is rewritten here.
"""
from __future__ import annotations
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
import hashlib
import json
import struct

class WordPool:
    """Bounded greedy substring factoring with direct ROM/RAM references.

    Search work is bounded (255-word phrases, at most 64 occurrences per key).
    Two search orders are costed by the caller. This is not a claim of a global
    mathematical minimum. It does find repeats independently in each voice.
    """
    def __init__(self, enabled=True, max_phrase=255):
        self.words = []
        self.index = defaultdict(list)
        self.enabled = enabled
        self.max_phrase = max_phrase

    def append(self, value):
        self.words.append(value)
        n = len(self.words)
        for length in (1, 2, 3):
            if n >= length:
                entries = self.index[tuple(self.words[n-length:n])]
                entries.append(n-length)
                if len(entries) > 64: del entries[0]

    @staticmethod
    def add_block(blocks, start, length, repeat=1):
        if blocks:
            old_start, old_length, old_repeat = blocks[-1]
            if (old_start, old_length) == (start, length) and old_repeat + repeat <= 255:
                blocks[-1] = (start, length, old_repeat + repeat); return
            if old_repeat == repeat == 1 and old_start + old_length == start and old_length + length <= 255:
                blocks[-1] = (old_start, old_length + length, 1); return
        blocks.append((start, length, repeat))

    def encode(self, values):
        values = tuple(values); blocks = []; i = 0
        while i < len(values):
            best = None
            limit = min(self.max_phrase, len(values) - i)
            if self.enabled:
                candidates = set()
                for length in (1, 2, 3):
                    if limit >= length:
                        candidates.update(self.index.get(values[i:i+length], ())[-64:])
                for start in sorted(candidates):
                    length = 0
                    while (length < limit and start+length < len(self.words) and
                           self.words[start+length] == values[i+length]):
                        length += 1
                    # Try each short period plus the longest available phrase.
                    sizes = set(range(1, min(length, 32)+1))
                    sizes.update(n for n in (48, 64, 96, 128, 192, 255, length) if 0 < n <= length)
                    for size in sorted(sizes):
                        repeat = 1
                        phrase = values[i:i+size]
                        while repeat < 255 and values[i+size*repeat:i+size*(repeat+1)] == phrase:
                            repeat += 1
                        covered = size * repeat
                        if covered < 3: continue  # a 4-byte descriptor must pay for itself
                        score = (covered * 2 - 4, covered, size, -start)
                        if best is None or score > best[0]: best = (score, start, size, repeat)
            if best:
                _, start, length, repeat = best
                self.add_block(blocks, start, length, repeat)
                i += length * repeat
            else:
                start = len(self.words)
                self.append(values[i]); self.add_block(blocks, start, 1); i += 1
        return blocks


def split_records(records, separate):
    """Deduplicate immutable write packets and exact timing/interleave schedules."""
    pool = []; ids = {}; streams = [[] for _ in range(5)]
    def intern(data, write=False):
        key = (write, data)
        if key not in ids:
            ids[key] = len(pool); pool.append(data)
        return ids[key]
    for tick in records:
        events = list(zip(tick[4::2], tick[5::2]))
        runs = []
        for register, value in events:
            # Gate settling belongs to the immediately preceding voice write.
            lane = (runs[-1][0] if runs else 3) if register == 25 else min(register // 7, 3)
            if not separate: lane = 0
            if not runs or runs[-1][0] != lane: runs.append((lane, []))
            runs[-1][1].append((register, value))
        for lane, pairs in runs:
            data = bytes([len(pairs)]) + bytes(v for pair in pairs for v in pair)
            streams[lane].append(intern(data, write=True))
        streams[4].append(intern(tick[:3] + bytes([len(runs)]) + bytes(lane for lane, _ in runs)))
    return pool, streams


def verify_structure(records, packets, streams, words, blocks):
    """Full byte-for-byte reconstruction, not a hash-only or audible-similarity test."""
    rebuilt = []
    for original, chunks in zip(streams, blocks):
        decoded = [word for start, length, repeat in chunks
                   for _ in range(repeat) for word in words[start:start+length]]
        if decoded != original: raise ValueError('Squeezer pointer-block round-trip failed')
        rebuilt.append(iter(decoded))
    for record in records:
        schedule = packets[next(rebuilt[4])]
        events = bytearray()
        for lane in schedule[4:]:
            packet = packets[next(rebuilt[lane])]
            if len(packet) != 1 + 2 * packet[0]: raise ValueError('Invalid squeeze packet')
            events.extend(packet[1:])
        decoded = schedule[:3] + bytes([len(events)//2]) + events
        if decoded != record: raise ValueError('Squeezer ordered-write round-trip failed')
    if any(next(stream, None) is not None for stream in rebuilt):
        raise ValueError('Squeezer produced unconsumed events')


def fixed_blocks(values, size):
    """Compare stable motif lengths, not just greedy matches against prior literals."""
    pool = []; encoded = bytearray(); chunks = []
    for i in range(0, len(values), size):
        part = values[i:i+size]
        needle = struct.pack('<'+'I'*len(part), *part)
        offset = encoded.find(needle)
        while offset >= 0 and offset % 4:
            offset = encoded.find(needle, offset+1)
        if offset < 0:
            offset = len(encoded); encoded.extend(needle); pool.extend(part)
        WordPool.add_block(chunks, offset//4, len(part))
    return pool, chunks


def factor_streams(streams, enabled, reverse, mixed):
    if not mixed or not enabled:
        pool = WordPool(enabled)
        chunks = [None] * 5
        for lane in (range(4, -1, -1) if reverse else range(5)):
            chunks[lane] = pool.encode(streams[lane])
        return pool.words, chunks
    words, chunks = [], []
    for stream in streams:
        pool = WordPool(); part = pool.encode(stream)
        candidates = [(pool.words, part)]
        for size in (1,2,3,4,6,8,12,16,24,32,48,64,96,128,192,255):
            candidates.append(fixed_blocks(stream, size))
        data, part = min(candidates, key=lambda entry: len(entry[0])*2 + len(entry[1])*4)
        chunks.append([(start+len(words), length, repeat) for start,length,repeat in part])
        words.extend(data)
    return words, chunks


def place_literals(items, base, overlap):
    """Exact substring/tail sharing in immutable data; offsets need not be aligned."""
    payload = bytearray(); addresses = [0] * len(items)
    ordering = sorted(range(len(items)), key=lambda i: (-len(items[i]), i)) if overlap else range(len(items))
    for index in ordering:
        data = items[index]
        offset = payload.find(data) if overlap else -1
        if offset < 0:
            shared = 0
            if overlap:
                for size in range(min(len(payload), len(data)-1), 0, -1):
                    if payload.endswith(data[:size]): shared = size; break
            offset = len(payload)-shared
            payload.extend(data[shared:])
        addresses[index] = base+offset
    return payload, addresses



def minimum_period(values):
    """Exact shortest period; a final partial occurrence need not divide length."""
    if not values:
        return 0
    borders = [0] * len(values)
    for i in range(1, len(values)):
        j = borders[i - 1]
        while j and values[i] != values[j]:
            j = borders[j - 1]
        if values[i] == values[j]:
            j += 1
        borders[i] = j
    return len(values) - borders[-1]


def refine_blocks(streams, words, chunks):
    """Reparse a fixed word bank by descriptor cost, then remove unused spans.

    All ordinary reference lengths 1..255 are eligible. Counted repeats consider
    the exact shortest period, the longest match and one-word runs. Search is
    bounded, deterministic and does not allocate target-side working buffers.
    The original bank remains a candidate if the refinement is not smaller.
    """
    from array import array
    from bisect import bisect_right
    words = tuple(words)
    index = defaultdict(list)
    for pos, word in enumerate(words):
        entries = index[word]
        entries.append(pos)
        if len(entries) > 64:
            del entries[32]
    refined = []
    for stream in streams:
        values = tuple(stream)
        n = len(values)
        if n > 32768:  # avoid a disproportionate host-side optimizer allocation
            return list(words), chunks
        cost = [0] * (n + 1)
        choices = [None] * n
        shifted_matches = {}
        for pos in range(n - 1, -1, -1):
            longest, target = 0, 0
            for begin in index.get(values[pos], ()):
                limit = min(255, n - pos, len(words) - begin)
                if limit <= longest:
                    continue
                low, high = 1, limit
                while low < high:
                    middle = (low + high + 1) // 2
                    if words[begin:begin + middle] == values[pos:pos + middle]:
                        low = middle
                    else:
                        high = middle - 1
                if low > longest:
                    longest, target = low, begin
            if not longest:
                raise ValueError('Phrase bank cannot reconstruct its source')
            end = min(range(pos + 1, pos + longest + 1), key=lambda j: (cost[j], -j))
            best = (4 + cost[end], -(end - pos))
            choice = (target, end - pos, 1)
            periods = {1, longest, minimum_period(values[pos:pos + longest])}
            for period in sorted(periods):
                if pos + 2 * period > n:
                    continue
                if period not in shifted_matches:
                    if n * (len(shifted_matches) + 1) > 4_000_000:
                        continue
                    same = array('I', [0]) * (n + 1)
                    for i in range(n - period - 1, -1, -1):
                        if values[i] == values[i + period]:
                            same[i] = same[i + 1] + 1
                    shifted_matches[period] = same
                count = min(255, 1 + shifted_matches[period][pos] // period)
                if count < 2:
                    continue
                repeat = min(range(2, count + 1), key=lambda r: (cost[pos + r * period], -r))
                candidate = (4 + cost[pos + period * repeat], -period * repeat)
                if candidate < best:
                    best, choice = candidate, (target, period, repeat)
            cost[pos] = best[0]
            choices[pos] = choice
        result = []
        pos = 0
        while pos < n:
            start, length, repeat = choices[pos]
            WordPool.add_block(result, start, length, repeat)
            pos += length * repeat
        refined.append(result)
    intervals = sorted((start, start + length) for part in refined for start, length, _ in part)
    retained = []
    for start, end in intervals:
        if retained and start <= retained[-1][1]:
            retained[-1] = (retained[-1][0], max(end, retained[-1][1]))
        else:
            retained.append((start, end))
    compact = []
    mapping = []
    for start, end in retained:
        mapping.append((start, end, len(compact)))
        compact.extend(words[start:end])
    starts = [start for start, _, _ in mapping]
    result = []
    for part in refined:
        relocated = []
        for start, length, repeat in part:
            begin, end, address = mapping[bisect_right(starts, start) - 1]
            if start + length > end:
                raise ValueError('Phrase refinement split a referenced block')
            relocated.append((address + start - begin, length, repeat))
        result.append(relocated)
    return compact, result


@dataclass(frozen=True)
class ChannelCandidate:
    player: bytes
    data: bytes
    load: int
    mode: str
    gap_address: int
    blocks: int
    repeated_blocks: int
    cycles_bound: int
    safe_timing: bool
    zero_page_bytes: int = 4
    stack_bytes: int = 4

    @property
    def size(self):
        return len(self.player) + len(self.data)

    @property
    def data_bytes(self):
        return len(self.data)

    def image(self, loop: bool):
        # Loop preference was linked when constructing the candidate.
        return self.player + self.data


def _build(records, packets, streams, words, chunks, loop, load, templates, overlap, strategy):
    suffix = '-prg' if load == 0x09B4 else ''
    name = 'channel-templates' if templates else 'channel-raw'
    asset = Path(__file__).resolve().parents[1] / 'assets' / (name + suffix)
    player = bytearray(asset.with_suffix('.bin').read_bytes())
    info = json.loads(asset.with_suffix('.json').read_text())
    if (len(player) != info['size'] or info['load'] != load
            or hashlib.sha256(player).hexdigest() != info['sha256']):
        raise ValueError('Invalid bundled channel-phrase player')
    verify_structure(records, packets, streams, words, chunks)
    literals = list(packets)
    patterns = []
    if templates:
        template_ids = {}
        writes = set(word for lane in streams[:4] for word in lane)
        for index in sorted(writes):
            packet = packets[index]
            registers = packet[1::2]
            if registers not in template_ids:
                template_ids[registers] = len(patterns)
                patterns.append(bytes([len(registers)]) + registers)
            if len(patterns) > 256:
                return None
            literals[index] = bytes([template_ids[registers]]) + packet[2::2]
    payload, addresses = place_literals(literals + patterns, load + len(player), overlap)
    template_low = load + len(player) + len(payload)
    if templates:
        # Preflight before converting any future data addresses to 16-bit words.
        if template_low + 2 * len(patterns) > 0x10000:
            return None
        payload.extend(address & 255 for address in addresses[len(packets):])
        payload.extend(address >> 8 & 255 for address in addresses[len(packets):])
        struct.pack_into('<H', player, info['template_low'], template_low)
        struct.pack_into('<H', player, info['template_high'], template_low + len(patterns))
    word_base = load + len(player) + len(payload)
    size = len(player) + len(payload) + 2 * len(words) + sum(4 * len(part) + 1 for part in chunks)
    if load + size > 0x10000:
        return None
    payload.extend(b''.join(struct.pack('<H', addresses[word]) for word in words))
    for lane, part in enumerate(chunks):
        start = load + len(player) + len(payload)
        player[info['starts_lo'] + lane] = start & 255
        player[info['starts_hi'] + lane] = start >> 8
        for offset, length, repeat in part:
            if not 1 <= length <= 255 or not 1 <= repeat <= 255:
                raise ValueError('Invalid counted phrase descriptor')
            payload.extend(struct.pack('<BBH', length, repeat, word_base + offset * 2))
        payload.append(0)
    player[info['loop']] = int(loop)
    # Conservative upper bound: cold descriptor setup on every fetch, maximum
    # page-crossing penalties, ordered writes and gate gaps, init/loop margin.
    maximum = 0
    safe = True
    for tick, schedule_id in zip(records, streams[4]):
        runs = packets[schedule_id][3]
        bound = 1000 + (runs + 1) * 330 + runs * 140 + tick[3] * 65
        maximum = max(maximum, bound)
        safe &= bound + 128 < int.from_bytes(tick[:2], 'little')
    label = 'Counted channel phrases' + (' / register templates' if templates else '')
    return ChannelCandidate(bytes(player), bytes(payload), load, label + ' / ' + strategy,
                            info['gap'], sum(map(len, chunks)),
                            sum(repeat > 1 for part in chunks for _, _, repeat in part), maximum, safe)


def channel_candidates(records, loop, load=0x1000):
    """Compare shared/mixed banks and cost refinement without touching the source."""
    if load not in (0x1000, 0x09B4):
        raise ValueError('Unsupported channel player link address')
    result = []
    for separate in (True, False):
        packets, streams = split_records(records, separate)
        seeds = []
        for reverse, mixed in ((False, False), (True, False), (False, True)):
            words, chunks = factor_streams(streams, True, reverse, mixed)
            seeds.append((words, chunks, 'mixed' if mixed else 'reverse' if reverse else 'shared'))
        # Refine the most economical initial word bank. Its unrefined version
        # remains available because fewer descriptors can mean more literal RAM.
        seed = min(seeds, key=lambda item: 2 * len(item[0]) + 4 * sum(map(len, item[1])))
        words, chunks = refine_blocks(streams, seed[0], seed[1])
        seeds.append((words, chunks, 'cost-refined'))
        for words, chunks, strategy in seeds:
            for templates in (False, True):
                candidate = _build(records, packets, streams, words, chunks, loop, load,
                                   templates, True, ('voices-' if separate else 'ticks-') + strategy)
                if candidate is not None:
                    result.append(candidate)
    # Each linked image is distinct; do not verify equivalent seed results twice.
    unique = {}
    for candidate in result:
        unique.setdefault(candidate.player + candidate.data, candidate)
    return sorted(unique.values(), key=lambda c: (c.size + c.zero_page_bytes + c.stack_bytes,
                                                  c.cycles_bound, c.mode))
