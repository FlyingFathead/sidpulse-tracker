"""SQUEEZER v2.0: overlapping phrase banks and complete bounded match lookup.

The v1.0 optimizer remains unchanged in phrase_optimizer.py. Both sets of
candidates use the same resident decoder and exact playback checks. Bank
placement is heuristic; this is not a claim of globally optimal compression.
"""
from __future__ import annotations
from collections import defaultdict, deque
from bisect import bisect_left

from .stream_packer import PackedStreams, verify_streams


def _literal_bank(packed: PackedStreams) -> bytearray:
    """Greedily merge matching fragment ends, with deterministic tie breaking.

    v1 only shares overlaps at the growing bank's last tail. Here any two
    remaining fragment ends can meet. Matches are bounded to the decoder's
    127-byte phrase limit; no recursive reference or C64 workspace is added.
    """
    pieces = sorted({packed.data[a:b] for a,b in packed.literal_ranges if b-a >= 4},
                    key=lambda piece: (-len(piece),piece))
    fragments = dict(enumerate(pieces))
    for length in range(126,0,-1):
        prefixes = defaultdict(set)
        for index,piece in fragments.items():
            if len(piece)>length:prefixes[piece[:length]].add(index)
        for index in list(fragments):
            while index in fragments:
                piece=fragments[index]
                if len(piece)<=length:break
                matches=prefixes.get(piece[-length:],set())-{index}
                if not matches:break
                other=min(matches);tail=fragments.pop(other)
                prefixes[tail[:length]].discard(other)
                fragments[index]=piece+tail[length:]
    return bytearray(b''.join(fragments.values()))


def _parse(stream: bytes, bank: bytes, index: dict[bytes, list[int]]):
    """Exact byte-cost segmentation for the indexed literal matches.

    Lexicographic neighbors find the longest match among all bank positions.
    Comparisons are bounded to 127 bytes. Every length from 4 to that maximum
    is eligible. The DP minimizes packet bytes, then packet count.
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
            probe=stream[pos:pos+127]
            at=bisect_left(index[0],probe)
            neighbors=index[1][max(0,at-1):at+1]
            for offset in neighbors:
                if bank[offset:offset+4]!=probe[:4]:continue
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
    entries=sorted((bank[pos:pos+127],pos) for pos in range(max(0,len(bank)-3)))
    index=([key for key,_ in entries],[pos for _,pos in entries])
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


def additional_candidates(records, original_candidates):
    from dataclasses import replace
    from .squeeze import make_streams,make_register_streams,verify_candidate
    for mode in ('single','lanes','registers'):
        seeds=sorted((item for item in original_candidates
                      if item.mode==mode and not item.optimized),key=lambda item:item.size)[:2]
        streams=(make_register_streams(records) if mode=='registers'
                 else make_streams(records,mode=='lanes'))
        for seed in seeds:
            # Bound extra host memory/work for pathological oversized inputs.
            # All original encodings remain available even if this pass skips.
            if sum(b-a for a,b in seed.packed.literal_ranges)>131072:continue
            packed=optimize_bank(streams,seed.packed)
            cycles,safe=verify_candidate(packed,records,mode=='lanes',registers=mode=='registers')
            yield replace(seed,packed=packed,cycles_bound=cycles,safe_timing=safe,
                          optimized=True,optimizer_version=2)
