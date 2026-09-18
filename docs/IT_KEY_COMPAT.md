# IT / Schism keyboard contract, v0.1.1

Primary references inspected: Schism Tracker commit
`84d2c46c1d3b5660edbc3eca259bf1219e59623e`, especially
[keyboard.c](https://github.com/schismtracker/schismtracker/blob/84d2c46c1d3b5660edbc3eca259bf1219e59623e/schism/keyboard.c),
[page_patedit.c](https://github.com/schismtracker/schismtracker/blob/84d2c46c1d3b5660edbc3eca259bf1219e59623e/schism/page_patedit.c),
[pattern help](https://github.com/schismtracker/schismtracker/blob/84d2c46c1d3b5660edbc3eca259bf1219e59623e/helptext/pattern-editor),
[global keys](https://github.com/schismtracker/schismtracker/blob/84d2c46c1d3b5660edbc3eca259bf1219e59623e/helptext/global-keys),
and [instrument help](https://github.com/schismtracker/schismtracker/blob/84d2c46c1d3b5660edbc3eca259bf1219e59623e/helptext/instrument-list).
Historical reference: [Impulse Tracker source](https://github.com/jthlim/impulse-tracker).

## Implemented core

| Keys | SIDpulse behavior |
|---|---|
| F1, F2, F3, F4, F11, F12 | Help, pattern, samples, instruments, orders + pattern bank, settings |
| F9 / Ctrl+L | Load .sidpulse |
| F10 | Save .sidpulse through the shared browser |
| Ctrl+S / Ctrl+W | Quick-save current .sidpulse (browse when unnamed) |
| Escape | Close overlay / return, or main menu |
| Z S X D C V G B H N J M | Lower physical piano row |
| Q 2 W 3 E R 5 T 6 Y 7 U I 9 O 0 P | Upper physical piano row |
| Physical 1 | Note cut `^^^` |
| Physical grave / non-US hash | Note off `===` |
| Physical period | Clear current field; period is not a piano note |
| Space / Enter | Reuse field / pick defaults |
| Comma | Toggle supported current edit-copy mask |
| Caps Lock + note | Audition without writing |
| 4 / 8 | Audition cell / row while held |
| Keypad / and *; Alt+Home/End | Lower / raise octave |
| Ctrl+Up/Down; < / > | Previous / next instrument |
| Arrows | Navigate fields/rows; nine cursor positions per voice |
| Tab / Shift+Tab | Next voice note column / current or preceding note column |
| Home / End | Field edge, then voice edge, then pattern edge |
| PgUp/Down; Ctrl+PgUp/Down | 16 rows / pattern start and end |
| Ctrl+Home/End | One row backward / forward |
| +/-; Shift+keypad +/-; Ctrl +/- | One pattern / four patterns / order's pattern |
| Alt+0..9 | Row skip, including zero for stationary note entry |
| Insert/Delete | Insert/delete current voice's row |
| Alt+Insert/Delete | Insert/delete all three voices' row |
| Alt+B/E; Shift+arrows | Block bounds; interactive rectangular voice/row selection |
| Alt+L | Whole voice; repeat to select whole pattern |
| Alt+C/Z | Copy / cut block |
| Alt+P/O/M | Insert paste / overwrite paste / mix into empty cells |
| Alt+U | Unmark and clear clipboard |
| Alt+Q/A; plus Shift | Transpose semitone / octave |
| Alt+S | Set block instrument |
| Ctrl+Insert/Delete | Roll selected block down/up |
| Alt+Enter / Alt+Backspace | Store / restore pattern snapshot |
| Ctrl+Backspace | Undo |
| Ctrl+C / Ctrl+H | Center cursor / current-row highlight |
| Ctrl+F2 | Pattern length 1–256: linked slider and clickable three-digit field; OK / Cancel |
| F5 / Ctrl+F5 | Start song / always restart. Repeated F5 only shows Info by default; configurable in F12 |
| F6 / Shift+F6 / Ctrl+F6 | Pattern loop / song from order / pattern from row |
| F7 / Ctrl+F7 | Play mark or current row / set-clear playback mark |
| F8 / Shift+F8 | Stop / pause-resume |
| Scroll Lock / Ctrl+F | Toggle playback tracing |

Instrument numbers use decimal 01..99. Effect parameters use hex 00..FF;
effect letters are A..Z. Pattern notes support C-0..B-7 in this prototype.

## Deliberate SID adaptations and additions

- Nine cursor positions preserve the displayed note/octave/instrument/expression/effect layout. The note-name position accepts the entire physical piano range. At the octave digit, typed 0..7 changes only an existing note's octave, then follows Skip; 8/9 is rejected. Letter piano keys still enter notes there. Caps Lock keeps piano audition non-destructive. Blank, release and cut cells are not converted into notes by an octave digit.
  EX is visible and navigable but reserved. It has no pretend per-voice PCM volume.
- F4 defaults to an instrument bank and replaces sample-tracker synthesis controls
  with actual SID fields. Tab switches bank/properties. It does not implement all
  historical instrument subpages yet.
- Shift+F10 is native Save as for now (Schism uses it for audio export). Ctrl+S
  is a quick-save alias; Ctrl+Shift+S is Save as. Ctrl+N creates a project.
- Ctrl+Shift+Backspace adds redo. Ctrl+Alt +/- and Ctrl+Alt+0 add UI zoom without
  stealing Schism Ctrl +/- pattern/order navigation. Ctrl+mouse wheel also zooms.
- Ctrl+Enter toggles fullscreen; Alt+Enter remains the pattern snapshot command.
- F11 supports order insert/delete, N new, Shift+N duplicate, and Enter to edit
  a hex pattern number. Direct digit-in-list entry and order skip/end markers
  are not implemented in this build.

## Not yet claimed compatible

This is a substantial tested subset, not full Schism parity. Sequencing and
tracing now work. No multichannel
edit mode, Shift-chord recording, note-fade emulation, template modes, per-field
mix-paste, system clipboard interop, pattern view schemes, advanced volume
operations, complete edit-mask semantics, or historical MIDI keys.
Ctrl+Z/Ctrl+X are not reassigned to undo/cut; Schism uses them for MIDI behavior.
The key-event logger (`--log-keys`) and tests support focused parity fixes after
the first hands-on review. No arbitrary panning/volume effects are translated
into fake SID hardware features.

The complete inventory and visibility flags are in [COMMANDS.md](COMMANDS.md).
`sidpulse/assets/commands.json` controls enabled bindings, applicability, help
visibility, and menu visibility. F1 -> 8 Shortcuts renders that data, including
grey inactive entries. For example Info-page Alt+S stereo toggle is inapplicable;
Pattern-page Alt+S set-instrument remains enabled. Context is part of identity.

## Voice monitoring additions in this checkpoint

Alt+F1, Alt+F2 and Alt+F3 preserve Schism's direct channel toggles for the
three available voices. Alt+F9 toggles the current voice; Alt+F10 solos it.
Repeating Solo restores the previous mute set. The Info page also accepts
Q for mute and S for solo. Pattern-page M and S retain their piano-key roles.
Clickable [M]/[S] headers operate the same monitoring state.

The initial pyresidfp monitor disconnects selected voice waveforms while
retaining the shadow register values and oscillator/gate activity. The native
filter/output can retain a transient. This is a preview control, not song data.

## v0.2.0 additions

Ctrl+Shift+F2 toggles CTRL CH / FILTER focus. Ctrl+F2 still edits pattern length.
Ctrl+Shift+E exports PSID with a native-save offer. F4 property focus uses
PgUp/PgDn for General/Motion; its instrument list retains note audition. Song
notes use Shift+F9, with Shift+Enter for a newline. Shift+F10 remains Save As.
These additions do not remap the established transport or block-edit shortcuts.


## v0.2.1

F4 has a scrollable 01..99 bank including empty slots. Enter opens a preset/manual
chooser; Insert creates a blank instrument; Delete confirms (Cancel default).
Tab cycles bank/buttons/fields. Numeric fields have sliders plus typed entry.
Ctrl+F12 selects colour themes; Shift+F12 opens font settings. Ctrl+Q offers real
Save/Discard/Cancel buttons. These routes retain the registry capability flags.

## v0.2.5

Instrument parameter typing now requires a mouse click on the yellow value field.
Highlighted fields, Enter, digits and A–F never start parameter entry. All note
scancodes remain available for audition. Enter still activates buttons and the
instrument chooser. Ctrl+N always confirms New project, and every quit request
starts on Cancel with Discard & Quit clearly labelled.

## Added in v0.2.15

F11 **L** toggles the bottom song-end loop button in either panel. Holding the key
does not repeatedly toggle; Ctrl+L still opens a project. This is a SIDpulse
addition, not a claim of an identical historical IT shortcut. F12 is the same
saved flag and F6 still loops only the current pattern.

Instrument-list dots indicate playback/audition rather than cursor selection.
ADSR's zero attack is a vertical schematic fastest-rate symbol, not a zero-ms SID
setting. No original note-entry or octave-edit keys are reassigned by these dots.

## Added in v0.2.16

F9, F10, Save As and SID/PRG export destinations share the same browser. F10 now
opens it even for a named project; Ctrl+S/W quick-saves outside it. Inside Save,
Ctrl+S/W submits the visible draft. Filename starts from the current saved/opened
name with an unselected caret before the extension, ready for a revision edit.

Tab/Shift+Tab switches list/name/directory/action/cancel. In text fields,
Left/Right/Home/End and Shift select/move the caret instead of dialog buttons;
Backspace/Delete edit text; Ctrl+A/C/X/V operate on selections. Ctrl+L is directory
editing inside the browser and remains Load elsewhere. Alt+Up goes to the parent.
No piano key, transport, octave or block-edit bindings are changed outside this
file-browser context. See [FILE_BROWSER.md](FILE_BROWSER.md).

## Audio settings addition (v0.2.22)

Alt+F12 opens audio buffer and underrun-notification settings globally. It was
unassigned in v0.2.21; Ctrl+F12 and Shift+F12 retain their existing actions.
