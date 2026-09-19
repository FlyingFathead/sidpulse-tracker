"""Lossless resident phrase calls, malformed boundaries, and independent 6502 checks."""
from dataclasses import replace
import json
from pathlib import Path
import random

import pytest

from sidpulse.export.phrase_calls import pack_phrases, verify_phrases, PhraseReader
from sidpulse.export.stream_packer import PackedStreams, pack_streams
from sidpulse.export.squeeze import (StreamCandidate, make_streams, make_register_streams,
                                     verify_candidate, SqueezeOptions)
from sidpulse.export.replay_verify import ReplayCPU, verify_replay
from sidpulse.export.psid import compile_song
from sidpulse.song.model import Song, example_song
from test_channel_squeeze import interleaved


def literal_seed(packet_streams):
    data, starts, ranges = bytearray(), [], []
    for packets in packet_streams:
        starts.append(len(data))
        for packet in packets:
            assert 1 <= len(packet) <= 127
            data.append(len(packet)); start = len(data); data.extend(packet)
            ranges.append((start, len(data)))
    return PackedStreams(bytes(data), tuple(starts), {}, tuple(ranges), 4)


@pytest.mark.parametrize('seed', range(8))
def test_mixed_literals_references_empty_streams_and_deterministic_linking(seed):
    rng = random.Random(seed)
    fragments = [rng.randbytes(29) for _ in range(5)]
    streams = (b'',) + tuple(b''.join(rng.choice(fragments) for _ in range(90)) for _ in range(3))
    streams += (b'ABCD'*2000, bytes(range(256))*12, b'')
    original = pack_streams(streams, 8)
    packed = pack_phrases(original, streams)
    assert packed.calls
    assert packed == pack_phrases(original, streams)
    verify_phrases(packed, streams)
    linked = packed.link(0x20ff)
    for position, target in (packed.calls | packed.references).items():
        assert int.from_bytes(linked[position:position+2], 'little') == 0x20ff+target
    with pytest.raises(ValueError, match='16-bit'):
        packed.link(65536-len(packed.data)+1)


def test_repeat_255_split_and_shared_body_across_streams():
    # Force a single packet type so both repeat count boundaries are exercised.
    packets = [[b'phrase!']*600, [b'phrase!']*300, []]
    streams = tuple(b''.join(part) for part in packets)
    packed = pack_phrases(literal_seed(packets), streams)
    assert len(packed.data) < 100
    assert max(packed.data[position-1] for position in packed.calls) == 255
    assert len(set(packed.calls.values())) == 1
    verify_phrases(packed, streams)


def test_identical_phrase_suffix_shares_the_existing_return():
    packets = [[b'A'*40,b'B'*40,b'C'*40]*100, [b'B'*40,b'C'*40]*20]
    streams = tuple(b''.join(part) for part in packets)
    packed = pack_phrases(literal_seed(packets), streams)
    starts = sorted(packed.phrases)
    assert len(starts) == 2 and starts[1]-starts[0] == 41
    assert packed.phrases[starts[0]] == 3 and packed.phrases[starts[1]] == 2
    assert len(packed.data) == 3*41+1+2*4
    verify_phrases(packed, streams)


@pytest.mark.parametrize('kind', ['repeat_zero', 'repeat_extra', 'missing_return', 'nested', 'bad_target', 'trailing'])
def test_malformed_calls_fail_without_silent_truncation(kind):
    streams = (b'abcdef'*100,)
    packed = pack_phrases(literal_seed([[b'abcdef']*100]), streams)
    data = bytearray(packed.data)
    position, target = next(iter(packed.calls.items()))
    if kind == 'repeat_zero': data[position-1] = 0
    elif kind == 'repeat_extra': data[position-1] += 1
    elif kind == 'missing_return': data[target+7] = 1
    elif kind == 'nested': data[target] = 0
    elif kind == 'bad_target': packed = replace(packed, calls={position: position-2})
    else: data.extend((1, 99))
    with pytest.raises(ValueError): verify_phrases(replace(packed, data=bytes(data)), streams)


def test_literal_reference_cannot_alias_encoded_data():
    streams = (bytes(range(100))*100,)
    packed = pack_phrases(pack_streams(streams, 8), streams)
    position = next(iter(packed.references))
    references = dict(packed.references); references[position] = packed.starts[0]
    with pytest.raises(ValueError, match='literal'):
        verify_phrases(replace(packed, references=references), streams)


@pytest.mark.parametrize('mode', ['single', 'lanes', 'registers'])
@pytest.mark.parametrize('load', [0x1000, 0x09b4])
@pytest.mark.parametrize('loop', [False, True])
def test_both_6502_engines_agree_on_every_call_cycle_write_loop_and_reinit(mode, load, loop):
    from py65_nmos import MPU
    from test_psid import Memory, call
    records = interleaved(count=48)*5
    streams = make_register_streams(records) if mode == 'registers' else make_streams(records, mode == 'lanes')
    packed = pack_phrases(pack_streams(streams, 8), streams)
    assert packed.calls
    assets = Path(__file__).resolve().parents[1]/'sidpulse/assets'
    name = 'squeeze-phrases-'+mode+('-prg' if load != 0x1000 else '')
    info = json.loads((assets/'replay-players.json').read_text())[name]
    player = (assets/(name+'.bin')).read_bytes()
    bound, safe = verify_candidate(packed, records, mode == 'lanes',
                                    registers=mode == 'registers', reader_type=PhraseReader)
    choice = StreamCandidate(mode, packed, player, bound, safe, load, info['gap'])
    image = choice.image(loop)
    checked = verify_replay(image, len(player), records, loop, load=load, gap_address=info['gap'])
    assert checked.measured_max_cycles < bound and checked.stack_bytes <= 4
    mem = Memory(); mem[load:load+len(image)] = image
    class InstrumentedMPU(MPU):
        def step(self):
            if self.pc == info['gap']: mem.events.append((25, 32))
            return super().step()
    independent = InstrumentedMPU(memory=mem)
    bundled = ReplayCPU(image, len(player), load=load, gap_address=info['gap'])
    addresses = []
    for traversal in range(2 if loop else 1):
        for index, record in enumerate(records):
            addresses.append(load if not traversal and not index else load+3)
            addresses.extend([load+3]*record[2])
    if not loop: addresses.extend([load+3]*2)
    addresses.append(load)
    for address in addresses:
        mem.events.clear(); mem.writes.clear(); independent.p |= independent.DECIMAL
        actual = call(independent, address)
        assert actual == bundled.call(address)
        assert mem.events == bundled.events
        assert [(a,v) for a,v in mem.writes if a in (0xdc04,0xdc05,0xdc0e)] == bundled.timer_events
        assert all(0x100 <= a < 0x200 or load <= a < load+len(player)
                   or a in (0xf8,0xf9,0xdc04,0xdc05,0xdc0e) or 0xd400 <= a <= 0xd418
                   for a,_ in mem.writes)


@pytest.mark.parametrize('factory', [Song, example_song])
def test_new_family_keeps_smaller_old_candidates_and_original_song(factory):
    from copy import deepcopy
    song = factory(); before = deepcopy(song)
    old = compile_song(song, squeeze=SqueezeOptions(version=2))
    new = compile_song(song, squeeze=SqueezeOptions(version=201))
    assert len(new.data) <= len(old.data)
    assert song == before and new.ticks == old.ticks and new.seconds == old.seconds
    assert new.squeeze_report.squeezer_version == 201
