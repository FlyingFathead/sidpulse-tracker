# Performance: v0.2.34 versus v0.2.33

168 timing trials ran serially: 126 release comparisons, 30 active/inactive
waveform-command trials, and 12 comparisons at the same larger layout. Each
case has three repetitions. The immutable baseline is the delivered v0.2.33
full ZIP. Identical songs, buffers and settings are used for each baseline/
candidate pair. Source files remain unchanged. No tests, emulators, packaging
or other heavy jobs ran alongside measured trials.

Environment: Linux x86_64, Python 3.12.14, pygame-ce 2.5.7, NumPy 2.3.5 and
pyresidfp 0.17.0. Offline/UI workers use one allowed CPU; live workers use two.
Audio is 48 kHz. Scopes stay enabled in the playback comparisons. Exact
dependency versions, CPU affinity, source hashes and raw data are under
`validation/v0.2.34/`. SDL dummy devices test scheduling without a physical
audio device; these short runs cannot guarantee dropout-free hardware playback.

## Offline audio

Median CPU milliseconds per block, including conditioning, meters, scopes and
activity snapshots. Each trial renders 20 seconds.

| Song | Frames | v0.2.33 | v0.2.34 | Change |
|---|---:|---:|---:|---:|
| Synthwave SID | 2048 | 6.667 | 6.529 | -2.1% |
| Synthwave SID | 512 | 1.728 | 1.732 | +0.2% |
| HERMO.ROM PCM | 2048 | 6.529 | 6.461 | -1.0% |
| HERMO.ROM PCM | 512 | 1.729 | 1.713 | -0.9% |

## UI drawing

Median CPU milliseconds per frame, 300 frames per trial. Both releases keep
the requested controls and scopes enabled. W needs two extra character cells;
at the smaller sizes the new layout fits a slightly smaller font while
preserving the number of visible channels and the CTRL pane setting. Do not
interpret lower timings caused by that layout change as engine optimization.

| View | v0.2.33 | v0.2.34 | Change |
|---|---:|---:|---:|
| pattern-1280x900 | 2.814 | 2.620 | -6.9% |
| info-1280x900 | 2.135 | 2.042 | -4.4% |
| pcm-samples-1280x900 | 1.508 | 1.516 | +0.5% |
| pcm-instrument-1280x900 | 2.086 | 2.050 | -1.7% |
| pattern-960x1080 | 2.898 | 2.105 | -27.4% |
| info-960x1080 | 2.060 | 1.952 | -5.3% |
| pcm-samples-960x1080 | 1.961 | 1.913 | -2.5% |
| pcm-instrument-960x1080 | 1.688 | 1.696 | +0.5% |

A second comparison uses 1920×1080, the same font and character
width, all three channels and the CTRL pane in both releases; 500 frames per trial.

| View | v0.2.33 | v0.2.34 | Change |
|---|---:|---:|---:|
| pattern | 3.614 | 3.611 | -0.1% |
| info | 2.801 | 2.804 | +0.1% |

## Live playback

48 live trials completed: **0 gaps, 0 missing frames**.
Both 2048-frame and 512-frame buffers are exercised. CPU values are medians
as percentages of one core; late callbacks are summed over repetitions.

| Case | Release/input | Audio CPU % | UI CPU % | Late callbacks |
|---|---|---:|---:|---:|
| live-info-2048 | baseline-sid | 20.89 | 17.82 | 0 |
| live-info-2048 | candidate-sid | 20.41 | 16.72 | 0 |
| live-info-2048 | baseline-pcm | 20.99 | 17.42 | 0 |
| live-info-2048 | candidate-pcm | 20.41 | 16.19 | 0 |
| live-info-512 | baseline-sid | 22.42 | 16.92 | 0 |
| live-info-512 | candidate-sid | 22.90 | 16.64 | 0 |
| live-info-512 | baseline-pcm | 23.16 | 16.74 | 0 |
| live-info-512 | candidate-pcm | 23.24 | 16.33 | 0 |
| live-pcm-export-2048 | baseline-pcm | 21.58 | 45.85 | 2 |
| live-pcm-export-2048 | candidate-pcm | 21.73 | 45.83 | 1 |
| live-pcm-synthesis-0 | candidate-pcm | 20.90 | 16.75 | 4 |
| live-pcm-synthesis-1 | candidate-pcm | 13.48 | 23.61 | 0 |

