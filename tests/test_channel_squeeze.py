"""Generated machine-code and compiler safety regression tests; no SDL needed."""
from copy import deepcopy
from dataclasses import replace
import itertools
import random
import struct

import pytest

from sidpulse.export.channel_phrases import channel_candidates, split_records
from sidpulse.export.psid import compile_song, ExportError, _record_song
from sidpulse.export.replay_verify import verify_replay, VerificationError, CycleBudgetError
from sidpulse.export.squeeze import (make_register_streams, optimized_stream_candidates,
                                     SqueezeOptions, prepare_song)
from sidpulse.song.model import Song, Pattern, Cell


def record(events, period=45000, idle=0):
    return struct.pack('<HBB', period, idle, len(events)) + bytes(v for pair in events for v in pair)


def interleaved(seed=17, count=75):
    rng = random.Random(seed)
    records = []
    for i in range(count):
        # Bass and drums repeat while the lead and shared controls vary.
        events = [(7, i % 7), (0, rng.randrange(256)), (14, i % 11),
                  (8, 0x20), (24, i % 16), (7, i % 7)]
        if i % 4 == 0:
            events[2:2] = [(25, 32)]
        if i % 8 == 1:
            events = []
        records.append(record(events, 45000 + i % 3, i % 3))
    return records


@pytest.mark.parametrize('load', [0x1000, 0x09B4])
@pytest.mark.parametrize('loop', [False, True])
def test_every_new_player_executes_ordered_trace_slow_calls_and_reinitialization(load, loop):
    records = interleaved()
    choices = list(optimized_stream_candidates(records, load)) + channel_candidates(records, loop, load)
    seen = set()
    for choice in choices:
        if hasattr(choice, 'packed'):
            identity = choice.mode
        else:
            identity = 'templates' if 'templates' in choice.mode else 'raw'
        if identity in seen:
            continue
        seen.add(identity)
        checked = verify_replay(choice.image(loop), len(choice.player), records, loop,
                                load=load, gap_address=choice.gap_address)
        assert checked.calls >= len(records) * (2 if loop else 1)
        assert 0 < checked.measured_max_cycles < checked.max_cycles < 36000
        assert checked.stack_bytes <= choice.stack_bytes
    assert seen == {'single', 'lanes', 'registers', 'templates', 'raw'}


def test_changing_lead_does_not_change_bass_or_drum_phrases():
    first = [record([(7, i % 7), (0, i % 2), (14, i % 11)]) for i in range(128)]
    second = [record([(7, i % 7), (0, i), (14, i % 11)]) for i in range(128)]
    a, b = make_register_streams(first), make_register_streams(second)
    assert a[7] == b[7] and a[14] == b[14]
    assert a[0] != b[0] and a[25] == b[25]
    pa, sa = split_records(first, True)
    pb, sb = split_records(second, True)
    assert [pa[x] for x in sa[1]] == [pb[x] for x in sb[1]]
    assert [pa[x] for x in sa[2]] == [pb[x] for x in sb[2]]


@pytest.mark.parametrize('bits', list(itertools.product([False, True], repeat=5)))
def test_all_checkbox_combinations_preserve_original_trace_and_source(bits):
    song = Song(speed=2)
    song.patterns[0].rows = [[Cell(48, 1), Cell(36, 2), Cell()]] + [[Cell(), Cell(), Cell()]]*3
    song.patterns[1] = deepcopy(song.patterns[0])
    song.patterns[4] = Pattern()
    song.orders = [0, 1]
    song.instruments[7] = deepcopy(song.instruments[1])
    song.samples = {'2': {'name': 'unused'}}
    original = deepcopy(song)
    options = SqueezeOptions(*bits)
    cleaned, _ = prepare_song(song, options)
    assert _record_song(cleaned)[1] == _record_song(song)[1]
    result = compile_song(song, squeeze=options)
    assert result.squeeze_report.enabled == bits[0]
    assert song == original


def test_cpu_budget_failure_uses_legacy_without_shortening(monkeypatch):
    import sidpulse.export.psid as psid
    song = Song()
    expected = compile_song(song, squeeze=False)
    def reject(*args, **kwargs):
        raise CycleBudgetError('Deliberately exhausted test budget')
    monkeypatch.setattr(psid, 'verify_replay', reject)
    got = compile_song(song)
    assert got.data == expected.data and got.ticks == expected.ticks
    assert 'CPU budget' in got.squeeze_report.fallback_reason


def test_semantic_verification_failure_is_fatal_not_a_silent_fallback(monkeypatch):
    import sidpulse.export.psid as psid
    original = Song()
    def reject(*args, **kwargs):
        raise VerificationError('Deliberate write mismatch')
    monkeypatch.setattr(psid, 'verify_replay', reject)
    with pytest.raises(ExportError, match='verification failed'):
        compile_song(original)
    assert original == Song()


def test_verifier_refuses_corrupted_machine_code_and_song_data():
    records = interleaved(count=10)
    choice = channel_candidates(records, False)[0]
    image = bytearray(choice.image(False))
    image[0] = 0x02  # unsupported/illegal instruction
    with pytest.raises(VerificationError):
        verify_replay(image, len(choice.player), records, False, gap_address=choice.gap_address)
    with pytest.raises(VerificationError):
        verify_replay(choice.image(False), len(choice.player), [], False)
    wrong = list(records)
    wrong[0] = record([(7, 123)])
    with pytest.raises(VerificationError, match='mismatch'):
        verify_replay(choice.image(False), len(choice.player), wrong, False,
                      gap_address=choice.gap_address)


def test_earlier_candidate_preferences_keep_explicit_opt_out():
    import json
    from sidpulse.preferences import config_path, load_squeeze_options
    path = config_path(); path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({'export_squeeze': {'compact': False, 'enabled': False}}))
    assert load_squeeze_options() == SqueezeOptions(enabled=False, streams=False)
    path.write_text(json.dumps({'export_squeezer': {'phrases': False, 'unused_data': False}}))
    assert load_squeeze_options() == SqueezeOptions(streams=False, unused=False)
