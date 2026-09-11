"""One editable capability registry for keyboard dispatch, menus and help.

Routing targets are descriptive names, never eval'd Python. Semantic command
execution stays in the editor; the JSON decides whether a binding is available.
"""
import json
from pathlib import Path
import pygame as pg

REGISTRY_PATH = Path(__file__).resolve().parents[1] / "assets" / "commands.json"


def read_registry(path=REGISTRY_PATH):
    document = json.loads(Path(path).read_text(encoding="utf-8"))
    if document.get("registry_version") != 1:
        raise ValueError("Unsupported command registry version")
    seen = set()
    for entry in document["commands"]:
        if entry["id"] in seen:
            raise ValueError(f"Duplicate command ID: {entry['id']}")
        seen.add(entry["id"])
        for flag in ("applicable", "implemented", "keybind_in_use", "visible", "visible_in_help", "visible_in_menu"):
            if type(entry[flag]) is not bool:
                raise ValueError(f"{entry['id']}.{flag} must be true/false")
        if entry["keybind_in_use"] and not (entry["implemented"] and entry["applicable"]):
            raise ValueError(f"Active binding {entry['id']} has no supported implementation")
    return document["commands"]


COMMANDS = read_registry()


def available(entry, keyboard=False):
    return entry["implemented"] and entry["applicable"] and (entry["keybind_in_use"] or not keyboard)


def reason(entry):
    if not entry["applicable"]:
        return entry.get("reason") or "Not applicable to the single-SID target"
    if not entry["implemented"]:
        return entry.get("reason") or "Not implemented yet"
    return "Key binding disabled in the command table"


def context_matches(entry, page):
    return "global" in entry["contexts"] or page in entry["contexts"]


def match_event(event, page):
    if event.type != pg.KEYDOWN:
        return None
    modifiers = set()
    for label, bits in (("ctrl", pg.KMOD_CTRL), ("alt", pg.KMOD_ALT), ("shift", pg.KMOD_SHIFT)):
        if event.mod & bits:
            modifiers.add(label)
    # Caps Lock and Num Lock do not change command-chord identity.
    ordered = sorted(COMMANDS, key=lambda e: "global" in e["contexts"])
    for entry in ordered:
        if not context_matches(entry, page):
            continue
        for rule in entry.get("key_rules", []):
            if set(rule.get("modifiers", [])) != modifiers:
                continue
            if "scancode" in rule:
                matches = getattr(event, "scancode", 0) == rule["scancode"]
            else:
                matches = event.key == getattr(pg, rule["key"])
            if matches:
                return entry
    return None


def find_route(command, page):
    for entry in COMMANDS:
        if context_matches(entry, page) and entry.get("command") == command.name:
            if "value" not in entry or entry["value"] == command.value:
                return entry
    return None


def menu_entry(command, value=None):
    for entry in COMMANDS:
        if entry.get("command") == command and ("value" not in entry or entry["value"] == value):
            return entry
        if command == "pending" and entry.get("feature") == value:
            return entry
    return None


def help_entries(context=None):
    return [entry for entry in COMMANDS if entry["visible"] and entry["visible_in_help"]
            and (context is None or context_matches(entry, context))]
