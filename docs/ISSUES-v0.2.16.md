# SIDpulse Tracker v0.2.16 — issues, fixes and remaining limitations

This document records the issues fixed for the final **v0.2.16** release and
remaining known limitations. Internal checkpoint/patch names are deliberately
omitted from the public release documentation.

## File browser and filename editing

### Save As and export hid the directory browser

Load, F10 Save, Save As, SID export and PRG export now use the same visible
file browser. Filename and directory fields remain visible while choosing a
destination; Save As no longer opens a separate filename popup over the list.

### Filename editing was destructive or append-only

The browser now has a movable caret and selection for single-line filename and
directory editing. Left/Right, Home/End, Shift-selection, Backspace/Delete,
Ctrl+word movement/deletion, Ctrl+A and clipboard operations work in the field.
Clicking positions the caret. Save As starts with the caret before the extension
and does not select the entire filename, so a revision suffix can be edited
without replacing the rest of the name.

Folder navigation and refresh preserve the filename draft. Long names scroll
with the caret instead of forcing destructive re-entry.

### Save/export defaults and quick-save behavior were inconsistent

The latest successfully opened or saved native project supplies the next default
filename and directory. A new project clears that inherited name. Export uses the
current project basename with the appropriate export suffix but does not rename
the editable `.sidpulse` project.

F10 and menu Save open the browser. Ctrl+S/Ctrl+W remain quick-save shortcuts
outside the browser. Successful open/save updates the future default; cancelled
or failed operations do not.

### Cancelled/failed destination choices lost context

Overwrite confirmation defaults to Cancel. Cancelling the confirmation returns
to the same editable filename and directory. Invalid paths and write errors keep
the draft available instead of silently falling back to a previous location.
Existing atomic writers and `.bak` behavior remain in use.

### Text-entry routing could collide with tracker controls

While filename/directory fields have focus, text input is handled before tracker
note-entry dispatch. Physical piano-key mappings must not alter pattern data
while editing a path. Printable text input, including AltGr combinations, is not
misinterpreted as project shortcuts.

## Other fixes included in v0.2.16

### Effect-entry status

Implemented effects no longer report that sequencing is pending. Status feedback
uses the same capability knowledge as playback/export; unsupported commands can
still be stored without falsely claiming playback support.

### Pattern beat/bar shading

F12 includes project-local, display-only beat/bar shading controls. This supports
non-default layouts such as a 12-row beat / 48-row bar shuffle grid without
changing musical timing or the native song format.

### Oversized SID export diagnostics

SID export preflights its complete memory requirement and reports the player,
unique tick-record data, pointer sequence, total requirement and available
budget. Oversized projects are refused with the practical instruction:

> Shorten or simplify the project and try again.

The exporter does not silently delete musical material to force a project to fit.
The underlying compiled-player memory budget is unchanged.

### Direct octave-digit entry

When the cursor is on a note's octave digit, typing `0`..`7` changes only the
octave. Pitch class, instrument and effects are preserved. Unsupported octave
digits are rejected rather than being reinterpreted as piano-key input.

### Instrument activity indicators

The F4 instrument list shows activity dots for instruments actually triggered or
gated during playback/audition. Selection alone does not light an instrument.
Sample-bank indicator positions remain intentionally idle because PCM/digi
sample playback is not yet implemented.

### ADSR attack display

Attack `00` is drawn vertically in the schematic envelope display rather than
being forced to an artificial minimum horizontal width. This is a visualization
fix only: the SID's fastest hardware attack rate and audio behavior are unchanged.

### Song-end looping

F11 exposes **Loop song when the playlist ends**, synchronized with the same F12
setting. ON restarts from order 000; OFF stops at the end. F6 pattern looping
remains separate. A final-row timing bug that could use the old loop state was
also corrected.

## Release-documentation fixes

Before the final release, documentation was brought into line with the actual
v0.2.16 behavior and delivery model:

- stale v0.2.12 download/update instructions were replaced with v0.2.16 full-ZIP
  and checksum instructions;
- local incremental-update packages were separated from public GitHub release
  assets;
- Save/F10/quick-save and song-loop terminology was made consistent with the
  implemented UI;
- the obsolete “initial private handoff” wording was removed from dependency
  notes;
- release instructions now require the exact release commit to pass CI before
  tagging/publishing;
- no project-wide source license was invented or selected by this cleanup.

## Compatibility

- Application version: **0.2.16**
- Native `.sidpulse` song format: **6**
- Existing explicitly saved audio-buffer preferences are preserved.
- Runtime dependency pins are unchanged by these fixes.
- User songs and machine preferences are not rewritten by the release update.

## Remaining limitations

- PCM/digi sample playback is not implemented; sample activity indicators remain
  idle.
- WAV/MP3 export is not implemented.
- The compiled SID exporter still has a finite resident-memory budget; large
  editable projects can legitimately be too large to export.
- Filename caret movement operates on Python Unicode code points rather than
  grapheme clusters; full platform-native IME composition UI is not implemented.
- Windows drive/volume selection is handled through path entry rather than a
  dedicated drive picker.

## Validation

The validation procedure is maintained in [`VALIDATION.md`](VALIDATION.md).
Release-specific test counts and CI results belong in the release record/CI logs,
not as permanent numbers in this issue document.
