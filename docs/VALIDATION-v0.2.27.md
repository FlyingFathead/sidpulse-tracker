# SIDpulse Tracker v0.2.27 validation

Final complete suite: **1,375 passed**, no failures/skips, 222.03 seconds.
Final focused rendering/input suite: **175 passed**, 8.72 seconds. Complete logs
and JUnit reports are under `validation/v0.2.27/inline-revision/`.

## Focused validation

Focused confirmation, automation, renderer, instrument monitoring, settings and
app tests pass. Pixel comparisons verify cached and direct cell drawing in F2
and Info at 960x1080, 1280x900 and 480x360, including value edits, reset commands,
theme changes and zoom. Mouse targets are checked after scrolling, resizing and
expanding/collapsing the control pane. Responsive layouts retain fonts during
steady frames.

Cut and Reset begin on Cancel. Tests cover mouse activation, Enter cancellation,
keyboard checkbox focus/Space, checkbox cancellation, preference persistence and
write failure, changed targets, PW-only cut, clipboard contents and atomic undo.
Reset preserves notes, FX, instrument definitions and extension data. User
preference reset restores Cut confirmation and M/S defaults.

The M/S setting hides controls in both banks, bypasses instrument monitoring,
preserves channel monitoring, restores session choices when enabled, and leaves
the song unchanged. Existing native monitor tests cover held-note mute/unmute,
trigger ownership and the spawned audio worker. Menu tests exercise the new UI
Settings route and the latched parent button after mouse navigation.

The dirty title indicator is cached; the exact editor dirty check still guards
quit/save/autosave. Tests cover edits, undo, redo, save and out-of-history changes.

Screens were inspected for Cut/Reset at half-HD and small window sizes, the
ordered F2 toolbar, parent/child menus and M/S on/off. Native Windows, physical
audio devices and C64 hardware are outside this Linux SDL dummy validation.

## Recording and scrolling

The default inline recorder stays inside F4; legacy popup method 1 remains
available. Tests cover all five parameters, red single-channel arming, explicit
channel changes, independent instrument browsing, direct bank Disarm, mouse and
focused keyboard control, one-pass key-hold behavior, cancellation and one Undo.
A real spawned audio worker exercises PW and ADSR capture. Stopped/unarmed
controls do not alter instruments or notes. Save/cancel preserves take semantics.
Small windows and zoom levels 1/2/3 keep the blue slider and controls above the
footer. Screens include half-HD, quarter-HD, minimum-size and high-zoom layouts.

Both banks start at 001 for new/load, including songs with saved instrument 24.
Every slot is exercised down and up at two window sizes, with F2 centering off
as well as on. View changes preserve selected empty slots. Centering clamps at
both ends without blank padding. Mouse, wheel and keyboard navigation agree.

## Export and native sound checks

SQUEEZER v1.0 retains its original optimizer byte-for-byte. The v8 v1.0 SID is
byte-identical to the previous compiler output. v2.0 is deterministic, retains
all v1.0 choices and selects no larger export in these trials. Dropdown tests
cover mouse/keyboard, disabled/hidden states, invalidation and persistence.
PRG tests execute both startup wrappers, version credits and wrong-clock exits.

Both SID and PRG targets, both squeezer versions, all four bundled native examples
and v8 pass export verification. v8 has three alternating-order trials per
version/target; examples have one each. Every compact output traverses two loops
and reinitializes, checking ordered writes, CIA timing, explicit gate delay,
memory ownership and cycle budgets. Raw data and sizes are in
`validation/v0.2.27/inline-revision/SQUEEZER-AB.md`.

Native baseline/revised comparison matches raw PCM, conditioned PCM, SID writes
and clock calls, and final playback state. v8 runs for 200 seconds (full song and
loop restart); each bundled example runs for 12 seconds with irregular block
sizes. Sources are byte-checked before/after. The initialized-emulator fork is
only a test control; production audio/export workers retain spawn.

## Performance

The report retains starter v0.2.23 and v0.2.26 measurements. This revision adds
222 serial timing records against the earlier delivered v0.2.27, using unchanged
v8 and default M/S/scopes. Tests, profilers and exports run outside timing trials.
UI and audio CPU are reported separately. Final five-trial GUI medians improve
in all seven cases: instrument -9.8%, instrument scrolling -6.1%, inline PW
recording -53.8%. Native audio timings remain within observed trial variation.

Final live cases show no gaps/missing frames; earlier three-trial 512-frame
scheduling lateness remains documented. All raw measurements, source hashes,
profiles and limits are retained. Physical audio devices, Windows scheduling and
C64 hardware/analog sound are outside these Linux SDL dummy and instruction-model
checks. The data support these tested workloads, not a universal guarantee.

## Packaging

Full and incremental ZIPs use the `sidpulse-tracker/` root. The overlay covers
v0.2.26 and previous v0.2.27 candidates. Packaging checks ZIP integrity, privacy,
version consistency, exact overlay/full equality and run.sh executable metadata.
No deletions or new dependencies are required. Native project and user preference
files do not need replacement.
