# F2 selection and clipboard

Modern keyboard mode is the default from v0.2.26: **Ctrl+Insert** copies and
**Shift+Insert** pastes. The Alt shortcuts below work in both Modern and Classic.
Choose a profile under Settings Menu > Keyboard mapping. See
[keyboard mapping](KEYBOARD_MAPPING.md) for octave controls and profile details.

Select just the fields you want to change. A PW selection can be pasted onto
another voice without replacing its notes, instrument numbers, effects or ADSR.
The internal clipboard keeps the selected fields even after clicking a new
destination or moving to another pattern.

| Action | Mouse | Keyboard |
|---|---|---|
| Select fields and rows | Drag from first to last field/row | Shift+arrows |
| Extend selection | Shift+click | Shift+arrows |
| Select one field for all rows | Click NOTE, IN, FX, A, D, S, R or PW header | Shift+arrows across the desired rows |
| Copy | Copy button / Pattern Edit Menu | Alt+C |
| Cut | Pattern Edit Menu | Alt+Z |
| Paste overwrite | Paste button / Pattern Edit Menu | Alt+O |
| Paste insert | Pattern Edit Menu | Alt+P |
| Paste mix | Pattern Edit Menu | Alt+M |
| Paste Special | Paste Special button / Pattern Edit Menu | Ctrl+Shift+V |
| Roll selected fields down/up | Keyboard | Modern: Ctrl+Shift+Insert/Delete; Classic: Ctrl+Insert/Delete |
| Whole current voice / whole pattern | Pattern selection using keyboard | Alt+L once / twice |
| Mark whole-voice block start/end | Pattern selection using keyboard | Alt+B / Alt+E |
| Clear block and clipboard | Pattern selection using keyboard | Alt+U |
| Undo / redo | Existing editing controls | Ctrl+Backspace / Ctrl+Shift+Backspace |

For example, drag vertically down channel 1's PW values, press Alt+C, click the
starting row in channel 2 and press Alt+O. Only channel 2's PW entries change.
Alternatively click PW in the header to copy its full pattern-length lane.
Dragging at the top/bottom edge scrolls through longer patterns; hidden voices
can be reached at the left/right grid edges. Selecting while playback follows
the cursor turns following off; playback continues.

The atomic units are NOTE (including octave), IN, FX (command and parameter),
each ADSR value, and the complete three-digit PW. Selecting one PW digit copies
the complete value. EX is reserved and carries no editable data. Selections
crossing voices include fields between their endpoints; middle voices include
all supported fields. Alt+B/E and Alt+L retain whole-cell behavior, including
unfamiliar future-format fields.

Ordinary Paste uses exactly the copied fields, at the current row and voice.
The cursor's digit position does not remap fields: PW always goes to PW. Copied
blank entries clear the corresponding destination entries during overwrite.
Zero and instrument-reset commands are real values and are copied as such.

**R** in A/D/S/R restores that parameter's instrument default. In PW, type
**RAL** to reset all five at the current row/channel, or **R then Enter** for PW
only. Unfinished R/RA input is temporary and Escape cancels it. **Reset all
automation** in the toolbar/menu writes all five resets to the selected
rows/channels (or current cell with no selection), while preserving notes,
instrument numbers and FX. It has one-step undo. See [automation](AUTOMATION.md).
Paste clips at the final pattern row or third voice and creates one undo step.

Paste insert shifts only the copied fields down within the fixed pattern length;
values moved past the bottom are dropped. Other fields keep their positions.
Paste mix writes only to empty destination fields; NOTE/IN/FX/automation are
checked independently for field selections. FX command and parameter are checked
together. Legacy whole-cell mix retains its whole-cell emptiness check. Roll,
transpose and block instrument commands also respect the selection: transposing
a PW-only block cannot change the notes.

## Paste Special

| Choice | Fields affected |
|---|---|
| Notes | NOTE only, including octave and note-off |
| Automation | A D S R PW |
| Both | NOTE plus A D S R PW |

Paste Special filters the fields actually copied. It cannot restore fields that
were excluded from the source selection. These three choices leave destination
IN and FX intact. To include IN/FX, select them and use ordinary Paste.

Copy / Paste / Paste Special buttons are on by default. Toggle **Pattern clipboard
buttons** in Settings or Pattern Edit Menu to hide them; keyboard/menu actions
continue working. Ctrl+C retains its established center-cursor command. This
clipboard is internal to SIDpulse Tracker, not the operating system text clipboard.

Buttons show a pressed state and activate on release inside. Drag away before
releasing to cancel. Successful copy/paste and empty clipboard notices appear
briefly above F8: SILENCE; the same notices accompany keyboard actions.

## Cut and confirmation (v0.2.27)

The button row is Cut / Copy / Paste / Paste Special / Reset all automation.
Cut (Alt+Z) honors the same field selection as Copy and keeps the removed values
in the internal pattern clipboard. Ctrl+Backspace restores the cut as one undo
step. The confirmation starts on Cancel; the unchecked Don't show this again
option is saved only when Cut is confirmed. Re-enable it under Settings Menu >
UI Settings > Confirm before Cut. Reset all automation always asks first.

Clipboard visibility and other display controls are now in UI Settings.
