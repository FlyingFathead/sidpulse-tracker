# SIDpulse Tracker v0.2.25 validation

## Results

- Full regression suite: **1154 passed**, no failures or skips, 178.78 seconds.
- Focused feature/audio/recovery checks: **71 passed**, 2.01 seconds; the later
  unavailable-audio reset case is included in the full suite above.
- Both headless smoke commands passed: `--example` and `--play-welcome-song`.
- Live native-audio check passed: narrow scope telemetry, preference reset with
  a real output-buffer change, paused transport preservation, then resume and
  scope processing disabled during playback.
- The subsequent launcher-only addition passed Bash syntax checking, banner
  checks at 42/80/132 columns, and an actual run.sh startup smoke with a 96-column
  banner and exit code 0. Windows wrapper/PowerShell invocation and CRLF line
  endings were reviewed; native Windows execution was not available.
- Python 3.12.14, pygame-ce 2.5.7, pyresidfp 0.17.0, Linux x86_64 with SDL dummy
  audio/video. These checks do not represent physical audio or Windows hardware
  validation. No synthesis/export implementation was changed for this release.

## Selection and paste

Tests cover PW-only copying to another voice while its cursor is on NOTE,
note/octave grouping, all Paste Special choices, rejected attempts to paste
uncopied fields, reverse selections and multi-voice endpoint fields. Insert,
cut, roll, transpose, instrument changes, mix, zero/reset values, FX grouping,
cross-pattern copy and boundary clipping are covered. Unselected destination
data and unknown extension fields survive partial edits; undo/redo is checked.

Pygame input tests exercise drag selection, field headers, keyboard selection,
clipboard buttons, Paste Special cancellation, edge scrolling and focus loss.
Preference toggles persist without dirtying musical data. Legacy whole-channel
and pattern operations retain their existing regression coverage.

## Responsive display

Rendered F2/Info screens were inspected at 960x1080, 960x540, 800x600 and 1280x900.
The narrow default exposes all three F2 voice lanes with the control pane
collapsed. Expand/collapse works in both views and survives reload. Scope hit
rectangles fit narrow Info panels and do not overlap mute/solo buttons.
Settings Menu, the Cancel-default reset dialog and Paste Special were inspected.

With native playback of the PW sweep demonstration, live red scope traces were
captured at 960px with both expanded and collapsed control panels. Turning scopes
off clears per-voice telemetry while playback remains active. The existing native
scope test also verifies that scope PCM is separate from the audible output.

## Preference reset

Reset is the last Settings Menu item. Enter, Escape and a mouse click all cancel
the default confirmation without changing preference bytes. Confirmed reset
restores the supported user preferences while preserving song data, dirty state,
undo revision, a saved user preset and an existing recovery file.

Simulated worker tests cover stale acknowledgements, failed output switching,
cancellation during an output change, and atomic preference-write failure with
restoration of the prior output. A pre-existing audio initialization failure
still permits clearing bad configuration and shows restart guidance.

A real spawned audio worker started at 4096 samples, played the sweep project,
paused, and reset to System default / 2048 samples. The complete published paused
playback state and editable song were unchanged. Preferences were atomically
cleared, playback resumed, and disabling scopes left playback running.

## Release contents

The incremental archive is relative to the final v0.2.24 source release. The full
archive contains every tracked source file. Both use the `sidpulse-tracker/`
top-level directory. Packaging checks verify archive integrity and byte-for-byte
equality between the v0.2.24 tree plus incremental overlay and the full v0.2.25
archive. SHA-256 checksums accompany both ZIPs. No file removals are required.

Logs are in `validation/v0.2.25/`. Existing format, PW recording, export and audio
tests passed in the full suite; detailed previous-release register/PCM comparisons
are recorded in [v0.2.24 validation](VALIDATION-v0.2.24.md).
