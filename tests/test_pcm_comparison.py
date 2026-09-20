"""PCM comparison must measure actual encodings and preserve the source/audio."""
from copy import deepcopy
from dataclasses import replace

import pygame as pg
import pytest

from sidpulse.export.comparison import compile_comparison
from sidpulse.export.pcm import compile_pcm
from sidpulse.export.squeeze import SqueezeOptions
from sidpulse.song.model import Cell, Instrument
from test_pcm_media import pcm_song


def repeating_song():
    song = pcm_song(4005)
    song.speed = 6
    song.instruments[2] = Instrument(waveform=64)
    song.patterns[0].rows = [[Cell(36+i%4, 2), Cell(48+(i//4)%4, 2),
                             Cell(48, 1) if i%4 == 0 else Cell()] for i in range(16)]
    song.orders = [0]*4
    return song


@pytest.mark.parametrize('kind', ['prg', 'sid'])
def test_pcm_versions_are_real_and_cached_results_match_independent_exports(kind, monkeypatch):
    import sidpulse.export.pcm as pcm
    song = repeating_song()
    before = deepcopy(song)
    options = SqueezeOptions()
    expected = {v: compile_pcm(song, kind=kind, squeeze=replace(options, version=v))
                for v in (1, 2, 201, 202)}
    recorded = []
    original = pcm.record_pcm
    def record(*args, **kwargs):
        recorded.append(1)
        return original(*args, **kwargs)
    monkeypatch.setattr(pcm, 'record_pcm', record)
    comparison = compile_comparison(song, options, kind)
    assert len(recorded) == 1
    assert {e.version: e.result for e in comparison.entries} == expected
    assert song == before
    sizes = [len(e.result.data) for e in comparison.entries]
    assert sizes == sorted(sizes, reverse=True) and len(set(sizes)) >= 3
    assert 'phrase calls' in expected[201].squeeze_report.algorithm
    assert 'dictionary IDs' in expected[202].squeeze_report.algorithm
    assert all(e.result.squeeze_report.squeezer_version == e.version for e in comparison.entries)
    assert len(comparison.best.result.data) == min(sizes)


def test_packing_off_keeps_pcm_and_embedded_project_intact():
    song = repeating_song()
    before = deepcopy(song)
    off = compile_pcm(song, kind='prg', squeeze=False)
    streams_off = compile_pcm(song, kind='prg', squeeze=SqueezeOptions(streams=False))
    on = compile_pcm(song, kind='prg')
    assert song == before and off.data == streams_off.data
    assert off.squeeze_report.verified_calls and 'uncompressed music' in off.squeeze_report.summary()
    assert len(off.data) > len(on.data)
    assert off.unique_records == on.unique_records and off.seconds == on.seconds


def test_oversized_pcm_version_does_not_hide_smaller_verified_version(monkeypatch):
    import sidpulse.export.pcm as pcm
    song = repeating_song()
    result = compile_pcm(song, kind='prg')
    monkeypatch.setattr(pcm, 'LIMIT', pcm.LOAD+len(result.data)-2)
    comparison = compile_comparison(song, SqueezeOptions(), 'prg')
    assert comparison.entries[0].result is None and comparison.entries[0].error
    assert comparison.entries[-1].result is not None


def test_unsafe_smallest_candidate_falls_back_but_bad_audio_is_fatal(monkeypatch):
    import sidpulse.export.pcm_verify as verify
    from sidpulse.export.replay_verify import CycleBudgetError, VerificationError
    song = repeating_song()
    small = compile_pcm(song, kind='prg')
    real = verify.verify_pcm
    def reject_small(image, *args, **kwargs):
        if len(image)+2 == len(small.data):
            raise CycleBudgetError('Test music deadline exceeded')
        return real(image, *args, **kwargs)
    monkeypatch.setattr(verify, 'verify_pcm', reject_small)
    fallback = compile_pcm(song, kind='prg')
    assert len(fallback.data) > len(small.data)
    def corrupt(*args, **kwargs):
        raise VerificationError('Test sample mismatch')
    monkeypatch.setattr(verify, 'verify_pcm', corrupt)
    with pytest.raises(VerificationError, match='sample mismatch'):
        compile_comparison(song, SqueezeOptions(), 'prg')


@pytest.mark.parametrize('size', [(640,480), (960,1080), (1280,900)])
def test_pcm_comparison_controls_mouse_keyboard_and_export(tmp_path, size):
    from sidpulse.app import App
    from sidpulse.project.format import save, load
    from sidpulse.ui import export_squeezer as ui
    from sidpulse.ui.squeezer_comparison import visible_entries
    from sidpulse.preferences import load_squeeze_options, load_squeeze_comparison
    from export_gui_helpers import finish_export_analysis
    app = App(repeating_song(), audio=False, size=size)
    try:
        before = deepcopy(app.editor.song)
        ui.open_dialog(app, 'prg')
        finish_export_analysis(app)
        assert app.dialog['pcm'] and len(app.dialog['comparison'].entries) == 4
        ui.toggle_all_versions(app)
        assert len(visible_entries(app.dialog)) == 3
        # Focus scrolls the actual controls into the viewport on every size.
        app.dialog['focus'] = 11
        app.dialog['ensure_focus'] = True
        app.renderer.render(app)
        rect, version = next((r,v) for r,a,v in app.renderer.hits if a == 'squeeze_use_version')
        assert app.screen.get_rect().contains(rect)
        app.handle(pg.event.Event(pg.MOUSEBUTTONDOWN, button=1, pos=rect.center))
        assert app.dialog['options'].version == version
        app.dialog['focus'] = 10
        app.handle(pg.event.Event(pg.KEYDOWN, key=pg.K_SPACE, mod=0))
        assert not app.dialog['compare'] and app.dialog['result'] is None
        ui.select_version(app, 1)
        ui.analyze(app)
        finish_export_analysis(app)
        expected = app.dialog['result'].data
        received = []
        app.prompt_export = lambda result, kind: received.append((result.data, kind))
        ui.activate(app, 'export')
        assert app.dialog['kind'] == 'pcm_export_confirm' and not received
        app.handle(pg.event.Event(pg.KEYDOWN, key=pg.K_y, mod=0))
        assert received == [(expected, 'prg')]
        assert load_squeeze_options().version == 1 and load_squeeze_comparison() is False
        assert app.editor.song == before
        assert load(save(tmp_path/'song.sidpulse', app.editor.song))[0] == before
        ui.open_dialog(app, 'prg')
        finish_export_analysis(app)
        ui.toggle(app, 0)
        ui.analyze(app)
        finish_export_analysis(app)
        assert app.dialog['comparison'] is None
        assert 'uncompressed music' in app.dialog['result'].squeeze_report.algorithm
        ui.activate(app, 'cancel')
    finally:
        app.close()
