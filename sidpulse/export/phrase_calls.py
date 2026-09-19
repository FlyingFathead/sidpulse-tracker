"""Single-level calls/repeats over literal-sharing packets (SQUEEZER v2.0.1).

Call packet: 0, repeat count, body address LE16. Return packet: $80.
Repeat counts are 1..255. Bodies contain only ordinary literal/reference packets;
there is no recursion, history window or whole-song expansion buffer.
"""
from bisect import bisect_right
from collections import defaultdict
from dataclasses import dataclass, field

from .stream_packer import PackedStreams


@dataclass(frozen=True)
class PhraseStreams(PackedStreams):
    calls: dict[int, int] = field(default_factory=dict)
    phrases: dict[int, int] = field(default_factory=dict)

    def link(self, address):
        result = bytearray(super().link(address))
        for position, target in self.calls.items():
            result[position:position+2] = (address+target).to_bytes(2, 'little')
        return bytes(result)


def pack_phrases(seed: PackedStreams, streams: tuple[bytes, ...]) -> PhraseStreams:
    """Share profitable, non-overlapping sequences of existing packet tokens.

    Candidate gains include the phrase body and every four-byte call and one-byte return. Greedy
    selection is deterministic; it is not an optimal grammar search. Old compact
    candidates remain available including their smaller decoder/state cost.
    """
    if len(seed.starts) != len(streams):
        raise ValueError('Wrong stream count for phrase packing')
    tokens, token_index, sequences, intervals = [], {}, [], []
    for start, stream in zip(seed.starts, streams):
        pos, decoded, sequence = start, 0, []
        while decoded < len(stream):
            tag = seed.data[pos]; count = tag & 127
            if not count or decoded+count > len(stream):
                raise ValueError('Invalid seed packet boundary')
            if tag & 128:
                target = seed.references[pos+1]
                token = (tag, target)
                intervals.append((target, target+count)); pos += 3
            else:
                token = (tag, seed.data[pos+1:pos+1+count]); pos += 1+count
            number = token_index.get(token)
            if number is None:
                number = len(tokens); token_index[token] = number; tokens.append(token)
            sequence.append(number); decoded += count
        sequences.append(tuple(sequence))
    weights = [3 if tag & 128 else tag+1 for tag, _ in tokens]
    # Bound extra host work; callers can still select all older candidates.
    if sum(map(len, sequences)) > 32768:
        raise ValueError('Phrase search packet limit exceeded')
    candidates = []
    for width in (1,2,3,4,6,8,12,16,24,32,48,64,96,128):
        occurrences = defaultdict(list)
        for channel, sequence in enumerate(sequences):
            for pos in range(len(sequence)-width+1):
                occurrences[sequence[pos:pos+width]].append((channel, pos))
        for phrase, locations in occurrences.items():
            if len(locations) < 2:
                continue
            size = sum(weights[t] for t in phrase)
            # Count disjoint occurrences and actual repeat runs. Overlapping
            # matches in a constant stream must not inflate a long body's gain.
            previous_channel, previous_end, repeats = -1, -1, 0
            total = runs = 0
            for channel, pos in locations:
                if channel == previous_channel and pos < previous_end:
                    continue
                if channel == previous_channel and pos == previous_end and repeats < 255:
                    repeats += 1
                else:
                    runs += 1; repeats = 1
                total += 1
                previous_channel, previous_end = channel, pos+width
            estimate = total*size-size-1-4*runs
            if estimate > 0:
                candidates.append((estimate, size, phrase, locations))
    candidates.sort(key=lambda item: (-item[0], -item[1], item[2]))
    occupied = [bytearray(len(s)) for s in sequences]
    plans = [{} for _ in sequences]
    bodies = []
    for _, size, phrase, locations in candidates:
        width = len(phrase); runs = []; total = 0
        previous_channel, previous_end = -1, -1
        for channel, pos in locations:
            if channel == previous_channel and pos < previous_end:
                continue
            if any(occupied[channel][pos:pos+width]):
                continue
            repeats = 1
            while (repeats < 255 and sequences[channel][pos+repeats*width:pos+(repeats+1)*width] == phrase
                   and not any(occupied[channel][pos+repeats*width:pos+(repeats+1)*width])):
                repeats += 1
            end = pos+width*repeats
            runs.append((channel,pos,repeats,end)); total += repeats
            previous_channel, previous_end = channel, end
        if total*size-size-1-4*len(runs) <= 0:
            continue
        index = len(bodies); bodies.append(phrase)
        for channel,pos,repeats,end in runs:
            occupied[channel][pos:end] = b'\1'*(end-pos)
            plans[channel][pos] = (index,repeats,end)
    # Retain only literal bank intervals referenced by ordinary packets.
    retained = []
    for begin,end in sorted(intervals):
        if retained and begin <= retained[-1][1]:
            retained[-1] = (retained[-1][0], max(end,retained[-1][1]))
        else: retained.append((begin,end))
    output, mapping = bytearray(), []
    for begin,end in retained:
        mapping.append((begin,end,len(output))); output.extend(seed.data[begin:end])
    beginnings = [begin for begin,_,_ in mapping]
    references, calls, phrases, starts = {}, {}, {}, []
    literals = [(0,len(output))] if output else []
    def emit(number):
        tag, value = tokens[number]; output.append(tag)
        if tag & 128:
            begin,end,target = mapping[bisect_right(beginnings,value)-1]
            if value+(tag & 127)>end: raise ValueError('Split phrase literal')
            references[len(output)] = target+value-begin; output.extend(b'\0\0')
        else:
            start = len(output); output.extend(value); literals.append((start,len(output)))
    body_starts = [0]*len(bodies)
    suffixes = {}
    for index in sorted(range(len(bodies)),key=lambda i:(-len(bodies[i]),bodies[i])):
        body = bodies[index]
        if body in suffixes:
            start = suffixes[body]
        else:
            start = len(output)
            for offset,number in enumerate(body):
                suffixes.setdefault(body[offset:],len(output)); emit(number)
            output.append(128)
        body_starts[index] = start; phrases[start] = len(body)
    for sequence,plan in zip(sequences,plans):
        starts.append(len(output)); pos = 0
        while pos < len(sequence):
            if pos in plan:
                index,repeats,end = plan[pos]
                output.extend((0,repeats))
                calls[len(output)] = body_starts[index]; output.extend(b'\0\0'); pos = end
            else: emit(sequence[pos]); pos += 1
    packed = PhraseStreams(bytes(output),tuple(starts),references,tuple(literals),seed.minimum_match,calls,phrases)
    verify_phrases(packed,streams)
    return packed


