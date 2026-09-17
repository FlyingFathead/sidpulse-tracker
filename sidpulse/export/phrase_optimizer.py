"""Cost-driven static phrase-bank optimization for resident byte streams.

No new bytecode or C64 workspace is required: the existing decoder references
immutable literal slices. A host-side DP selects the cheapest sequence of
literal packets and references for the available bank. Bank discovery remains
bounded and heuristic; the exporter also retains the original candidates.
"""
from __future__ import annotations
from collections import defaultdict, deque

from .stream_packer import PackedStreams, verify_streams


def _literal_bank(packed: PackedStreams) -> bytearray:
    """Share exact substrings and tail overlaps before assigning addresses."""
    pieces = {packed.data[a:b] for a, b in packed.literal_ranges if b - a >= 4}
    bank = bytearray()
    for piece in sorted(pieces, key=lambda p: (-len(p), p)):
        if bank.find(piece) >= 0:
            continue
        overlap = 0
        for n in range(min(len(bank), len(piece) - 1), 0, -1):
            if bank.endswith(piece[:n]):
                overlap = n
                break
        bank.extend(piece[overlap:])
    return bank


def _parse(stream: bytes, bank: bytes, index: dict[bytes, list[int]]):
    """Exact byte-cost segmentation for the indexed literal matches.

    At most 64 bank positions are examined for any four-byte prefix, with exact
    comparisons after lookup. Every length from 4 to the longest verified match
    is eligible, not only powers of two or tracker-row boundaries.
    """
    n = len(stream)
    costs = [0] * (n + 1)
    packets = [0] * (n + 1)
    lengths = bytearray(n)
    sources = [-1] * n
    # Descending indices. The key cost[j]+j selects the cheapest literal end;
    # each candidate end is inserted and removed only once.
    literal_ends = deque()
    for pos in range(n - 1, -1, -1):
        j = pos + 1
        key = (costs[j] + j, packets[j], -j)
        while literal_ends and key <= (costs[literal_ends[-1]] + literal_ends[-1],
                                      packets[literal_ends[-1]], -literal_ends[-1]):
            literal_ends.pop()
        literal_ends.append(j)
        while literal_ends[0] > pos + 127:
            literal_ends.popleft()
        end = literal_ends[0]
        best = (end - pos + 1 + costs[end], 1 + packets[end], -(end - pos))
        length, source = end - pos, -1
        maximum, target = 0, -1
        if pos + 4 <= n:
            for offset in index.get(stream[pos:pos + 4], ()):
                limit = min(127, n - pos, len(bank) - offset)
                if limit <= maximum:
                    continue
                lo, hi = 4, limit
                while lo < hi:
                    middle = (lo + hi + 1) // 2
                    if bank[offset:offset + middle] == stream[pos:pos + middle]:
                        lo = middle
                    else:
                        hi = middle - 1
                if lo > maximum:
                    maximum, target = lo, offset
            if maximum >= 4:
                end = min(range(pos + 4, pos + maximum + 1),
                          key=lambda j: (costs[j], packets[j], -j))
                candidate = (3 + costs[end], 1 + packets[end], -(end - pos))
                if candidate < best:
                    best = candidate
                    length, source = end - pos, target
        costs[pos], packets[pos] = best[:2]
        lengths[pos], sources[pos] = length, source
    out = []
    pos = 0
    while pos < n:
        count = lengths[pos]
        out.append((pos, count, sources[pos]))
        pos += count
    return out


def optimize_bank(streams: tuple[bytes, ...], seed: PackedStreams) -> PackedStreams:
    bank = bytes(_literal_bank(seed))
    index = defaultdict(list)
    for pos in range(max(0, len(bank) - 3)):
        entries = index[bank[pos:pos + 4]]
        entries.append(pos)
        if len(entries) > 64:
            del entries[32]
    plans = [_parse(stream, bank, index) for stream in streams]
    # Remove unused bank spans. Every referenced interval is kept intact and
    # direct pointers are rebuilt, so unrelated gaps consume no C64 RAM.
    intervals = sorted((source, source + count) for plan in plans
                       for _, count, source in plan if source >= 0)
    retained = []
    for begin, end in intervals:
        if retained and begin <= retained[-1][1]:
            retained[-1] = (retained[-1][0], max(end, retained[-1][1]))
        else:
            retained.append((begin, end))
    output = bytearray()
    mapping = []
    for begin, end in retained:
        mapping.append((begin, end, len(output)))
        output.extend(bank[begin:end])
    original_starts = [begin for begin, _, _ in mapping]
    from bisect import bisect_right
    references, starts = {}, []
    ranges = [(0, len(output))] if output else []
    for stream, plan in zip(streams, plans):
        starts.append(len(output))
        for pos, count, source in plan:
            if source < 0:
                output.append(count)
                start = len(output)
                output.extend(stream[pos:pos + count])
                ranges.append((start, len(output)))
            else:
                begin, end, target = mapping[bisect_right(original_starts, source) - 1]
                if source + count > end:
                    raise ValueError('Optimizer split a live phrase')
                output.append(128 | count)
                references[len(output)] = target + source - begin
                output.extend(b'\0\0')
    packed = PackedStreams(bytes(output), tuple(starts), references, tuple(ranges), seed.minimum_match)
    verify_streams(packed, streams)
    return packed
