from copy import deepcopy
import json
import pytest

from sidpulse.commands.editor import Editor
from sidpulse.project.format import ProjectError, decode, encode, load, save
from sidpulse.song.model import Song, example_song


def test_lossless_banks_and_unicode(tmp_path):
    song = example_song()
    song.title = "Yö – Ääni"
    song.samples = {"1": {"name": "Digi 01", "pcm_s16le_base64": "AAABAP//", "rate": 8000}}
    song.macros = {"wave": {"1": {"steps": [16, 32, 64], "loop": 1}}}
    song.instruments[1].macros = {"wave": 1}
    song.filter_programs = {"1": {"cutoff": [10, 1024]}}
    song.export_config = {"load_address": 4096, "preference": "cycles"}
    editor = {"zoom": 2.5, "future_window_setting": {"foo": [1, 2]}}
    path = save(tmp_path / "night.sidpulse", song, editor)
    restored, state = load(path)
    assert restored == song
    assert state == editor
    assert 1 in restored.instruments and "1" in restored.samples


def test_backup_and_failed_replace_preserve_original(tmp_path, monkeypatch):
    song = Song()
    path = save(tmp_path / "work.sidpulse", song)
    first = path.read_bytes()
    song.title = "Revision two"
    save(path, song)
    assert path.with_suffix(".sidpulse.bak").read_bytes() == first
    second = path.read_bytes()
    def fail(*args):
        raise OSError("disk unavailable")
    monkeypatch.setattr("sidpulse.project.format.os.replace", fail)
    song.title = "Cannot save this"
    with pytest.raises(OSError):
        save(path, song)
    assert path.read_bytes() == second


@pytest.mark.parametrize("mutation", [
    lambda d: d.update(format_version=0),
    lambda d: d["song"].update(sid_model="9999"),
    lambda d: d["song"].update(orders=[99]),
    lambda d: d["song"]["patterns"][0]["rows"][0].pop(),
    lambda d: d["song"]["patterns"][0]["rows"][0][0].update(note=True),
    lambda d: d["song"]["instruments"][1].update(pulse_width=4096),
    lambda d: d["song"].update(speed=0),
])
def test_bad_projects_are_rejected(mutation):
    document = encode(Song())
    mutation(document)
    with pytest.raises(ProjectError):
        decode(document)


def test_save_boundary_and_undo_dirty_state():
    editor = Editor()
    editor.enter_note(48)
    editor.mark_saved()
    assert not editor.dirty
    editor.enter_note(50)
    assert editor.dirty
    editor.history.undo(editor.song)
    assert not editor.dirty
    editor.history.redo(editor.song)
    assert editor.dirty


def test_unknown_version_load_does_not_touch_bytes(tmp_path):
    path = tmp_path / "future.sidpulse"
    raw = b'{"format":"SIDPULSE","format_version":9000}'
    path.write_bytes(raw)
    with pytest.raises(ProjectError):
        load(path)
    assert path.read_bytes() == raw
