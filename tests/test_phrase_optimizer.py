"""Pure compiler tests: exact periods, byte costs, bank liveness and repeats."""
from collections import defaultdict
from functools import lru_cache
import random

import pytest

from sidpulse.export.phrase_optimizer import _parse, optimize_bank
from sidpulse.export.stream_packer import pack_streams, verify_streams
from sidpulse.export.channel_phrases import minimum_period, factor_streams, refine_blocks


@pytest.mark.parametrize('period', [1, 2, 3, 5, 7, 11, 13, 37, 127, 251])
@pytest.mark.parametrize('tail', [False, True])
def test_shortest_period_is_not_restricted_to_tracker_lengths(period, tail):
    phrase = tuple(range(period))
    values = phrase * 4 + (phrase[:max(1, period // 2)] if tail else ())
    assert minimum_period(values) == period
    assert minimum_period(()) == 0
    assert minimum_period((1, 2, 3, 4)) == 4


@pytest.mark.parametrize('seed', range(24))
@pytest.mark.parametrize('version',[1,2])
def test_byte_segmentation_matches_exhaustive_cost_for_fixed_bank(seed,version):
    rng = random.Random(seed)
    bank = bytes(rng.randrange(5) for _ in range(24))
    source = bank[3:14] + bytes(rng.randrange(6) for _ in range(9)) + bank[:15]
    index = defaultdict(list)
    for i in range(len(bank) - 3):
        index[bank[i:i+4]].append(i)

    @lru_cache(None)
    def optimal(pos):
        if pos == len(source):
            return 0
        costs = [1 + n + optimal(pos + n) for n in range(1, min(127, len(source)-pos)+1)]
        for n in range(4, min(127, len(source)-pos)+1):
            if source[pos:pos+n] in bank:
                costs.append(3 + optimal(pos + n))
        return min(costs)

    if version==1:plan = _parse(source, bank, index)
    else:
        from sidpulse.export.squeeze_v2 import _parse as parse_v2
        entries=sorted((bank[i:i+127],i) for i in range(len(bank)-3))
        plan=parse_v2(source,bank,([key for key,_ in entries],[i for _,i in entries]))
    assert sum(3 if target >= 0 else n+1 for _, n, target in plan) == optimal(0)
    assert b''.join(bank[target:target+n] if target >= 0 else source[pos:pos+n]
                    for pos, n, target in plan) == source


@pytest.mark.parametrize('seed', range(10))
def test_optimized_bank_random_roundtrip_deterministic_and_live(seed):
    rng = random.Random(seed)
    phrase = bytes(rng.randrange(256) for _ in range(139))
    streams = (phrase * 8, b'', phrase[8:103]*9, b'\x00'*777,
               bytes(rng.randrange(256) for _ in range(301)))
    old = pack_streams(streams, 16)
    new = optimize_bank(streams, old)
    verify_streams(new, streams)
    assert new == optimize_bank(streams, old)
    assert len(new.link(0x1600)) == len(new.data)
    # A detached bank, when present, consists entirely of referenced bytes.
    if new.literal_ranges and new.literal_ranges[0][0] == 0:
        end = new.literal_ranges[0][1]
        used = set()
        for pos, target in new.references.items():
            used.update(range(target, min(end, target + (new.data[pos-1] & 127))))
        assert used == set(range(end))


@pytest.mark.parametrize('period', [1, 7, 11, 37])
def test_counted_blocks_keep_tail_and_more_than_255_repetitions(period):
    riff = list(range(period))
    streams = [riff * 300 + [999, 998], riff * 17, [], [77]*999, list(range(61))]
    words, blocks = factor_streams(streams, True, False, False)
    refined_words, refined = refine_blocks(streams, words, blocks)
    for original, chunks in zip(streams, refined):
        assert [w for begin, n, repeat in chunks for _ in range(repeat)
                for w in refined_words[begin:begin+n]] == original
        assert all(1 <= n <= 255 and 1 <= repeat <= 255 for _, n, repeat in chunks)
    assert any(repeat > 1 for chunks in refined for _, _, repeat in chunks)
    # Every retained pointer-table word is read by at least one block.
    used = {i for chunks in refined for begin, n, _ in chunks for i in range(begin, begin+n)}
    assert used == set(range(len(refined_words)))
