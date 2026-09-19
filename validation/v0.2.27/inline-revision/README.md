# Inline recording and SQUEEZER v2.0 revision

This follows the initially delivered v0.2.27 candidate. The comparison baseline
is `fbe9017`, including its executable launcher fix. Both runtime snapshots report
application version 0.2.27; use the **baseline/candidate labels**, not the version
string, when grouping measurements.

The unchanged v8 stress song has SHA-256
`91032c512875fa96636d21ba05bacda2a309e4e67a30ee96f42b1f47e7c58430`.
The native source is not included in this public validation directory.

- `squeezer-v8/` has three serial, alternating-order SID/PRG export trials for
  each squeezer version. Every compact export executes both loop passes and
  reinitialization with ordered-write, timing, memory and CPU-budget checks.
- `squeezer-examples/` covers all four previously bundled `.sidpulse` examples
  with both squeezer versions and both export targets.
- `SQUEEZER-AB.md` summarizes those sizes and compiler/replay measurements.
- `performance/` compares default UI rendering, full-arrangement native audio,
  live playback and live recording. Requested M/S and scope features remain
  enabled; view-specific scope visibility follows the normal application.
- `runtime-sha256.json` identifies the measured source and bundled assets.
- Screens show inline recording, expanded selectors, minimum window layout,
  empty-slot ADSR recording and top/middle/bottom positions in both banks.

Reproduce from the repository root with isolated baseline/candidate snapshots:

```bash
python scripts/compare_squeezers.py --out ../example-comparison --repetitions 1
python scripts/compare_squeezers.py path/to/v8.sidpulse --out ../v8-comparison --repetitions 3
python scripts/benchmark_inline_revision.py --baseline ../baseline --candidate . --input path/to/v8.sidpulse --out ../performance-comparison --repetitions 3
```

Performance runs are serial and separate from regression tests, export analysis,
profiling and native PCM comparison. The 200-second audio case covers the full
189.89-second v8 arrangement and part of its next loop. GUI timings use synthetic
active scopes and changing rows; live timings use the real spawned audio worker.
SDL dummy output is not a physical-device or Windows latency test. The export
instruction model is not a full C64 hardware/analog SID emulator.

## Final revision gates

- Complete suite: **1,375 passed**, no failures or skips, 222.03 seconds.
- Focused final rendering/input checks: **175 passed**, 8.72 seconds.
- `full-tests.*` and `focused-render.*` are the final runs. The earlier full and
  export runs remain explicitly named intermediate/focused evidence.
- `final-ui/`: 70 records, five matched trials per view/version after button caching.
- `final-live/`: seven additional delivered-code live cases, all counters zero.
- `interim-zoom-ui/`: 70 follow-up records before the final button optimization.
- `native-pcm/`: exact native comparison for v8 (200 seconds) and all four bundled
  examples (12 seconds each). Raw/conditioned PCM, writes/clocks and final state match.
- `runtime-buttons-sha256.json`: final runtime; the other manifests identify
  earlier measured snapshots. After PCM comparison only the two UI drawing
  modules changed. Exporter and synthesis files are identical to measured files.
- `quarter-hd-zoom3.png` and the squeezer-version screenshots cover the final
  responsive layout and both version choices at large/small sizes.

The perfs report retains the earlier 512-frame scheduling lateness. Zero counters
in the final single-trial checks do not erase earlier results or prove every host.

Final packaging removed one trailing blank line from the retained popup module.
Its parsed syntax tree is identical to the tested version.
`runtime-delivered-sha256.json` records this whitespace-only difference from
`runtime-buttons-sha256.json`; no executable behavior changed after the gates.
