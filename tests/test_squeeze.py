"""Export-only compression, source safety, accounting and CLI regressions.

These tests need only pytest. Actual binary execution is tested separately.
"""
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import random
import struct
import sys

import pytest

from sidpulse.export.psid import compile_song, _record_song, ExportMemoryError
from sidpulse.export.prg import compile_prg, PRG_LOAD
from sidpulse.export.squeeze import (SqueezeOptions, prepare_song, resolve_options,
    stream_candidates, verify_candidate, make_streams, COMPACT_PRG_LOAD)
from sidpulse.export.stream_packer import pack_streams, verify_streams, StreamReader
from sidpulse.preferences import config_path, load_squeeze_options, save_squeeze_options, save_preferences
from sidpulse.project.format import load
from sidpulse.song.model import Song, Cell, Pattern, ControlCell, example_song
from sidpulse.song.welcome import welcome_song


def fixture_song():
    song = Song(speed=3, tempo=32, export_config={'loop': False})
    song.instruments[5] = deepcopy(song.instruments[1])
    song.instruments[5].name = 'A differently named copy'
    song.patterns = {0: Pattern(rows=[
        [Cell(48, 5), Cell(24, 2), Cell(36, 4)],
        [Cell(effect='T', parameter=150), Cell(effect='H', parameter=0x34), Cell()],
        [Cell(55, 5, 'G', 0x10), Cell(effect='A', parameter=4), Cell(48, 4, 'S', 0xD2)],
        [Cell(effect='J', parameter=0x37), Cell(effect='F', parameter=0xF2), Cell(effect='S', parameter=0xC2)]],
        controls={0: ControlCell(0x200, 8, 2, 16, 15, 4), 2: ControlCell(slide=-5)})}
    song.patterns[1] = deepcopy(song.patterns[0])
    song.patterns[1].name = 'Same music, different label'
    song.patterns[8] = Pattern()
    song.orders = [0, 1, 0]
    return song


@pytest.mark.parametrize('minimum', [4, 8, 16, 32, 64, 127])
@pytest.mark.parametrize('seed', range(8))
def test_packet_roundtrip_and_literal_only_references(minimum, seed):
    rng = random.Random(seed)
    phrase = bytes(rng.randrange(256) for _ in range(181))
    streams = (b'', bytes(range(256)), phrase * 15, b'\xff' * 999, phrase[29:] * 11)
    packed = pack_streams(streams, minimum)
    verify_streams(packed, streams)
    assert pack_streams(streams, minimum) == packed
    linked = packed.link(0x2100)
    for pos, target in packed.references.items():
        assert struct.unpack_from('<H', linked, pos)[0] == 0x2100 + target
    assert len(linked) == len(packed.data)


def test_bad_reference_and_address_overflow_are_rejected():
    streams = (b'abcdefgh' * 99,)
    packed = pack_streams(streams, 4)
    assert packed.references
    refs = dict(packed.references)
    refs[next(iter(refs))] = len(packed.data) + 1
    with pytest.raises(ValueError):
        verify_streams(replace(packed, references=refs), streams)
    with pytest.raises(ValueError):
        packed.link(65535)
    with pytest.raises(ValueError):
        pack_streams(streams, 3)


def test_cleanup_keeps_order_positions_and_implicit_instrument():
    source = fixture_song()
    before = deepcopy(source)
    prepared, stats = prepare_song(source, SqueezeOptions())
    assert source == before
    assert prepared.orders == [0, 0, 0]
    assert stats.duplicate_patterns == 1 and stats.duplicate_instruments == 1
    assert stats.unused_patterns == 1 and stats.unused_instruments == 1
    assert min(prepared.instruments) == min(source.instruments)
    assert _record_song(source)[1] == _record_song(prepared)[1]
    # An effect or a shared-filter change is not a duplicate pattern.
    source.patterns[1].controls[0].volume = 9
    prepared, stats = prepare_song(source, SqueezeOptions())
    assert stats.duplicate_patterns == 0
    assert _record_song(source)[1] == _record_song(prepared)[1]


