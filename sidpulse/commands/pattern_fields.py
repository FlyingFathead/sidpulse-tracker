"""One field map for cursor movement, selection, clipboard and drawing."""
from sidpulse.song.model import ENVELOPE_FIELDS

FIELDS = ("note", "note", "instrument", "instrument", "expression", "expression", "effect", "parameter", "parameter", *ENVELOPE_FIELDS, "pulse_width", "pulse_width", "pulse_width")
COLUMN_OFFSETS = (0, 2, 5, 6, 8, 9, 11, 12, 13, 15, 17, 19, 21, 23, 24, 25)
CURSOR_HINTS = (
    "Insert note | Piano keys; Caps Lock: audition",
    "Select octave | 0..7 changes this note",
    "Select instrument | Tens digit, decimal 01..99",
    "Select instrument | Units digit, decimal 01..99",
    "Expression | EX is reserved; no independent PCM voice volume",
    "Expression | EX is reserved; no independent PCM voice volume",
    "Insert effect | A..Z; F1: effect reference",
    "Effect parameter | High hex digit, 00..FF",
    "Effect parameter | Low hex digit, 00..FF",
    "Attack | Hex 0..F; R: instrument attack; .: keep running value",
    "Decay | Hex 0..F; R: instrument decay; .: keep running value",
    "Sustain | Hex level 0..F; R: instrument sustain; .: keep running value",
    "Release | Hex 0..F; R: instrument release; .: keep running value",
    "Pulse width | High hex digit; RAL: reset all automation; R then Enter: reset PW",
    "Pulse width | Middle hex digit; RAL: reset all automation; R then Enter: reset PW",
    "Pulse width | Low hex digit; RAL: reset all automation; R then Enter: reset PW",

)

AUTOMATION_FIELDS = frozenset((*ENVELOPE_FIELDS, "pulse_width"))
FIELD_GROUPS = (("NOTE", (0, 1), ("note",)),
                ("IN", (2, 3), ("instrument",)),
                ("EX", (4, 5), ()),
                ("FX", (6, 7, 8), ("effect", "parameter")),
                *((label, (index,), (name,)) for label, index, name in zip("ADSR", range(9, 13), ENVELOPE_FIELDS)),
                ("PW", (13, 14, 15), ("pulse_width",)))

def group_for_column(column):
    return next(group for group in FIELD_GROUPS if column in group[1])

def group_span(columns):
    start, end = COLUMN_OFFSETS[columns[0]], COLUMN_OFFSETS[columns[-1]] + 1
    return start, end - start
