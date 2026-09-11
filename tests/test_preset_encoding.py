"""Preset text must survive systems whose default text encoding is not UTF-8."""
from pathlib import Path

import pytest

from sidpulse.song.model import Instrument
from sidpulse.song.presets import save_user_preset, user_presets


@pytest.mark.parametrize("name", ["My pulse \u00e4", "Y\u00f6 \u2013 \u00c4\u00e4ni", "\u97f3\u8272 \U0001f3b9"])
def test_user_presets_round_trip_with_legacy_default_encoding(monkeypatch, name):
    original_open = Path.open

    def legacy_open(path, mode="r", buffering=-1, encoding=None, errors=None, newline=None):
        if path.parent.name == "presets" and "b" not in mode and encoding in (None, "locale"):
            encoding = "cp1252"
        return original_open(path, mode, buffering, encoding, errors, newline)

    # Reproduce a Windows default without overriding explicitly chosen encodings.
    monkeypatch.setattr(Path, "open", legacy_open)
    instrument = Instrument(name=name, attack=3, pulse_width=0x640)
    path = save_user_preset(instrument)
    assert name.encode("utf-8") in path.read_bytes()

    presets, errors = user_presets()
    assert errors == []
    assert presets == [("User", instrument)]
