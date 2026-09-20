# Performance: v0.2.35 versus v0.2.34

45 trials ran serially with three repetitions and alternating version order.
The baseline is the immutable v0.2.34 full release ZIP. Both versions use the
same PCM/SID arrangement, 48 kHz audio, enabled voice scopes, window sizes and
buffer settings. No tests, emulators, builds or packaging ran during measurement.
The 29 Python modules covering audio, sequencing, SID, song and project handling
are byte-for-byte unchanged. Timing measurements still check integration costs.

Environment: Linux x86_64, Python 3.12.14, pygame-ce 2.5.7, NumPy 2.3.5,
pyresidfp 0.17.0. One allowed CPU is used for offline/UI trials and two for
live trials. SDL dummy devices measure scheduling, not a physical audio device.
Inputs remain unchanged. Source hashes and raw data are in `validation/v0.2.35/`.

## Offline audio

Each trial renders 20 seconds with conditioning, meters and scopes enabled.
Values are median CPU milliseconds per block. DIGI selection affects export,
not this host playback pipeline.

| Buffer | v0.2.34 | v0.2.35 | Change |
|---|---:|---:|---:|
| 2048 | 6.474 | 6.467 | -0.1% |
| 512 | 1.730 | 1.718 | -0.7% |

## Export UI drawing

Median CPU milliseconds per frame, 300 frames per trial. The Info background
and scopes remain enabled beneath the ready-to-analyze export menu. Analysis
is not running in these drawing measurements.
#1 and #2 describe the selected DIGI method, not squeezer versions.

| Window | v0.2.34 | v0.2.35 #1 | v0.2.35 #2 |
|---|---:|---:|---:|
| 640 | 3.751 | 3.774 | 3.833 |
| 1280 | 5.412 | 5.357 | 5.537 |

## Live playback

15 trials of 10 measured seconds after warmup. Ordinary playback uses the
2048-frame default buffer; background export comparison is stressed at 512.
The Info view and scopes remain enabled under the export modal. CPU values
are median percentages of one core; counts are totals over three repetitions.

| Case | Version/method | Audio CPU % | UI CPU % | Gaps | Missing frames | Late callbacks |
|---|---|---:|---:|---:|---:|---:|
| live-info-2048 | baseline | 19.88 | 15.69 | 0 | 0 | 0 |
| live-info-2048 | candidate-1 | 19.89 | 15.77 | 0 | 0 | 0 |
| live-export-512 | baseline | 22.99 | 44.61 | 0 | 0 | 14 |
| live-export-512 | candidate-1 | 23.10 | 45.27 | 0 | 0 | 3 |
| live-export-512 | candidate-2 | 23.08 | 44.62 | 0 | 0 | 17 |

Totals: **0 gaps, 0 missing frames, 34 late callbacks**.
All requested background analyses completed without compiler errors. Short
fixed-input runs do not guarantee physical-device or physical-C64 performance.

## Reproduce

Use `scripts/benchmark_releases.py --worker TASK.json` with an immutable prior
release and identical PCM input. Repeat each case three times, alternating
version order; keep other heavy work stopped. The worker task uses the existing
`repo`, `song`, `cpus`, `kind`, `frames`, `seconds`, `size`, `page` and `scopes`
fields. Use `digi_method: 1` or `2` for the candidate export choice,
`export_dialog: true` for ready-menu drawing, and `export_analysis: true` for
background analysis during live playback. The baseline has one PCM method.
