# v0.2.39 working-tree checkpoint-002 validation

This follow-up is based on checkpoint-001, not the original v0.2.39 release.
It changes the F11 length gestures, protects populated trailing rows, reverses
the on-screen octave control order, and warns when opening a native project
stamped with an older SIDpulse Tracker version.

## Results

- Full suite: **1,733 passed** in 616.79 s on Linux/Python 3.12.14 with
  pygame-ce 2.5.7 and SDL dummy devices. Focused length, octave, compatibility,
  project-drop and checkpoint cases: **95 passed**.
- Headless example startup passed. At 480×360, the octave buttons and their hit
  regions run left to right as **−1, 0, +1**. A blocked F11 decrement displayed
  the exact occupied row and left the pattern unchanged.
- F11 tests verify that a single row-count click selects, a double-click opens
  the length dialog, each triangle applies one undoable row change, and a row
  containing either cell data or a filter control prevents a destructive
  shorten. The same rule applies to the slider/number dialog. A project saved
  after a permitted shorten still contains its populated final row.
- Version checks use the saved app version when present. Older-version native
  projects load and show a compatibility notice; newer versions, future formats
  and unfamiliar fields retain their existing warnings. A file without an app
  version stamp cannot be dated to a specific release. Future data is preserved
  where representable, but unsupported features cannot be promised to play or
  export correctly.

Screenshots: [F11 at 480×360](../validation/v0.2.39-pattern-bank-drop-checkpoint-002/f11-480.png)
and [protected row notice](../validation/v0.2.39-pattern-bank-drop-checkpoint-002/f11-protected-480.png).

## Serial comparison with checkpoint-001

The same bundled song, 48 kHz audio, enabled scopes, 2048-sample buffer and
SDL dummy devices were used in alternating baseline/candidate order. Three
offline trials per version measured two seconds of audio and 120 UI frames:

| Case | Checkpoint-001 median CPU | Checkpoint-002 median CPU |
|---|---:|---:|
| Offline audio block | 7.441 ms | 7.536 ms |
| F11 480×360 frame | 0.799 ms | 0.838 ms |
| F4 1280×900 frame | 3.123 ms | 3.223 ms |

All six offline audio trials recorded zero over-budget blocks. Two three-second
live F11 trials per version drew 180 frames each; all recorded **zero audio gaps
and zero late callbacks**. The per-trial measurements and environment are in
[performance.json](../validation/v0.2.39-pattern-bank-drop-checkpoint-002/performance.json).
These short dummy-device measurements do not establish physical-device or
Windows performance. No release or CI claim is made for this checkpoint.
