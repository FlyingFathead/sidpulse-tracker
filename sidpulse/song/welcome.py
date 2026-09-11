"""The welcome arrangement is an ordinary, editable native project."""
from pathlib import Path

from sidpulse.project.format import load


def welcome_song():
    """Load a fresh document without giving the editor the bundled asset's path."""
    path = Path(__file__).resolve().parents[1] / 'assets/autumn-at-five.sidpulse'
    song, _ = load(path)
    return song
