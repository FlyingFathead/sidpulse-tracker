# SIDpulse Tracker v0.2.26 validation

## Results

Full regression suite: **1209 passed**, no failures or skips, 180.79 seconds.
The log is in `validation/v0.2.26/full-tests.txt`.
Both headless startup smoke commands passed: `--example` and
`--play-welcome-song`. Focused native-audio, recording, GUI and reset checks also
passed; logs and inspected screen captures are in `validation/v0.2.26/`.

Environment: Python 3.12.14, pygame-ce 2.5.7, pyresidfp 0.17.0, Linux x86_64 with
SDL dummy video/audio. Native SID emulation and the spawned audio worker were
exercised. Physical output devices, native Windows and C64 hardware were not
available for this validation.

## Input and visible feedback

Tests exercise mouse-down bevel changes, exactly one activation on release,
fast-click feedback, release-outside cancellation, focus loss, page switches,
resize and Escape. Clipboard success and failure notices share the keyboard,
mouse and Paste Special paths. PW-only copying preserves destination notes and
other unselected fields, with undo.

Modern/Classic profiles are checked through real Pygame input, preference save,
reload, cancellation, write failure and reset. Modern Ctrl+Insert copies without
rolling PW values; Classic retains roll. Modern +/-/0 work only in the intended
audition contexts; pattern numbers and text dialogs keep their meaning. Octave
buttons were exercised at 960x540 and 480x360 in both profiles, including range
limits and the next audition note's octave.

## Instrument monitoring

Actual-trigger tests cover one instrument on multiple voices, instrument memory,
portamento without retrigger, delayed notes, retriggers and release tails. Solo
restores the earlier instrument mute set when disabled, and channel monitoring
remains an independent restriction. Restart lookahead, including a future loop,
never changes the live monitor. Traced musical register writes are identical
with monitoring enabled or absent.

Native 6581 and 8580 checks mute/unmute a sounding instrument without retriggering
or changing its shadow registers. A spawned worker follows ownership changes in
audition, applies monitoring during song playback, changes it while paused and
preserves monitor choices across panic/start. GUI tests check buttons beside bank
rows, compact selected-instrument controls, no accidental row selection or song
edit, disabled empty/sample controls, and clearing monitors on new/load/deletion.

## Recording and automation resets

While disarmed, PW recording has no channel-choice hit target or keyboard focus.
Arming reveals its controls, with a red REC_ARM role. Saved color overrides and
preference reset are tested. Layouts were inspected at 1920x1080, 960x1080,
960x540 and 480x360; expanded controls fit and wrap in narrow panels.

R/RA prefixes in PW do not modify the song, undo history or encoded project.
Completing RAL writes all five resets in one undo step to the current cell only.
Escape, navigation, focus loss, mouse clicks, menus and page changes cancel
incomplete input. Backspace, invalid input, R then Enter for PW only, immediate
ADSR R and Caps Lock audition are covered. The Reset all automation button
operates on selected rows/channels, remains visible without clipboard buttons,
preserves notes/FX/instruments/extension data, and is undone atomically. R/RAL
display and native-save round trips retain the existing per-field -1 encoding.

The existing automation playback/export tests remain in the full suite. No
export player, dependency or musical-format version change is required.

## Release archives

The incremental archive is based on the first final v0.2.25 tree and includes
its later launcher warning refresh. Packaging verifies that both delivered
v0.2.25 variants plus the incremental overlay exactly equal the full v0.2.26
archive. Both ZIPs use the `sidpulse-tracker/` root; no removals are needed.
SHA-256 checksums accompany the two archives. Source scans exclude private
project material and machine-specific paths.