The existing sample-fitting trials are retained as background-job smoke
checks. That workflow changes its page on completion, so those rows are not
used to claim an audio performance improvement. Ordinary playback and all
new command trials keep the Info page and scopes active.

## W and sync/ring FX active versus inactive

The two included fixtures have identical notes, instruments and arrangement.
The active version adds W and Z commands on every row and channel. This changes
audio intentionally; it measures the cost of using the controls, not an audio
identity comparison. Scopes are enabled in both cases.

| Case | Off | On | Unit |
|---|---:|---:|---|
| audio-2048 | 6.452 | 6.564 | CPU ms/block |
| audio-512 | 1.698 | 1.703 | CPU ms/block |
| pattern-1280x900 | 2.553 | 2.618 | CPU ms/frame |
| live-2048 | 19.644 | 19.659 | audio core % |
| live-512 | 22.234 | 21.972 | audio core % |

Native audio, conditioned audio, SID write/cycle traces and final state match
v0.2.33 exactly for seven existing songs, including 200 seconds of mixed PCM/SID.
No waveform analysis or additional sample interrupt was added to normal playback.

## Reproduce

Run the commands separately with no other heavy jobs. Use the previous full
ZIP as the baseline and copies of the same original SID/PCM songs.

```bash
python scripts/benchmark_pcm_update.py --baseline ../baseline/sidpulse-tracker --candidate . --song SID_SONG.sidpulse --pcm PCM_SONG.sidpulse --out ../release-perf --repetitions 3 --live-repetitions 3
python scripts/benchmark_waveform.py --candidate . --fixtures validation/v0.2.34 --out ../waveform-perf
```

The fixed-layout cases use `scripts/benchmark_releases.py --worker TASK.json`
with kind `gui`, size `[1920,1080]`, page `pattern` or `info`, 500 iterations,
scopes true, and the same SID input, alternating baseline/candidate three times.

## Export warning and batch synthesis follow-up

24 additional serial trials cover the final export warning and batch fitting,
with three repetitions per case. The 12 live trials use the original HERMO.ROM
PCM arrangement at 960×1080 with Info and scopes held active throughout. The
worker fits both mapped samples; it never applies proposals or changes the
playing song. The fitting worker has its existing lower scheduling priority.
Fitting CPU is temporary work in a separate process; the table measures the
audio process and UI separately, not total CPU across all three processes.

| Buffer | Fitting | Audio core % | UI core % | Gaps | Late callbacks |
|---|---|---:|---:|---:|---:|
| 2048 | Off | 20.52 | 16.17 | 0 | 0 |
| 2048 | On | 20.19 | 21.28 | 0 | 0 |
| 512 | Off | 22.53 | 16.12 | 0 | 2 |
| 512 | On | 22.98 | 21.96 | 0 | 18 |

Both fits completed in 5.91–6.39 seconds. Every enabled trial reached
the review window without replacing instruments. Extra UI CPU includes the
progress/review modal; the audio process stays close to the matching idle-fit
case. The small-buffer stress run has late callbacks, so these results are
not a claim of perfect callback timing. No gaps or missing frames occurred.

The warning popup adds bounded drawing work over the same Info background:
median CPU milliseconds per frame, 300 frames per trial.

| Window | Popup closed | Popup open |
|---|---:|---:|
| 640x480 | 0.873 | 1.389 |
| 1280x900 | 1.985 | 3.118 |

Across all **192 trials / 60 live runs**: **0 gaps, 0 missing frames, 31 late callbacks**. Ordinary playback and fixed-layout UI
medians show no material regression against v0.2.33 in these workloads.
The batch operation adds analysis/progress cost only while requested.
Short runs on SDL dummy devices do not replace physical-device testing.

```bash
python scripts/benchmark_batch_synthesis.py --candidate . --song PCM_SONG.sidpulse --out ../batch-perf
```
