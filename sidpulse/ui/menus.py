"""Visible capability map; unimplemented entries are disabled, never fake actions."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Item:
    label: str
    command: str
    value: object = None
    enabled: bool = True


MENUS = {
    "Main Menu": [Item("File Menu...", "submenu", "File Menu"),
                  Item("Playback Menu...", "submenu", "Playback Menu"),
                  Item("View Patterns           F2", "page", "pattern"),
                  Item("Sample Menu...", "submenu", "Sample Menu"),
                  Item("Instrument Menu...", "submenu", "Instrument Menu"),
                  Item("Orders / Pattern bank   F11", "page", "orders"),
                  Item("View Variables          F12", "page", "settings"),
                  Item("Message Editor    Shift+F9", "comments"),
                  Item("Settings Menu...", "submenu", "Settings Menu"),
                  Item("Help!                    F1", "page", "help"),
                  Item("About SIDpulse Tracker", "about"),
                  Item("Quit", "quit")],
    "File Menu": [Item("New project", "new"),
                  Item("Clear all pattern data", "clear_patterns"),
                  Item("Clear all instruments", "clear_instruments"), Item("Load .sidpulse           F9", "open"),
                  Item("Save .sidpulse          F10", "save"), Item("Save as...       Shift+F10", "save_as"),
                  Item("Export PSID... Ctrl+Shift+E", "export"),
                  Item("Export PRG...", "export_prg"),
                  Item("Import SID / remap...", "pending", "SID remapping", False)],
    "Playback Menu": [Item("Info Page", "page", "info"),
                      Item("Play song               F5", "play", "song"),
                      Item("Play pattern            F6", "play", "pattern"),
                      Item("Play from mark / row    F7", "play", "cursor"),
                      Item("Play from order   Shift+F6", "play", "order"),
                      Item("Pause / resume    Shift+F8", "pause"),
                      Item("Stop / silence          F8", "panic")],
    "Sample Menu": [Item("View Sample Bank        F3", "page", "samples"),
                    Item("Import PCM sample...", "pending", "PCM sample import", False),
                    Item("Convert to digi...", "pending", "Digi conversion", False)],
    "Instrument Menu": [Item("View SID Instruments    F4", "page", "instrument"),
                        Item("Arps / wave / pitch tables...", "instrument_programs"),
                        Item("Vibrato / gate programs...", "instrument_programs")],
    "Settings Menu": [Item("Song / SID settings     F12", "page", "settings"),
                      Item("MIDI configuration Shift+F1", "pending", "MIDI configuration", False),
                      Item("System configuration Ctrl+F1", "pending", "System configuration", False),
                      Item("Colour themes     Ctrl+F12", "appearance_settings", 17),
                      Item("Font settings    Shift+F12", "appearance_settings", 18),
                      Item("Audio settings    Alt+F12", "audio_settings"),
                      Item("Autosave settings...", "autosave_settings"),
                      Item("F5 restart option...", "f5_restart_settings"),
                      Item("Reset audio counters", "audio_reset_stats"),
                      Item("Bottom helper: on / off", "helper_toggle"),
                      Item("Zoom in       Ctrl+Alt +", "zoom", 1),
                      Item("Zoom out      Ctrl+Alt -", "zoom", -1),
                      Item("Zoom reset    Ctrl+Alt+0", "zoom", 0),
                      Item("Fullscreen  Ctrl+Alt+Enter", "fullscreen")],
}


def menu_items(title):
    from sidpulse.ui.registry import menu_entry, available
    from dataclasses import replace
    result = []
    for item in MENUS[title]:
        entry = menu_entry(item.command, item.value)
        if entry:
            if not (entry["visible"] and entry["visible_in_menu"]):
                continue
            item = replace(item, enabled=available(entry))
        result.append(item)
    return result
