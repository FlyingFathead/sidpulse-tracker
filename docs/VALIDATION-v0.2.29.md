# SIDpulse Tracker v0.2.29 validation

**1,423 tests passed** in 300.99 seconds, with no failures or skips. A final
five-test UI check passed after keeping keyboard focus on the selected comparison
button and correcting the compact-PRG verification caption. Logs and sanitized
JUnit results are in `validation/v0.2.29/`.

The tests cover deterministic phrase packing, literal/reference mixtures, empty
streams, shared suffixes, repeat-count boundaries, malformed calls/returns and
extra decoded data. An independent py65 NMOS CPU agrees with the bundled verifier
on every callback's cycles, SID writes and CIA writes across all six new linked
players, loop modes, slow idle calls, termination and reinitialization. Source
cleanup, ordinary exports, native version compatibility and earlier UI/audio
regressions remain covered by the full suite.

The new comparison is byte-identical to three independent compiles for both
SID and PRG. Tests verify shared expensive work, source preservation, oversized
alternatives, fatal semantic failures, exact ties, size-only ties, unknown CPU,
config defaults, cancellation, keyboard navigation and immediate button selection.
Actual spawned-worker tests retain isolation, error and cancellation coverage.
Viewport tests include 360×360, 480×360 and 960×1080.

64tass 1.58.2974 independently rebuilt all **16 linked compact players** and the
compact PRG wrapper. Build/check output is retained. Hashes prove all **10 earlier
players** and the v1.0/v2.0 optimizer modules are unchanged. The six new players
use fixed embedded workspace, with no decompression buffer or recursive stack.
Both PRG wrappers print tracker 0.2.29 and the selected squeezer version correctly;
wrong-clock exits and squeezed/unsqueezed behavior are tested.

The unchanged v8 source and all four native examples have three serial export
trials for all versions and both targets. Stress-song three-version comparisons
are timed separately and checked against standalone export hashes. Matched native
UI/audio/live trials use immutable v0.2.28 with M/S and scopes enabled. See
[performance evidence and limits](PERFORMANCE-v0.2.29.md).

Screenshots show the three-version box at half-HD, quarter-HD and minimum sizes,
the version dropdown, and an explicitly named equal-result fixture for Joint best.
Final visual inspection checks that all three selection controls remain reachable.
The fixture illustrates tie rendering; it is not an additional musical measurement.

Release checks compare full ZIP bytes with overlays on v0.2.26, both previously
delivered v0.2.27 trees and v0.2.28. OS unzip restores executable run.sh even over
a deliberately nonexecutable launcher; direct full/overlay launcher smoke runs
verify the 0.2.29 banner and example playback. Packaging rejects private project
notes, reference-source archives and developer-machine paths. No remote push,
tag or publication is performed.

Native format versions remain **6/7**. Squeezer selection and comparison settings
are user preferences; they do not change songs or native synthesis. A new save
records application version 0.2.29. The GoatTracker 2.77 reference study is
conceptual; no reference code, player or example song is shipped.

These checks establish the stated Linux instruction/UI/audio results, not Windows
or physical audio-device timing, arbitrary C64 IRQ/VIC scheduling, or identical
analog SID attacks between differently timed replay routines.
