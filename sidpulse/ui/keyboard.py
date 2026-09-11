"""Physical SDL scancodes -> semantic commands. QWERTY note positions
remain consistent on Finnish and other layouts; text fields use Unicode.
"""
from dataclasses import dataclass
import pygame as pg

# USB/SDL scancodes, two staggered piano rows. C-4 at physical Z by default.
NOTE_SCANCODES = {
    29: 0, 22: 1, 27: 2, 7: 3, 6: 4, 25: 5, 10: 6, 5: 7,
    11: 8, 17: 9, 13: 10, 16: 11,
    20: 12, 31: 13, 26: 14, 32: 15, 8: 16, 21: 17, 34: 18,
    23: 19, 35: 20, 28: 21, 36: 22, 24: 23, 12: 24,
    38: 25, 18: 26, 39: 27, 19: 28,
}


@dataclass(frozen=True)
class Command:
    name: str
    value: object = None


def _dispatch_unchecked(event, page="pattern", column=0):
    if event.type not in (pg.KEYDOWN, pg.KEYUP):
        return None
    key, mod = event.key, event.mod
    scan = getattr(event, "scancode", 0)
    ctrl, alt, shift = bool(mod & pg.KMOD_CTRL), bool(mod & pg.KMOD_ALT), bool(mod & pg.KMOD_SHIFT)
    if event.type == pg.KEYUP:
        return Command("release", scan)
    if alt and not ctrl and not shift:
        if key in (pg.K_F1, pg.K_F2, pg.K_F3):
            return Command("mute", (pg.K_F1, pg.K_F2, pg.K_F3).index(key))
        if key in (pg.K_F9, pg.K_F10):
            return Command("mute" if key == pg.K_F9 else "solo")
    if page == "info" and not (alt or ctrl or shift) and key in (pg.K_q, pg.K_s):
        return Command("mute" if key == pg.K_q else "solo")
    if ctrl and shift and key==pg.K_e:
        return Command("export")
    if ctrl and shift and key==pg.K_F2:
        return Command("control_focus")
    if ctrl and key == pg.K_RETURN:
        return Command("fullscreen")
    if ctrl and alt and key in (pg.K_EQUALS, pg.K_PLUS, pg.K_KP_PLUS, pg.K_MINUS, pg.K_KP_MINUS, pg.K_0):
        return Command("zoom", 0 if key == pg.K_0 else (-1 if key in (pg.K_MINUS, pg.K_KP_MINUS) else 1))
    if ctrl and key in (pg.K_s, pg.K_w):
        return Command("save_as" if shift else "save")
    if ctrl and key == pg.K_l:
        return Command("open")
    if ctrl and key == pg.K_n:
        return Command("new")
    if ctrl and not shift and key == pg.K_q:
        return Command("quit")
    if ctrl and key == pg.K_BACKSPACE:
        return Command("redo" if shift else "undo")
    if key == pg.K_ESCAPE:
        return Command("escape")
    if key == pg.K_F12 and shift:
        return Command("appearance_settings",18)
    if key == pg.K_F12 and ctrl:
        return Command("appearance_settings",17)
    if key == pg.K_F1 and shift:
        return Command("pending", "MIDI configuration")
    if key == pg.K_F1 and ctrl:
        return Command("pending", "System configuration")
    if key == pg.K_F9 and shift:
        return Command("comments")
    if key in (pg.K_F1, pg.K_F2, pg.K_F3, pg.K_F4, pg.K_F11, pg.K_F12) and not alt and not ctrl:
        return Command("page", {pg.K_F1: "help", pg.K_F2: "pattern", pg.K_F3: "samples", pg.K_F4: "instrument", pg.K_F11: "orders", pg.K_F12: "settings"}[key])
    if key == pg.K_F9 and not alt:
        return Command("open")
    if key == pg.K_F10 and not alt:
        return Command("save_as" if shift else "save")
    if key == pg.K_F8 and not alt and not ctrl:
        return Command("pause" if shift else "panic")
    if key == pg.K_F5 and not alt and not shift:
        return Command("play", "restart" if ctrl else "song")
    if key == pg.K_F6 and not alt:
        return Command("play", "order" if shift else "pattern_cursor" if ctrl else "pattern")
    if key == pg.K_F7 and not alt and not shift:
        return Command("playback_mark") if ctrl else Command("play", "cursor")
    if page == "pattern" and ((key == pg.K_SCROLLLOCK and not (ctrl or alt or shift)) or (key == pg.K_f and ctrl and not (alt or shift))):
        return Command("follow")
    if key == pg.K_KP_DIVIDE or (alt and key == pg.K_HOME):
        return Command("octave", -1)
    if key == pg.K_KP_MULTIPLY or (alt and key == pg.K_END):
        return Command("octave", 1)
    if ctrl and key in (pg.K_UP, pg.K_DOWN):
        return Command("instrument", -1 if key == pg.K_UP else 1)
    if page == "pattern":
        if ctrl and not alt and key in (pg.K_KP_PLUS, pg.K_KP_MINUS, pg.K_MINUS, pg.K_PLUS, pg.K_EQUALS):
            return Command("order_pattern", -1 if key in (pg.K_KP_MINUS, pg.K_MINUS) else 1)
        if alt:
            if pg.K_0 <= key <= pg.K_9:
                return Command("skip", key - pg.K_0)
            mapping = {pg.K_b: ("mark", "start"), pg.K_e: ("mark", "end"), pg.K_l: ("mark", "all"),
                       pg.K_u: ("mark", "clear"), pg.K_c: ("copy", False), pg.K_z: ("copy", True),
                       pg.K_p: ("paste", "insert"), pg.K_o: ("paste", "overwrite"), pg.K_m: ("paste", "mix"),
                       pg.K_q: ("transpose", 12 if shift else 1), pg.K_a: ("transpose", -12 if shift else -1),
                       pg.K_s: ("block_instrument", None), pg.K_RETURN: ("store_pattern", None),
                       pg.K_BACKSPACE: ("restore_pattern", None), pg.K_LEFT: ("channel", -1), pg.K_RIGHT: ("channel", 1),
                       pg.K_INSERT: ("insert_row", True), pg.K_DELETE: ("delete_row", True)}
            return Command(*mapping[key]) if key in mapping else None
        if ctrl:
            mapping = {pg.K_c: ("center", None), pg.K_h: ("highlight", None), pg.K_F2: ("pattern_length", None),
                       pg.K_PAGEUP: ("edge", 0), pg.K_PAGEDOWN: ("edge", -1),
                       pg.K_HOME: ("move", (-1, 0, shift)), pg.K_END: ("move", (1, 0, shift)),
                       pg.K_LEFT: ("channel", -1), pg.K_RIGHT: ("channel", 1),
                       pg.K_INSERT: ("roll", 1), pg.K_DELETE: ("roll", -1)}
            return Command(*mapping[key]) if key in mapping else None
        if key in (pg.K_KP_PLUS, pg.K_KP_MINUS, pg.K_MINUS, pg.K_PLUS) or (key == pg.K_EQUALS and shift):
            return Command("pattern", (4 if shift and key != pg.K_EQUALS else 1) * (-1 if key in (pg.K_KP_MINUS, pg.K_MINUS) else 1))
        if key in (pg.K_UP, pg.K_DOWN, pg.K_LEFT, pg.K_RIGHT):
            dr, dc = {pg.K_UP: (-1, 0), pg.K_DOWN: (1, 0), pg.K_LEFT: (0, -1), pg.K_RIGHT: (0, 1)}[key]
            if shift:
                dc *= 9
            return Command("step_move", (dr, dc, shift))
        if key in (pg.K_PAGEUP, pg.K_PAGEDOWN):
            return Command("move", (-16 if key == pg.K_PAGEUP else 16, 0, shift))
        if key == pg.K_TAB:
            return Command("channel", -1 if shift else 1)
        if key in (pg.K_HOME, pg.K_END):
            return Command("home_end", key == pg.K_END)
        if key in (pg.K_INSERT, pg.K_DELETE):
            return Command("delete_row" if key == pg.K_DELETE else "insert_row", False)
        if key == pg.K_BACKSPACE:
            return Command("step_move", (-1, 0, False))
        if key == pg.K_SPACE:
            return Command("repeat")
        if key == pg.K_RETURN:
            return Command("pick")
        if getattr(event, "unicode", "") in ("<", ">"):
            return Command("instrument", -1 if event.unicode == "<" else 1)
        if scan == 54 and not shift:
            return Command("mask")
        if scan == 55 and not shift:
            return Command("clear")
        # Both parts of NOTE are a piano input target. Caps Lock auditions
        # from any voice field without turning note keys into parameter digits.
        if not shift and scan in NOTE_SCANCODES and (column in (0, 1) or mod & pg.KMOD_CAPS):
            return Command('piano', (scan, NOTE_SCANCODES[scan], bool(mod & pg.KMOD_CAPS)))
        if column != 0:
            if key == pg.K_PERIOD:
                return Command("clear")
            return Command("digit", getattr(event, "unicode", ""))
        if shift:
            return None  # SID gate-release has no distinct PCM note-fade state.
        if scan == 30:  # physical 1
            return Command("note", -2)
        if scan in (53, 50):  # grave/non-US hash, including Finnish section sign
            return Command("note", -1)
        if scan == 33:
            return Command("audition_cell")
        if scan == 37:
            return Command("audition_row")
    elif alt or ctrl:
        return None
    if page in ("pattern", "instrument") and not shift and scan in NOTE_SCANCODES:
        return Command("piano", (scan, NOTE_SCANCODES[scan], bool(mod & pg.KMOD_CAPS) or page == "instrument"))
    if page != "pattern":
        return Command("page_key", event)
    return None


def dispatch(event, page="pattern", column=0):
    from sidpulse.ui.registry import available, find_route, match_event, reason
    entry = match_event(event, page)
    if entry and not available(entry, keyboard=True):
        return Command("pending", f"{entry['description']}: {reason(entry)}")
    command = _dispatch_unchecked(event, page, column)
    if command and event.type == pg.KEYDOWN and command.name not in ("pending", "release"):
        capability = entry or find_route(command, page)
        if capability and not available(capability, keyboard=True):
            return Command("pending", f"{capability['description']}: {reason(capability)}")
    return command