@pytest.mark.parametrize('field', ['patterns', 'instruments', 'unused', 'streams'])
def test_individual_options_can_be_disabled_without_source_changes(field):
    song = fixture_song(); before = deepcopy(song)
    result = compile_song(song, squeeze=replace(SqueezeOptions(), **{field: False}))
    assert song == before
    assert result.squeeze_report.enabled
    if field == 'streams':
        assert result.data == compile_song(song, squeeze=False).data


@pytest.mark.parametrize('clock', ['PAL', 'NTSC'])
@pytest.mark.parametrize('loop', [False, True])
@pytest.mark.parametrize('factory', [Song, fixture_song, welcome_song, example_song])
def test_both_stream_codecs_verify_exact_original_timing_and_writes(clock, loop, factory):
    song = factory(); song.clock = clock; song.export_config['loop'] = loop
    original = deepcopy(song)
    records = _record_song(song)[1]
    prepared, _ = prepare_song(song, SqueezeOptions())
    assert _record_song(prepared)[1] == records
    for candidate in stream_candidates(records):
        assert candidate.safe_timing
        assert verify_candidate(candidate.packed, records, candidate.mode == 'lanes')[0] == candidate.cycles_bound
        assert len(candidate.image(loop)) == candidate.size
    assert song == original


@pytest.mark.parametrize('factory', [Song, example_song, welcome_song])
@pytest.mark.parametrize('compiler', [compile_song, compile_prg])
def test_default_enabled_reduces_actual_resident_image_not_just_file(factory, compiler):
    song = factory(); before = deepcopy(song)
    legacy = compiler(song, squeeze=False)
    packed = compiler(song)
    report = packed.squeeze_report
    assert report.enabled and report.saved_bytes == len(legacy.data) - len(packed.data) > 0
    assert report.resident_bytes < report.original_resident_bytes
    assert report.payload_bytes == report.player_bytes + report.song_data_bytes
    assert report.zero_page_bytes in (2, 4)
    if compiler is compile_prg:
        assert report.zero_page_bytes == 4
    assert song == before
    assert compiler(song, squeeze=False).data == legacy.data


