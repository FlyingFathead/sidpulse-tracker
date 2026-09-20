# Performance and validation: v0.2.33 versus v0.2.32

150 timing trials ran serially: 126 release comparisons and 24 sample-tool checks.
Three repetitions use identical input files, the native SID backend, 48 kHz
audio, enabled scopes and 2048/512-frame buffers. Version order alternates.
The baseline is the delivered v0.2.32 full ZIP. No tests, emulators or other
heavy jobs ran alongside the measured trials. Inputs remain unchanged.

Environment: Python 3.12.14, pygame-ce 2.5.7, NumPy and pyresidfp on Linux x86_64.
CPU affinity limits offline/UI workers to one allowed CPU and live workers
to two. SDL dummy devices test scheduling without a physical audio device.
Exact versions, affinity, source hashes and every raw result are in
`validation/v0.2.33/performance-environment.json` and the adjacent JSONL files.

## Offline audio CPU

Median CPU milliseconds per render block, including conditioning, meters,
voice scopes and activity snapshots:

| Song | Frames | v0.2.32 | v0.2.33 | Change |
|---|---:|---:|---:|---:|
| Synthwave SID | 2048 | 6.900 | 6.566 | -4.8% |
| HERMO.ROM PCM | 2048 | 6.521 | 6.483 | -0.6% |
| Synthwave SID | 512 | 1.728 | 1.737 | +0.5% |
| HERMO.ROM PCM | 512 | 1.718 | 1.737 | +1.1% |

## UI CPU

Median CPU milliseconds per drawn frame. Scopes and all new controls remain
enabled in the default comparison; the sample page preserves its bank list.

| View | v0.2.32 | v0.2.33 | Change |
|---|---:|---:|---:|
| pattern-1280x900 | 2.874 | 2.943 | +2.4% |
| info-1280x900 | 2.158 | 2.103 | -2.5% |
| pcm-samples-1280x900 | 1.616 | 1.509 | -6.6% |
| pcm-instrument-1280x900 | 2.013 | 2.047 | +1.7% |
| pattern-960x1080 | 3.326 | 2.918 | -12.3% |
| info-960x1080 | 2.079 | 2.064 | -0.7% |
| pcm-samples-960x1080 | 2.047 | 1.956 | -4.4% |
| pcm-instrument-960x1080 | 1.722 | 1.749 | +1.6% |

Small positive changes are reported explicitly. The largest default UI
increase is about 0.07 ms/frame, with overlapping trial ranges; these runs
do not show a material playback or interaction regression. The large negative
pattern-view percentage includes noisy baseline timings and is not claimed
as an optimization.

## Real-time playback

All 42 live trials completed with **zero gaps and zero missing frames**.
Thirty-six exercise ordinary playback, export analysis and the real synthesis
workflow. Six additional trials keep the Info page and voice scopes active
throughout fitting to isolate the background computation cost.

| Case | Version | Audio CPU, % of one core | UI CPU, % of one core | Late callbacks (sum) |
|---|---|---:|---:|---:|
| live-info-2048 | baseline-sid | 20.06 | 16.66 | 0 |
| live-info-2048 | candidate-sid | 20.25 | 17.05 | 0 |
| live-info-2048 | baseline-pcm | 20.58 | 17.64 | 0 |
| live-info-2048 | candidate-pcm | 19.99 | 16.40 | 0 |
| live-info-512 | baseline-sid | 22.82 | 16.64 | 0 |
| live-info-512 | candidate-sid | 22.33 | 17.01 | 0 |
| live-info-512 | baseline-pcm | 22.49 | 16.48 | 8 |
| live-info-512 | candidate-pcm | 22.48 | 16.54 | 0 |
| live-pcm-export-2048 | baseline-pcm | 20.65 | 44.85 | 0 |
| live-pcm-export-2048 | candidate-pcm | 20.97 | 45.01 | 0 |
| Fitting off, scopes on | v0.2.33 | 20.40 | 16.27 | 1 |
| Fitting on, scopes on | v0.2.33 | 20.66 | 24.66 | 0 |

The normal product changes to F3 when the fit is ready, which stops Info-page
voice scopes. Its lower measured audio CPU is therefore not credited as a
performance improvement. The fixed-background comparison above retains scopes.
Every fitting trial produced a proposal. Timing variation and late callbacks
remain visible in raw results; short dummy-device trials cannot guarantee
dropout-free playback on every machine or physical audio device.

## New toggle costs

Normalization preferences and Auto-squeeze were also drawn in their opposite
states. They run audio processing only during an explicit import or squeeze.

| F3 state | 1280×900 ms/frame | 960×1080 ms/frame |
|---|---:|---:|
| Defaults: before on, after off, import squeeze on | 1.509 | 1.956 |
| Import squeeze off | 1.507 | 1.900 |
| Normalization before/after off | 1.519 | 1.903 |
| Normalization before/after on | 1.533 | 1.894 |

Freeze shows a protected summary in place of editing controls, so its UI
cost differs by design. It has no audio or C64 playback branch.

| F4 size | Unfrozen ms/frame | Frozen ms/frame |
|---|---:|---:|
| 640x480 | 0.811 | 0.723 |
| 960x1080 | 1.711 | 1.398 |
| 1280x900 | 2.069 | 1.302 |

## Sound, editor and C64 validation

- Exact raw PCM, conditioned PCM, SID writes/cycles and sequencing state match
  the baseline across seven songs, including a 200-second PCM stress run.
- The broad suite exercised 1,592 cases: 1,583 passed and nine exposed layout
  or mixed-version worker issues. After corrections, all 115 affected cases
  passed. Final compact sample controls passed 17 cases; the final freeze,
  synthesis and clipboard follow-up passed 22. No failing case is left open.
- C64 unit checks verify decoder events, ownership handoff, sample/DAC writes,
  loop/stop, memory and instruction budgets. All bundled players reproduce
  from their assembly source. Independent interrupt tests cover entry delays.
- Full HERMO.ROM PRGs run past the loop boundary in VICE 3.7.1 classic reSID
  with 6581/8580 and PAL/NTSC. The 8580 comparison isolates all 32 drum hits.
- The new C64 NMI bound is 121 cycles per approximately 4 kHz sample. The
  display and sprites are off, and the compiler reserves additional scheduling
  capacity. This is a different resource tradeoff from the old volume-DAC
  routine, not a claim of lower C64 CPU use.
- Physical C64 listening and Windows/device-specific scheduling remain to be
  tested. The experimental warning and model/clock requirements stay visible.
