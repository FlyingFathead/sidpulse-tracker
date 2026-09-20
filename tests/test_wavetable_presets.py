"""The supplied drum presets are the exact standalone reference SID recipes."""
from copy import deepcopy
from pathlib import Path

import pytest

from sidpulse.app import App
from sidpulse.project.format import decode, encode, load
from sidpulse.song.model import Cell, Pattern, Song
from sidpulse.song.presets import built_in_catalog


def drums():
    return [inst for category, inst in built_in_catalog()
            if category == '[Wavetable] Drums & Percussion']


def test_factory_drums_match_reference_and_are_independent():
    reference = load(Path(__file__).resolve().parents[1] / 'examples/synthesized-reference-drums.sidpulse')[0]
    expected = [reference.instruments[i] for i in (1, 2)]
    assert drums() == expected
    changed = drums()
    changed[0].pitch_sequence[0] += 12
    changed[1]._extra_fields['editor_frozen'] = False
    assert drums() == expected


@pytest.mark.parametrize('index', [0, 1])
def test_add_frozen_drum_round_trip_undo_and_sid_export(index):
    from sidpulse.export.psid import compile_song
    inst = drums()[index]
    app = App(audio=False)
    try:
        original = deepcopy(app.editor.song)
        app.open_presets()
        app.dialog['preset_index'] = next(i for i, (_, preset) in enumerate(app.dialog['presets']) if preset == inst)
        app.chooser_add()
        number = app.editor.instrument
        assert app.editor.song.instruments[number] == inst and app.instrument_frozen(number)
        restored = decode(encode(app.editor.song))[0]
        assert restored.instruments[number] == inst
        app.editor.history.undo(app.editor.song)
        assert app.editor.song == original
        app.editor.history.redo(app.editor.song)
        assert app.editor.song.instruments[number] == inst
    finally:
        app.close()
    song = Song(instruments={1: inst}, samples={}, orders=[0],
                patterns={0: Pattern(rows=[[Cell(48, 1), Cell(), Cell()]] * 8)})
    assert not inst.sample_override and inst.sample_slot == 0
    assert compile_song(song).data[:4] == b'PSID'