def test_long_sparse_song_previously_lost_to_flat_tick_pointer_table_now_fits():
    song = Song(speed=2)
    song.patterns[0].rows = [[Cell(24+i//4, 1) if i % 4 == 0 else Cell(), Cell(), Cell()] for i in range(256)]
    song.orders = [0] * 34
    with pytest.raises(ExportMemoryError):
        compile_song(song, squeeze=False)
    packed = compile_song(song)
    assert packed.ticks == 17408
    assert len(packed.data) < 7000


def test_independent_voice_data_does_not_depend_on_other_voice_changes():
    def record(t, bass, lead):
        events = bytes([7, bass, 0, lead, 8, 17])
        return struct.pack('<HBB', t, 0, 3) + events
    records_a = [record(19000, i % 4, 33) for i in range(64)]
    records_b = [record(19000, i % 4, i) for i in range(64)]
    assert make_streams(records_a, True)[1] == make_streams(records_b, True)[1]
    assert make_streams(records_a, True)[0] != make_streams(records_b, True)[0]


def test_migrated_preferences_default_on_and_merge_unrelated_settings():
    assert load_squeeze_options() == SqueezeOptions()
    save_preferences({'theme': 'Charcoal crimson', 'audio_buffer': 2048})
    assert load_squeeze_options() == SqueezeOptions()
    options = SqueezeOptions(enabled=False, patterns=False)
    save_squeeze_options(options)
    assert load_squeeze_options() == options
    import json
    data = json.loads(config_path().read_text())
    assert data['theme'] == 'Charcoal crimson' and data['audio_buffer'] == 2048
    data['export_squeeze'] = {'enabled': 'false', 'instruments': False, 'unknown': 1}
    config_path().write_text(json.dumps(data))
    assert load_squeeze_options() == SqueezeOptions(instruments=False)
    config_path().write_text('[]')
    assert load_squeeze_options() == SqueezeOptions()


def test_options_are_strict_and_master_off_does_not_run_cleanup():
    with pytest.raises(ValueError): SqueezeOptions(enabled=1)
    with pytest.raises(TypeError): resolve_options('yes')
    source = fixture_song()
    prepared, stats = prepare_song(source, SqueezeOptions(enabled=False))
    assert prepared == source and prepared is not source
    assert not any(vars(stats).values())


@pytest.mark.parametrize('target', ['sid', 'prg'])
@pytest.mark.parametrize('enabled', [False, True])
def test_cli_export_switch_preserves_source_and_ignores_desktop_preferences(target, enabled, tmp_path, monkeypatch, capsys):
    from sidpulse.__main__ import main
    save_squeeze_options(SqueezeOptions(enabled=not enabled))
    output = tmp_path / ('song.' + target)
    argv = ['sidpulse', '--export-' + target, str(output)]
    if not enabled: argv.append('--no-squeeze-song')
    monkeypatch.setattr(sys, 'argv', argv)
    assert main() == 0
    compiler = compile_prg if target == 'prg' else compile_song
    assert output.read_bytes() == compiler(Song(), squeeze=enabled).data
    assert load(output.with_suffix('.sidpulse'))[0] == Song()
    assert 'resident RAM' in capsys.readouterr().out


def test_squeeze_cli_rejected_outside_export(monkeypatch):
    from sidpulse.__main__ import main
    monkeypatch.setattr(sys, 'argv', ['sidpulse', '--no-squeeze-song'])
    with pytest.raises(SystemExit) as error: main()
    assert error.value.code == 2


def test_cpu_dense_fast_song_uses_verified_smaller_layout_or_legacy():
    song = example_song(); song.tempo = 255
    packed = compile_song(song)
    legacy = compile_song(song, squeeze=False)
    assert len(packed.data) <= len(legacy.data)
    if packed.data == legacy.data:
        assert 'CPU budget' in packed.squeeze_report.fallback_reason
        assert packed.squeeze_report.saved_bytes == 0
    else:
        assert packed.squeeze_report.verified_calls > 0
        assert (packed.squeeze_report.verified_max_cycles + 128) * 5 < min(
            (r[0] | r[1] << 8) * 4 for r in _record_song(song)[1])


def test_unused_sample_bank_is_not_discarded_from_the_project():
    song = Song(samples={'1': {'name': 'Digi 01', 'pcm_s16le_base64': 'AAABAP//', 'rate': 8000}})
    before = deepcopy(song)
    result = compile_song(song)
    assert song == before and result.squeeze_report.cleanup.unused_samples == 1
    assert any('PCM' in warning for warning in result.warnings)
    assert compile_song(song, squeeze=SqueezeOptions(unused=False)).squeeze_report.cleanup.unused_samples == 0


def test_pattern_jump_targets_are_order_positions_not_deduplicated_pattern_ids():
    song = fixture_song()
    song.patterns[0].rows[0][0] = Cell(effect='B', parameter=2)
    # Do not put the jump pattern at order 2, which would revisit itself.
    song.orders = [0, 1, 1]
    prepared, _ = prepare_song(song, SqueezeOptions())
    assert len(prepared.orders) == 3
    assert _record_song(prepared)[1] == _record_song(song)[1]


def test_squeezed_memory_preflight_precedes_linking_and_preserves_source(monkeypatch):
    song = Song(); before = deepcopy(song)
    monkeypatch.setattr('sidpulse.export.psid.LIMIT', 0x1080)
    with pytest.raises(ExportMemoryError) as caught:
        compile_song(song)
    error = caught.value
    assert error.budget_bytes == 128
    assert error.required_bytes == error.player_bytes + error.record_bytes + error.sequence_bytes
    assert error.sequence_bytes == 0 and error.player_bytes == 406
    assert song == before
