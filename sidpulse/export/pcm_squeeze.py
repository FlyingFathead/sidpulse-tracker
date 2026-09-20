"""Existing squeezer algorithms applied to the PCM player's 28 music streams.

Only music packets change. Sample bytes, trigger order and sample timing are
shared by all candidates. Newer versions retain every older encoding as a
fallback, just as the SID-only compiler does.
"""
from dataclasses import dataclass

from .stream_packer import PackedStreams, pack_streams, verify_streams


@dataclass(frozen=True)
class PCMCandidate:
    packed: PackedStreams
    decoder: str = 'plain'
    algorithm: str = 'literal sharing'
    optimized: bool = False

    @property
    def key(self):
        p = self.packed
        return (self.decoder, p.data, p.starts, tuple(p.references.items()),
                tuple(getattr(p, 'calls', {}).items()), getattr(p, 'dictionary', ()))


def literal_streams(streams):
    """Uncompressed baseline in the resident player's literal packet format."""
    data, starts, ranges = bytearray(), [], []
    for stream in streams:
        starts.append(len(data))
        for offset in range(0, len(stream), 127):
            part = stream[offset:offset+127]
            data.append(len(part))
            begin = len(data)
            data.extend(part)
            ranges.append((begin, len(data)))
    result = PackedStreams(bytes(data), tuple(starts), {}, tuple(ranges), 4)
    verify_streams(result, streams)
    return result


def candidates(streams, version, cache, progress=None):
    def memo(name, factory):
        if name not in cache:
            if progress:
                progress('Packing PCM music...', name + '; sample audio is unchanged.')
            cache[name] = tuple(factory())
        return cache[name]

    def v1():
        from .phrase_optimizer import optimize_bank
        seeds = sorted((pack_streams(streams, n) for n in (4, 8, 16, 32, 64)),
                       key=lambda p: (len(p.data), p.minimum_match))
        for packed in seeds:
            verify_streams(packed, streams)
            yield PCMCandidate(packed)
        for seed in seeds[:2]:
            if sum(b-a for a, b in seed.literal_ranges) <= 131072:
                yield PCMCandidate(optimize_bank(streams, seed),
                                   algorithm='v1 phrase bank', optimized=True)

    pool = list(memo('v1.0 literal sharing / phrase bank', v1))
    if version >= 2:
        def v2():
            from .squeeze_v2 import optimize_bank
            seeds = sorted((p for p in pool if not p.optimized), key=lambda p: len(p.packed.data))[:2]
            for seed in seeds:
                if sum(b-a for a, b in seed.packed.literal_ranges) <= 131072:
                    yield PCMCandidate(optimize_bank(streams, seed.packed),
                                       algorithm='v2 overlapping phrase bank', optimized=True)
        pool.extend(memo('v2.0 overlapping phrase bank', v2))
    if version >= 201:
        def phrases():
            from .phrase_calls import pack_phrases
            ordered = sorted(pool, key=lambda p: len(p.packed.data))
            seeds = [ordered[0]]
            plain = next(p for p in ordered if not p.optimized)
            if plain is not seeds[0]:
                seeds.append(plain)
            if sum(map(len, streams)) > 4_000_000:
                return
            for seed in seeds:
                try:
                    packed = pack_phrases(seed.packed, streams)
                except ValueError as exc:
                    if str(exc) == 'Phrase search packet limit exceeded':
                        continue
                    raise
                if packed.calls:
                    yield PCMCandidate(packed, 'phrases', 'v2.0.1 phrase calls', True)
        pool.extend(memo('v2.0.1 phrase calls', phrases))
    if version >= 202:
        def indexed():
            from .indexed_packets import pack_indexed
            for seed in pool:
                if seed.decoder == 'phrases':
                    packed = pack_indexed(seed.packed, streams)
                    # All PCM images reserve the same $0801..$17ff footprint.
                    if len(packed.data) < len(seed.packed.data):
                        yield PCMCandidate(packed, 'indexed', 'v2.0.2 dictionary IDs', True)
        pool.extend(memo('v2.0.2 dictionary IDs', indexed))
    seen = set()
    for candidate in sorted(pool, key=lambda p: len(p.packed.data)):
        if candidate.key not in seen:
            seen.add(candidate.key)
            yield candidate