class PhraseReader:
    """Independent byte decoder; conservative cold/call costs bound the 6502."""
    def __init__(self, packed):
        self.packed = packed; n = len(packed.starts)
        self.positions = list(packed.starts)
        self.sources = [0]*n; self.left = [0]*n
        self.repeats = [0]*n; self.returns = [0]*n
        self.cycles = 0

    def read(self, stream):
        data = self.packed.data
        if not self.left[stream]:
            pos = self.positions[stream]
            if not 0 <= pos < len(data): raise ValueError('Phrase stream out of bounds')
            if data[pos] == 128:
                if not self.repeats[stream]: raise ValueError('Return outside phrase')
                self.repeats[stream] -= 1
                site = self.returns[stream]
                pos = self.packed.calls[site+2] if self.repeats[stream] else site+4
                self.cycles += 180
            if not 0 <= pos < len(data): raise ValueError('Phrase continuation out of bounds')
            if data[pos] == 0:
                if self.repeats[stream]: raise ValueError('Nested phrase call')
                if pos+4>len(data) or not data[pos+1]: raise ValueError('Invalid phrase call')
                target = self.packed.calls[pos+2]
                if target not in self.packed.phrases: raise ValueError('Invalid phrase entry')
                self.returns[stream] = pos; self.repeats[stream] = data[pos+1]
                pos = target; self.cycles += 200
            tag = data[pos]; count = tag & 127
            if not count: raise ValueError('Nested call or empty phrase')
            if tag & 128:
                source = self.packed.references[pos+1]; self.positions[stream] = pos+3
            else: source = pos+1; self.positions[stream] = source+count
            if source < 0 or source+count>len(data): raise ValueError('Phrase literal out of bounds')
            self.sources[stream],self.left[stream] = source,count
            self.cycles += 240
        else: self.cycles += 80
        value = data[self.sources[stream]]
        self.sources[stream] += 1; self.left[stream] -= 1
        return value


def verify_phrases(packed, originals):
    """Reject nested calls and references to mutable/encoded/nonliteral data."""
    beginnings = [begin for begin,_ in packed.literal_ranges]
    for position,target in packed.references.items():
        length = packed.data[position-1] & 127
        index = bisect_right(beginnings,target)-1
        if index<0: raise ValueError('Missing phrase literal')
        begin,end = packed.literal_ranges[index]
        if not begin <= target < target+length <= end <= position-1:
            raise ValueError('Phrase reference outside immutable literal bank')
    for position,target in packed.calls.items():
        if (not 2 <= position < len(packed.data)-1 or packed.data[position-2] != 0
                or not packed.data[position-1] or target not in packed.phrases or target >= position-2):
            raise ValueError('Invalid phrase call link')
    for start,count in packed.phrases.items():
        if not 1 <= count <= 128: raise ValueError('Invalid phrase packet count')
        pos = start
        for _ in range(count):
            if not 0 <= pos < len(packed.data): raise ValueError('Truncated phrase body')
            tag = packed.data[pos]
            if not tag & 127: raise ValueError('Nested phrase body')
            pos += 3 if tag & 128 else tag+1
        if pos>=len(packed.data) or packed.data[pos]!=128: raise ValueError('Missing phrase return')
    reader = PhraseReader(packed)
    for channel,stream in enumerate(originals):
        if bytes(reader.read(channel) for _ in stream) != stream:
            raise ValueError('Phrase packing changed decoded data')
        if reader.left[channel]: raise ValueError('Phrase packet exceeds stream')
        pos = reader.positions[channel]
        if reader.repeats[channel]:
            if reader.repeats[channel]!=1 or pos>=len(packed.data) or packed.data[pos]!=128:
                raise ValueError('Phrase expands beyond original stream')
            pos = reader.returns[channel]+4
        end = packed.starts[channel+1] if channel+1<len(packed.starts) else len(packed.data)
        if pos!=end: raise ValueError('Unconsumed phrase stream packets')
