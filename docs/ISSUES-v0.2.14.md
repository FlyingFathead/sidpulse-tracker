# SIDpulse Tracker v0.2.14-cp001: octave input issue and fixes

## Reported behavior

In the F2 pattern editor, the user places the cursor on the `5` in `D#5`.
Typing `4`, `3`, or another valid octave digit should alter that digit only:
`D#5 -> D#4 -> D#3`. Pitch class, instrument and effects must not be replaced.

## Source-confirmed cause

The supplied v0.2.12 code and v0.2.13-cp001 both already have an octave setter
in `Editor.enter_digit()` for column 1. The failure is before that setter:
`sidpulse/ui/keyboard.py` routes physical piano scancodes from both note cursor
positions before numeric-field dispatch. Number-row `0`, `2`, `3`, `5`, `6`,
`7`, and `9` therefore become piano commands instead of octave-entry commands.
The valid digits `1` and `4` already reach the setter, making the defect appear
inconsistent. Existing editor tests called enter_digit directly, so they did
not expose this routing failure.

## Implemented fix

The keyboard dispatcher gives a single typed ASCII digit priority when the
cursor is at the octave position, before normal piano-key decoding. The editor
accepts octaves 0..7, preserving the note modulo 12 and all other cell fields.
It does not apply the entry instrument/effect mask or change the global entry
octave. It updates repeat-last-note state and advances by the existing Skip.
The edit is a single undoable operation; an unchanged digit creates no spurious
history entry. The active block selection is not transposed implicitly.

- `8`/`9`: report the existing range 0..7; no write and no cursor advance.
- Blank/release/cut cells: ask for a pitched note; do not fabricate a pitch.
- Note-name slot: full physical piano mapping, including its number keys,
  note cut, and cell/row auditions, remains unchanged.
- Octave slot: letter piano keys still enter notes as before.
- Caps Lock: mapped keys still audition; numeric keys cannot edit the octave.
- Alt+digits: keep the row-Skip shortcuts.
- Keypad: use the digit actually delivered by the input event (Num Lock on).
  A keypad event without numeric text is not treated as an octave change.
- Instrument numbers and hexadecimal effect parameters: unchanged.

The contextual helper, F1 help and keyboard documentation now describe the
number-slot distinction instead of incorrectly promising the full number-row
piano mapping in both note positions.

## Export wording retained and made more useful

Oversized SID exports begin with:

```text
SID export aborted: project exceeds the memory budget.
Shorten or simplify the project and try again.
```

The actual error also includes required, allowed and excess bytes, the existing
component breakdown, and confirmation that the editable `.sidpulse` is unchanged.
The unimplemented "future compact player" suggestion is removed. No exporter
compression, extra memory allocation, silent note removal or musical editing
is performed by this patch.

## Tests and limits

Executed in Linux / Python 3.13.5:

- 177 core tests passed; three pygame-dependent checks/modules skipped.
- 70 keyboard routing tests passed separately using a minimal event/constants
  adapter with the actual production dispatcher and command registry. This
  checks routing precedence, not real SDL keyboard delivery or drawing.
- All octave digits 0..7 and all 12 pitch classes, cell-field preservation,
  repeat-last-note, skip/wrap, no-op history, undo/redo, range errors and native
  save/load were checked.
- The existing four PAL/NTSC example SID hashes remain unchanged.
- Real-pygame keyboard tests and a mouse-click-to-octave-edit GUI regression are
  included for execution in a provisioned development environment.

pygame-ce, pyresidfp and py65 could not be installed here because package
network access failed. Consequently there is no claim of a Windows GUI,
real-SDL input, or native-audio test. See docs/VALIDATION.md for commands.

The built release also passed eight package scenarios: LF/CRLF copies of
both supported baselines, safe refusal of local conflicts, archive corruption
and an unsupported version, plus direct unzip/idempotency. Four existing
Broken Machine project files (v20/v21, Shuffle/Vocal_Edit) passed a one-note
octave edit, native save/load and undo; their uploaded originals were unchanged.

## Manual acceptance check

1. Open a disposable project copy; place `D#5 03` on a row with an effect.
2. Click its octave digit. With Caps Lock off, press `4`, then undo. Repeat
   with `3`, `5`, `0`, `2`, `6` and `7`, returning to the row as needed.
3. Only the octave changes, the instrument stays 03, and the effect is retained.
   Row movement follows Skip. Set Skip 0 to stay on the same row.
4. Press `8` or `9`: no change. Try a blank/cut/release row: no note appears.
5. Move to the note-name slot: the original piano keyboard still works.
6. With Caps Lock on, mapped piano keys audition without modifying the song.
7. Save/reopen and check undo/redo; test a Num Lock keypad digit if available.

## Follow-up proposals, not implemented

The remaining manual acceptance check is real keyboard testing on Windows 11
and Linux, including Finnish-layout digit keys and Num Lock behavior. Extending
the model above octave 7 would be a separate format/playback/export decision;
this input repair must not quietly produce currently invalid note values.

## Packaging

Cumulative v0.2.14-cp001, accepting the exact supplied v0.2.12 and v0.2.13-cp001
source snapshots. ZIP paths begin `sidpulse-tracker/`, for extraction from the
repository's parent directory. The standard-library apply script verifies the
archive and baseline contents, preserves CRLF compatibility, backs up changes,
refuses conflicts and unsafe paths, and is idempotent. It performs no Git or
network operations. Direct unzip is available but has no conflict/backup checks.
The original musical projects, audio-buffer preference and song format are not
changed or packaged in this update.
