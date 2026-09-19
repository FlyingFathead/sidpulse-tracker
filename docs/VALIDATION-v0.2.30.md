# SIDpulse Tracker v0.2.30 validation

The final full regression run passed **1,468 tests**. A focused run after the
startup icon integration and small-button label adjustment covers window identity,
shared scrolling, Top 3 selection, real export workers and progress/cancel controls.
The focused run passed 61 cases; the two runs cover 1,470 unique passing tests.
The final Show all preference follow-up passed another 61 cases, including
persistence after cancellation/restart, migration, reset and write-error handling.
Across all three runs, 1,472 unique cases pass. Logs and sanitized JUnit are included. The earlier 1,452-case run and memory-test
rerun remain as development history; its sole stale RAM-bound assertion was
corrected to use the selected player's actual allocation.

New tests cover deterministic dictionary ranking, empty streams, long inline
literal splitting, counted repeats, shared suffix entries, invalid IDs,
nonliteral reference targets, nested calls, missing returns and trailing data.
An independent py65 NMOS CPU agrees with the bundled verifier on every call's
cycles, SID writes and CIA writes for all six new linked players, both loop
modes, idle calls, termination and reinitialization. Decimal flag handling,
owned memory and dictionary immutability are checked explicitly.

The four-version comparison equals independent compiles for SID and PRG. Tests
cover shared work, original-song preservation, unavailable candidates, semantic
failures, complete ties, RAM/cycle tie breaks, unknown CPU, saved defaults,
cancellation, keyboard navigation and immediate mouse selection. Show all is the default and uses two columns in narrow windows; Top 3 is optional. Viewport
coverage includes 360×360, 480×360, 960×540 and 960×1080. Shared scrollbar tests
cover both ends, track paging, drag cancellation, modal isolation, keyboard
centering and unchanged song/filename drafts across lists, help and long text. Existing editor, recording, clipboard and native-format tests remain.

64tass 1.58.2974 independently rebuilt **22 compact players and the PRG wrapper**.
Earlier optimizer sources and player binaries are byte-identical to v0.2.29;
hashes and the final runtime snapshot are included. New players use unchanged
mutable workspace sizes and no additional per-stream state or decompression
buffer. PRG credits and wrong-clock behavior are tested for all four versions.

Serial fresh-process performance trials use the unchanged v8 native song and all
four bundled native examples, SID and PRG. v2.0.1/v2.0.2 have three trials each;
v1.0/v2.0 receive one current-build preservation trial, supplementing their
three-trial v0.2.29 baseline. Three shared four-version analyses are measured on
the stress song. Comparison hashes equal independently produced outputs.
Final native UI/audio/live trials use immutable v0.2.29 with M/S and scopes
enabled, after integrating the shared scrollbars and icon. The earlier UI batch
is retained separately. All ordinary pages plus bank navigation are measured,
with a separate scrollbar-drawing ablation and completed-comparison timings.
See [performance](PERFORMANCE-v0.2.30.md) for CPU, RAM, callback counts and limits.

Screenshots show actual completed results, the dropdown and narrow layouts.
`joint-best-fixture.png` deliberately gives every entry equal measured values to
verify tie presentation; it is a UI fixture, not a musical benchmark.

Release checks compare full ZIP bytes against cumulative overlays on v0.2.26,
both delivered v0.2.27 trees, v0.2.28, v0.2.29 and the initially delivered v0.2.30. OS extraction restores executable
run.sh over a deliberately nonexecutable launcher. Direct clean/overlay launcher
smokes verify the version banner and example playback. ZIPs exclude private notes,
reference archives, the supplied transcript and developer-machine paths.

Native formats stay **6/7**. New saves record tracker 0.2.30. No new runtime
dependencies, remote push, tag or publication. These checks do not replace
Windows, physical audio-device, VICE or real-C64 testing, and do not claim
identical analog sound or cycle spacing between every SID write.

The final-only display preference comparison is recorded in
`validation/v0.2.30/show-all-final/`. `runtime-final-sha256.json` identifies this
revision; `runtime-sha256.json` retains the earlier full measurement snapshot.
The audio, SID, sequencer and export algorithm sources remain byte-identical.
