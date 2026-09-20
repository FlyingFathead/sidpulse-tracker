# Runtime performance: v0.2.37 against v0.2.36

174 matched serial trials cover three repetitions with alternating version
order, followed by six longer PCM trials and four candidate-only rapid-navigation
trials: 184 measurements in total. The baseline is the
unchanged delivered v0.2.36 full ZIP. Both releases use the same source songs,
dependencies, buffer sizes and enabled scopes. The new drum presets are exact
stored instruments; opening the catalog reads 3.2 kB of JSON once per opening.
No fitting, file access, new thread or timer was added to ordinary playback.
The two header buttons reuse the existing button bitmap cache.

Environment: Python 3.12.14, Linux x86_64, numpy 2.5.3, pygame-ce 2.5.7,
pyresidfp 0.17.0, SDL dummy audio/video. Live trials use two CPUs; isolated
audio/draw trials use one. No tests, builds or other heavy jobs ran alongside
measurement. Percentages represent one logical CPU core. The UI and audio
worker are separate processes; export/fitting worker CPU is separate again.
These measurements compare both releases in this environment, not the absolute
CPU numbers from earlier environments or physical audio devices.

The updated build recorded **zero gaps and zero missing frames in all 58 live
trials**, including the four rapid-skip trials. Stopped combined CPU was 4.55%
for both releases. Offline audio cost changed by -1.1% to +2.6%; median GUI
cost changed by -0.038 to +0.107 ms per frame. These are small absolute changes.
The longer PCM repeat did not reproduce the original candidate CPU spike.

One baseline recording trial stalled, recording nine gaps / 20,480 missing
frames and a maximum draw time of 5.04 seconds. That result is retained in the
table and raw data; it is not evidence that this update fixes every recording
stall. All three candidate recording trials were clean.

## Live application

Values are medians of three runs. Gaps, missing frames and late callbacks are
totals across all three runs. Each ordinary case targets five seconds after
warmup; fitting targets eighteen seconds. Actual elapsed times are in the raw records. All Info voice scopes stay enabled.
Export measures the busy comparison dialog and then cancels unfinished work;
it measures contention rather than a complete export's elapsed time.

| Case | Buffer | UI CPU old → new | Audio CPU old → new | Gaps old/new | Missing frames old/new | Late callbacks old/new |
|---|---:|---:|---:|---:|---:|---:|
| playback / sid / info | 2048 | 19.49% → 19.23% | 21.98% → 21.71% | 0/0 | 0/0 | 0/0 |
| playback / sid / info | 512 | 19.07% → 18.98% | 24.25% → 24.24% | 0/0 | 0/0 | 0/0 |
| playback / pcm / info | 2048 | 19.23% → 20.88% | 21.95% → 23.36% | 0/0 | 0/0 | 0/11 |
| playback / pcm / info | 512 | 19.28% → 19.25% | 25.47% → 24.47% | 0/0 | 0/0 | 1/1 |
| stopped / sid / info | 2048 | 2.90% → 3.10% | 1.66% → 1.45% | 0/0 | 0/0 | 0/0 |
| paused / sid / info | 2048 | 3.10% → 3.31% | 1.45% → 1.66% | 0/0 | 0/0 | 0/0 |
| export / sid / info | 2048 | 42.73% → 42.11% | 23.05% → 22.86% | 0/0 | 0/0 | 0/0 |
| export / sid / info | 512 | 41.80% → 42.77% | 25.83% → 26.03% | 0/0 | 0/0 | 4/1 |
| export / pcm / info | 2048 | 44.21% → 47.33% | 22.57% → 23.27% | 0/0 | 0/0 | 1/0 |
| export / pcm / info | 512 | 46.41% → 46.65% | 25.57% → 25.75% | 0/0 | 0/0 | 12/2 |
| startup / sid / pattern | 2048 | 3.11% → 3.31% | 1.66% → 1.45% | 0/0 | 0/0 | 0/0 |
| audition / sid / info | 2048 | 18.01% → 19.64% | 19.63% → 19.85% | 0/0 | 0/0 | 0/0 |
| sample / sid / samples | 2048 | 11.60% → 12.02% | 9.94% → 10.31% | 0/0 | 0/0 | 0/0 |
| edit / sid / pattern | 2048 | 22.99% → 23.19% | 11.80% → 12.62% | 0/0 | 0/0 | 0/0 |
| record / sid / info | 2048 | 28.85% → 27.09% | 23.12% → 21.75% | 9/0 | 20480/0 | 37/0 |
| fit / pcm / info | 2048 | 23.94% → 23.81% | 23.63% → 23.19% | 0/0 | 0/0 | 0/0 |
| fit / pcm / info | 512 | 23.27% → 23.25% | 26.49% → 25.54% | 0/0 | 0/0 | 3/6 |

