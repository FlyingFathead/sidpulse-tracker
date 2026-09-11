import os

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

import pytest

@pytest.fixture(autouse=True)
def isolated_preferences(tmp_path, monkeypatch):
    monkeypatch.setenv("SIDPULSE_CONFIG_HOME", str(tmp_path / "settings"))
