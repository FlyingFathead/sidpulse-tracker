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
                  Item("Pattern Edit Menu...", "submenu", "Pattern Edit Menu"),
                  Item("Sample Menu...", "submenu", "Sample Menu"),
                  Item("Instrument Menu...", "submenu", "Instrument Menu"),
                  Item("Orders / Pattern bank   F11", "page", "orders"),
                  Item("View Variables          F12", "page", "settings"),
                  Item("Message Editor    Shift+F9", "comments"),
                  Item("Settings Menu...", "submenu", "Settings Menu"),
                  Item("Help!                    F1", "page", "help"),
                  Item("About SIDpulse Tracker", "about"),
                  Item("Quit", "quit")],
    "Pattern Edit Menu": [Item("Cut selection         Alt+Z", "copy", True),
                          Item("Copy selection        Alt+C", "copy", False),
                          Item("Paste overwrite       Alt+O", "paste", "overwrite"),
                          Item("Paste insert          Alt+P", "paste", "insert"),
                          Item("Paste mix             Alt+M", "paste", "mix"),
                          Item("Paste Special  Ctrl+Shift+V", "paste_special"),
                          Item("Reset all automation", "reset_automation"),
                          Item("Record automation Ctrl+Shift+R", "pulse_record_arm"),
                          Item("Clipboard buttons: on / off", "pattern_clipboard_buttons")],
    "File Menu": [Item("New project", "new"),
                  Item("Clear all pattern data", "clear_patterns"),
                  Item("Clear all instruments", "clear_instruments"), Item("Load .sidpulse           F9", "open"),
                  Item("Save .sidpulse          F10", "save"), Item("Save as .sidpulse...  Shift+F10", "save_as"),
                  Item("Export SID / RSID... Ctrl+Shift+E", "export"),
                  Item("Export PRG...", "export_prg"),
                  Item("Export WAV / MP3...", "export_audio"),
                  Item("Import SID / remap...", "pending", "SID remapping", False)],
    "Playback Menu": [Item("Info Page", "page", "info"),
                      Item("Play song               F5", "play", "song"),
                      Item("Play pattern            F6", "play", "pattern"),
                      Item("Play from mark / row    F7", "play", "cursor"),
                      Item("Play from order   Shift+F6", "play", "order"),
                      Item("Pause / resume    Shift+F8", "pause"),
                      Item("Stop / silence          F8", "panic")],
    "Sample Menu": [Item("View Sample Bank        F3", "page", "samples"),
                    Item("Import PCM sample...", "import_sample"),
                    Item("Assign sample to instrument...", "assign_sample"),
                    Item("Squeeze sample...", "sample_squeeze")],
    "Instrument Menu": [Item("View SID Instruments    F4", "page", "instrument"),
                        Item("Record automation Ctrl+Shift+R", "pulse_record_arm"),
                        Item("Arps / wave / pitch tables...", "instrument_programs"),
                        Item("Vibrato / gate programs...", "instrument_programs")],
    "Settings Menu": [Item("Song / SID settings     F12", "page", "settings"),
                      Item("UI Settings...", "submenu", "UI Settings"),
                      Item("Keyboard mapping...", "keyboard_mapping"),
                      Item("MIDI configuration Shift+F1", "pending", "MIDI configuration", False),
                      Item("System configuration Ctrl+F1", "pending", "System configuration", False),
                      Item("Audio settings    Alt+F12", "audio_settings"),
                      Item("Autosave settings...", "autosave_settings"),
                      Item("F5 restart option...", "f5_restart_settings"),
                      Item("Reset audio counters", "audio_reset_stats"),
                      Item("Reset all settings to defaults...", "reset_settings")],
    "UI Settings": [Item("Colour themes     Ctrl+F12", "appearance_settings", 17),
                      Item("Center pattern row: on / off", "center"),
                      Item("Automation display: 2 (inline)", "automation_display_toggle"),
                      Item("Font settings    Shift+F12", "appearance_settings", 18),
                      Item("Bottom helper: on / off", "helper_toggle"),
                      Item("Pattern clipboard buttons: on / off", "pattern_clipboard_buttons"),
                      Item("Confirm before Cut: on / off", "confirm_cut_toggle"),
                      Item("Instrument/sample M/S: on / off", "instrument_monitor_buttons"),
                      Item("Control/filter column: show / hide", "control_panel_toggle"),
                      Item("Channel visualizers: on / off", "channel_visualizers_toggle"),
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
