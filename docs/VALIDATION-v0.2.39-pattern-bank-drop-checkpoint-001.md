# v0.2.39 pattern bank, instrument clear and dropped project checkpoint

Base: the supplied v0.2.39 source snapshot. This is a working-tree candidate,
not a tagged release. The note covers the F11 row-length controls, F4 bulk
instrument clearing, and explicit validation/confirmation for dropped projects.

## Checks

- Full suite: **1,731 passed** in 629.17 s on Linux/Python 3.12.14 with
  pygame-ce 2.5.7 and SDL dummy drivers.
- Focused editor/file-dialog checks: **95 passed**. An earlier focused run
  covering F11/F4 and related project paths: **196 passed**.
- Both headless startup smokes passed (`--example`, `--play-welcome-song`).
  Command and effect references were regenerated (282 and 64 entries).
- At 480×360 and 1280×900, the F11 row count, selected-row triangles and F4
  clear action were drawn and checked for visible hit rectangles. The dropped
  project prompt fits at 480×360 with Cancel focused by default.
- Tests cover invalid JSON, structurally invalid projects, wrong extension,
  clean/dirty replacement, Cancel, save-before-open for named and unnamed
  projects, source changes after the first check, and failed saves. Invalid
  input leaves the open project and its path intact. The native decoder enforces
  its format, schema and 40 MiB limit; this is not a cryptographic authenticity
  check on files supplied by another person.
- Instrument clear tests cover both Cancel-default warnings, a saved project
  snapshot, failed snapshot saving, empty-bank playback/export, native
  round-trip, and undo/redo. Pattern shortening remains a single undoable edit.

Screenshots: [F11 480](../validation/v0.2.39-pattern-bank-drop-checkpoint-001/f11-480.png),
[F11 1280](../validation/v0.2.39-pattern-bank-drop-checkpoint-001/f11-1280.png),
[F4 480](../validation/v0.2.39-pattern-bank-drop-checkpoint-001/f4-480.png),
[F4 1280](../validation/v0.2.39-pattern-bank-drop-checkpoint-001/f4-1280.png),
[dirty drop 480](../validation/v0.2.39-pattern-bank-drop-checkpoint-001/drop-dirty-480.png).

## Serial baseline comparison

The same bundled `autumn-at-five.sidpulse` input, 48 kHz audio, enabled scopes
and SDL dummy devices were used against the supplied base and candidate, in
alternating order. Offline UI workers drew 120 frames per trial; offline audio
workers rendered two seconds. Five repeat trials per version gave these medians:

| Case | Base CPU | Candidate CPU | Change |
|---|---:|---:|---:|
| 2048-frame audio block | 6.851 ms | 6.695 ms | −2.3% |
| 512-frame audio block | 1.872 ms | 1.943 ms | +3.8% |
| F11 480×360 frame | 0.694 ms | 0.783 ms | +12.7% (+0.089 ms) |
| F4 1280×900 frame | 3.197 ms | 3.223 ms | +0.8% |

F11 draws the new controls and costs about 0.09 ms more per frame in this
comparison. The audio engine, sequencer and SID backend source files are
byte-identical to the baseline; the small CPU changes vary across trials and
are not attributed to audio changes. An initial three-trial run had one
over-budget 2048 block in the candidate. The repeat had one in the base;
the separate 512 run had two in the candidate. The complete raw samples and
environment are in [performance.json](../validation/v0.2.39-pattern-bank-drop-checkpoint-001/performance.json).

Three 2048-buffer and two 512-buffer live trials per version each drew 180
F11 frames over three seconds during song playback. All had **zero gaps and
zero late callbacks**. These short Linux dummy-device measurements do not
represent physical audio hardware, Windows scheduling, or sustained export
contention. No release or CI claim is made for this candidate.
