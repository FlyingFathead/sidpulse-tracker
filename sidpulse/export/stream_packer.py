"""Resident, zero-copy literal sharing. Nothing is expanded into C64 RAM.

Packets: 1..127 = literal length followed by those bytes; $81..$ff =
reference length followed by a LE16 address of an earlier *literal* slice.
There are no references to references, recursive calls, or history buffers.
Addresses are linked only after the complete memory requirement is known.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PackedStreams:
    data: bytes
    starts: tuple[int, ...]
    references: dict[int, int]
    literal_ranges: tuple[tuple[int, int], ...]
    minimum_match: int

    def link(self, address: int) -> bytes:
        if address < 0 or address + len(self.data) > 0x10000:
            raise ValueError('Packed streams do not fit the 16-bit address space')
        result = bytearray(self.data)
        for position, target in self.references.items():
            result[position:position + 2] = (address + target).to_bytes(2, 'little')
        return bytes(result)


def pack_streams(streams: tuple[bytes, ...], minimum_match: int = 16) -> PackedStreams:
    """Greedy/lazy literal sharing with bounded searches and deterministic output.

    A reference is legal only inside a literal packet already stored in the
    output. The shared index spans streams, so a voice can reuse another
    voice's normalized instrument/write sequences without changing its timing.
    Longer minimum matches sometimes save more than eagerly sharing tiny runs;
    the caller compares several complete encodings, including their player.
    """
    if not 4 <= minimum_match <= 127:
        raise ValueError('Minimum match must be 4..127 bytes')
    output = bytearray()
    starts, references, ranges = [], {}, []
    index: dict[bytes, list[tuple[int, int]]] = {}
    ends: dict[int, int] = {}

    def best(data: bytes, pos: int) -> tuple[int, int]:
        if len(data) - pos < minimum_match:
            return 0, 0
        candidates = index.get(data[pos:pos + 4], ())
        best_length, best_address = 0, 0
        for target, start in candidates:
            limit = min(127, ends[start] - target, len(data) - pos)
            if limit <= best_length or limit < minimum_match:
                continue
            # Slice comparisons use the host's bytes implementation. Bounded
            # binary search avoids walking all 127 bytes in Python per match.
            low, high = 4, limit
            while low < high:
                middle = (low + high + 1) // 2
                if output[target:target + middle] == data[pos:pos + middle]:
                    low = middle
                else:
                    high = middle - 1
            if low > best_length:
                best_length, best_address = low, target
        return (best_length, best_address) if best_length >= minimum_match else (0, 0)

    for data in streams:
        starts.append(len(output))
        pos, header = 0, None
        while pos < len(data):
            length, target = best(data, pos)
            # One literal byte can expose a much longer phrase. Do not consume
            # it as part of a short reference just because that reference fits.
            if length and pos + 1 < len(data):
                following, _ = best(data, pos + 1)
                if following > length + 1:
                    length = 0
            if length:
                header = None
                output.append(0x80 | length)
                references[len(output)] = target
                output.extend(b'\0\0')
                pos += length
                continue
            if header is None or output[header] == 127:
                header = len(output)
                output.append(0)
                ranges.append((header + 1, header + 1))
            output.append(data[pos])
            output[header] += 1
            pos += 1
            start = header + 1
            ends[start] = len(output)
            ranges[-1] = (start, len(output))
            if output[header] >= 4:
                target = len(output) - 4
                key = bytes(output[target:target + 4])
                bucket = index.setdefault(key, [])
                bucket.append((target, start))
                # Preserve both early reusable literals and recent long runs.
                if len(bucket) > 32:
                    del bucket[16]
    return PackedStreams(bytes(output), tuple(starts), references, tuple(ranges), minimum_match)


class StreamReader:
    """Independent packet decoder and conservative 6510 read-cost accounting."""
    def __init__(self, packed: PackedStreams):
        self.packed = packed
        self.positions = list(packed.starts)
        self.sources = [0] * len(packed.starts)
        self.left = [0] * len(packed.starts)
        self.cycles = 0

    def read(self, stream: int) -> int:
        data = self.packed.data
        if not self.left[stream]:
            pos = self.positions[stream]
            if not 0 <= pos < len(data):
                raise ValueError('Packed stream ends before its song terminator')
            tag = data[pos]
            count = tag & 127
            if not count:
                raise ValueError('Zero-length packet')
            if tag & 128:
                source = self.packed.references[pos + 1]
                self.positions[stream] = pos + 3
            else:
                source = pos + 1
                self.positions[stream] = source + count
            if source < 0 or source + count > len(data):
                raise ValueError('Packed literal reference is out of range')
            self.sources[stream], self.left[stream] = source, count
            self.cycles += 220  # includes JSR/RTS, page crossings and cold setup
        else:
            self.cycles += 80   # includes JSR/RTS and a source page crossing
        value = data[self.sources[stream]]
        self.sources[stream] += 1
        self.left[stream] -= 1
        return value


def verify_streams(packed: PackedStreams, originals: tuple[bytes, ...]) -> None:
    """Check every decoded byte and every reference's immutable source range."""
    from bisect import bisect_right
    starts = [start for start, _ in packed.literal_ranges]
    for position, target in packed.references.items():
        length = packed.data[position - 1] & 127
        index = bisect_right(starts, target) - 1
        if index < 0:
            raise ValueError('Reference does not point into a literal packet')
        start, end = packed.literal_ranges[index]
        if not start <= target < target + length <= end <= position - 1:
            raise ValueError('Reference crosses a literal boundary or points forward')
    reader = StreamReader(packed)
    for stream, original in enumerate(originals):
        decoded = bytes(reader.read(stream) for _ in original)
        if decoded != original:
            raise ValueError('Lossless stream verification failed')
        if reader.left[stream]:
            raise ValueError('Packet extends beyond the original stream')