## Offline audio pipeline

Twelve seconds per trial, including SID rendering, conditioning, scopes and
metering. Values are median CPU milliseconds per block; smaller is better.

| Input | Buffer | v0.2.36 | v0.2.37 | Change |
|---|---:|---:|---:|---:|
| sid | 2048 | 6.369 | 6.300 | -1.1% |
| sid | 512 | 1.782 | 1.828 | +2.6% |
| pcm | 2048 | 6.410 | 6.365 | -0.7% |
| pcm | 512 | 1.779 | 1.794 | +0.9% |

## GUI drawing

Median CPU milliseconds per frame, after cache warmup. Each trial draws 200
frames. The candidate full header includes both new navigation buttons.

| Window | Page | v0.2.36 | v0.2.37 | Difference |
|---|---|---:|---:|---:|
| [640, 480] | pattern | 1.049 | 1.069 | +0.020 ms |
| [640, 480] | info | 1.027 | 1.088 | +0.061 ms |
| [640, 480] | samples | 0.780 | 0.821 | +0.041 ms |
| [640, 480] | instrument | 0.908 | 1.015 | +0.107 ms |
| [1280, 900] | pattern | 2.710 | 2.697 | -0.014 ms |
| [1280, 900] | info | 2.078 | 2.180 | +0.101 ms |
| [1280, 900] | samples | 1.728 | 1.690 | -0.038 ms |
| [1280, 900] | instrument | 2.322 | 2.325 | +0.003 ms |

## Longer PCM recheck

One original candidate PCM/2048 trial had 47.25% UI CPU, 55.52% audio CPU,
11 late callbacks and 12 producer blocks over budget, with zero missing frames.
Its raw record remains in the main matrix. Three further matched pairs use
600 UI-frame windows (about ten seconds) to check reproducibility; no implementation changes were made
between the original and repeat measurements.

| Version | UI CPU median | Audio CPU median | Combined CPU median | Gaps | Missing frames | Late callbacks |
|---|---:|---:|---:|---:|---:|---:|
| baseline | 18.96% | 22.03% | 41.24% | 0 | 0 | 0 |
| candidate | 19.16% | 21.42% | 40.49% | 0 | 0 | 0 |

## Rapid order navigation

Four additional candidate-only live trials repeatedly send keypad +/- every
0.2 seconds across 480 UI frames (about eight seconds). They use the same SID/PCM arrangements, Info
page and all scopes. The audio worker and monotonically advancing sample clock
are checked throughout. These are stress measurements, not before/after CPU
comparisons because v0.2.36 has no playback order-skip command.

| Input | Buffer | Commands | UI CPU | Audio CPU | Gaps | Missing frames | Late callbacks |
|---|---:|---:|---:|---:|---:|---:|---:|
| sid | 2048 | 38 | 19.34% | 22.04% | 0 | 0 | 0 |
| sid | 512 | 37 | 19.18% | 24.49% | 0 | 0 | 0 |
| pcm | 2048 | 37 | 19.30% | 21.63% | 0 | 0 | 0 |
| pcm | 512 | 37 | 19.43% | 24.61% | 0 | 0 | 0 |

## Interpretation and limits

See the accompanying validation record for register-trace equality and timing
checks. Ordinary playback has no new DSP algorithm or per-sample work. Order
navigation is processed only when requested, using the existing tick boundary.
The sequencer retains one pending order target so rapid presses accumulate
correctly. Its ordinary row setup clears that field; it does not reset voices.

A late callback or over-budget producer block does not necessarily mean audible
loss: a gap/missing-frame counter records failure to provide queued audio.
Inspect all counters in the raw records rather than treating CPU alone as an
audio-quality verdict. Finite fitting/export jobs can occupy a core; low POSIX
background priority remains enabled. Neither a small UI nor disabled scopes was
used to disguise a performance problem.

2048 remains the default. A clean 512-sample trial does not remove the underruns
already observed under v0.2.36 export stress. Windows, physical audio drivers,
long sessions and hardware C64 playback still need separate measurements.
All four SQUEEZER implementations, both DIGI methods, source samples, native SID
backend, voice programs and audio conditioning are unchanged from v0.2.36.

Raw measurements, source hashes and environment records are in
`validation/v0.2.37/runtime/`, `runtime-extra/`, `runtime-pcm-followup/` and
`skip-stress.jsonl`.
Run `scripts/benchmark_runtime.py --baseline <v0.2.36> --candidate <v0.2.37>
--out <fresh-directory> --repetitions 3` to repeat the complete matched matrix.
