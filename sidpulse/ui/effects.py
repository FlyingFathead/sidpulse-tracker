"""Effect help capabilities; these are not claims of an implemented player."""
import json
from pathlib import Path

EFFECTS = json.loads((Path(__file__).resolve().parents[1] / "assets/effects.json").read_text())["effects"]
STATUS = {"implemented": "LIVE", "partial": "PART", "planned": "LATER", "mapping": "MAP?", "future_digi": "DIGI", "not_applicable": "NA"}


def visible_effects():
    return [entry for entry in EFFECTS if entry["visible"] and entry["visible_in_help"]]


def lookup_effect(letter, parameter):
    code = letter + (f"{parameter:02X}" if parameter is not None else "00")
    matches = [e for e in EFFECTS if all(a.islower() or a == b for a, b in zip(e["code"], code))]
    return max(matches, key=lambda e: sum(c.isupper() or c.isdigit() for c in e["code"]), default=None)
