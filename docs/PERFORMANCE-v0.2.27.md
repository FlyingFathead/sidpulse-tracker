# SIDpulse Tracker performance: v0.2.23, v0.2.26 and v0.2.27

## Findings

The regression was mainly UI work. The revised renderer uses substantially less CPU with M/S and scopes still enabled. Audio rendering changes are small compared with trial variation. Bank M/S drawing contributed in the instrument/sample pages; it did not account for the whole regression. The instrument list also paid the cost of comparing the entire song against its saved copy every frame.

Profiling identified repeated full-song equality checks, drawing each individual cell field, rebuilding per-cell mouse rectangles, and drawing the M/S bevels. The changes cache the displayed dirty indicator, composite cell images, button images, stable hit geometry and responsive font fitting. Exact save/quit/autosave checks and live audio scopes are preserved.

## UI drawing CPU time

Milliseconds of CPU per frame, median of five independent process trials; range in parentheses. Each trial warms 32 frames and measures 200 frames. Lower is better. The main comparisons retain enabled features.

### Starter comparison

| View / window | v0.2.23 | v0.2.26 | Change |
|---|---:|---:|---:|
| pattern / 960x1080 | 4.565 (4.433-4.842) | 6.618 (6.388-6.669) | +45.0% |
| instrument / 960x1080 | 2.683 (2.660-2.841) | 4.756 (4.637-5.328) | +77.3% |
| info / 960x1080 | 2.734 (2.582-3.121) | 4.508 (4.320-4.801) | +64.9% |
| pattern / 1280x900 | 4.147 (4.096-4.263) | 5.890 (5.787-5.936) | +42.0% |
| instrument / 1280x900 | 3.044 (2.982-3.124) | 4.268 (4.202-4.381) | +40.2% |
| info / 1280x900 | 2.669 (2.639-2.951) | 4.218 (4.207-4.303) | +58.1% |

### Initial v0.2.27 UI comparison

| View / window | v0.2.26 | v0.2.27 | Reduction |
|---|---:|---:|---:|
| pattern / 960x1080 | 6.613 (6.367-6.883) | 2.964 (2.828-3.000) | 55.2% |
| instrument / 960x1080 | 4.573 (4.517-4.617) | 1.808 (1.805-1.821) | 60.5% |
| info / 960x1080 | 4.469 (4.373-4.636) | 2.050 (2.016-2.075) | 54.1% |
| pattern / 1280x900 | 5.871 (5.849-5.974) | 2.972 (2.897-2.985) | 49.4% |
| instrument / 1280x900 | 4.267 (4.238-4.446) | 2.265 (2.182-2.297) | 46.9% |
| info / 1280x900 | 4.208 (4.119-4.263) | 2.134 (2.107-2.174) | 49.3% |

These are serial comparison batches on the same host. The final UI batch includes channel recording and centered scrolling; v0.2.26 was rerun alongside it. The v0.2.27 median is also below the starter median in all six tested view/window cases. Drawing CPU is not total application CPU. Multiply ms/frame by six to estimate one-core utilization at exactly 60 frames/second, before event handling and audio synchronization.

## M/S button isolation

Instrument/sample views at 960x1080, five trials of 400 measured frames each. v0.2.26 has no off setting, so the experiment suppresses only its bank-button drawing method. v0.2.27 uses its actual display preference. These are renderer-only trials, with no instrument actively muted/soloed.

| Version / view | Buttons enabled, ms/frame | Buttons disabled, ms/frame | Enabled minus disabled |
|---|---:|---:|---:|
| 0.2.26 / instrument | 4.655 (4.530-4.754) | 3.294 (3.270-3.478) | 1.361 ms |
| 0.2.26 / samples | 4.529 (4.370-4.588) | 2.830 (2.770-2.992) | 1.699 ms |
| 0.2.27 / instrument | 1.831 (1.818-1.936) | 1.747 (1.723-1.780) | 0.083 ms |
| 0.2.27 / samples | 1.376 (1.353-1.400) | 1.302 (1.248-1.452) | 0.074 ms |

## Native audio processing

Median CPU ms per block (five trials). Each trial warms 16 blocks after SID startup, then renders about 10 seconds at 48 kHz. 2048 frames provide a 42.667 ms block budget; 512 provide 10.667 ms. This includes the sequencer, native SID, output conditioning, meters, activity snapshots and enabled scope snapshots.

| Common workload | v0.2.23 | v0.2.26 in starter batch | v0.2.26 rerun | v0.2.27 |
|---|---:|---:|---:|---:|
| v5-common-2048-scopes-0 | 2.919 | 2.905 | 2.760 | 2.753 |
| v5-common-2048-scopes-1 | 6.436 | 6.526 | 6.419 | 6.438 |
| v5-common-512-scopes-0 | 0.713 | 0.716 | 0.711 | 0.723 |
| v5-common-512-scopes-1 | 1.731 | 1.699 | 1.697 | 1.694 |
| first-light-2048-scopes-0 | 2.859 | 2.849 | 2.812 | 2.807 |
| first-light-2048-scopes-1 | 6.569 | 6.523 | 6.596 | 6.542 |

| Unmodified v5, row automation enabled | v0.2.26 | v0.2.27 |
|---|---:|---:|
| 2048 frames, scopes off | 2.787 | 2.728 |
| 2048 frames, scopes on | 6.505 | 6.492 |

The unmodified sweep changes native chip work as well as executing automation, so this is a representative workload comparison, not a pure isolated cost per PW command. Differences of a few percent here are not evidence of an audio speedup or slowdown. Scopes remain the larger optional audio cost: they run three display-only native SID copies. Turning off Channel visualizers stops that processing.

## Live UI plus audio worker

960x1080, 15 measured seconds per case after warmup. CPU percentages are fractions of one logical core, separately for UI/main and the complete audio process. They are not the in-app render-budget percentage. The UI targets 60 Hz; Pygame integer clock timing achieved approximately 62 Hz on this host.

| Version / case | UI CPU | Audio process CPU | FPS | Gaps | Missing frames | Late callbacks | Over-budget blocks |
|---|---:|---:|---:|---:|---:|---:|---:|
| 0.2.23 / v5-common-pattern-2048 | 31.9% | 11.6% | 62.1 | 0 | 0 | 0 | 0 |
| 0.2.23 / v5-common-info-2048 | 20.3% | 20.2% | 62.0 | 0 | 0 | 0 | 0 |
| 0.2.23 / v5-common-info-512 | 20.2% | 22.0% | 62.1 | 0 | 0 | 0 | 0 |
| 0.2.26 / v5-common-pattern-2048 | 45.3% | 11.4% | 62.1 | 0 | 0 | 0 | 0 |
| 0.2.27 / v5-common-pattern-2048 | 22.1% | 11.3% | 62.2 | 0 | 0 | 0 | 0 |
| 0.2.26 / v5-common-info-2048 | 32.6% | 20.6% | 62.1 | 0 | 0 | 0 | 0 |
| 0.2.27 / v5-common-info-2048 | 17.6% | 20.6% | 62.1 | 0 | 0 | 0 | 0 |
| 0.2.26 / v5-common-info-512 | 32.7% | 22.5% | 62.2 | 0 | 0 | 0 | 0 |
| 0.2.27 / v5-common-info-512 | 17.3% | 23.1% | 62.0 | 0 | 0 | 0 | 0 |
| 0.2.27 / v5-automation-info-scopes-1 | 17.3% | 20.5% | 62.1 | 0 | 0 | 0 | 0 |
| 0.2.27 / v5-automation-info-scopes-0 | 17.4% | 12.7% | 61.8 | 0 | 0 | 0 | 0 |

### Follow-up on 512-frame scheduling

One interim optimization run recorded late callbacks without missing frames, so the same case was repeated twice per version, with alternating version order. These follow-up measurements are retained, including any lateness; no failed samples were discarded.

| Version / repeat | UI CPU | Audio process CPU | Gaps | Missing frames | Late callbacks | Over-budget blocks |
|---|---:|---:|---:|---:|---:|---:|
| 0.2.26 / 1 | 33.5% | 23.6% | 0 | 0 | 4 | 4 |
| 0.2.27 / 1 | 16.6% | 22.3% | 0 | 0 | 0 | 0 |
| 0.2.27 / 2 | 17.3% | 22.9% | 0 | 0 | 2 | 3 |
| 0.2.26 / 2 | 31.6% | 22.7% | 0 | 0 | 0 | 0 |

Shared-host scheduling and SDL dummy callbacks are not a hardware latency guarantee. Use the retained counters to distinguish a late callback from lost audio frames. Test the actual output device on the target machine before reducing its audio buffer.

## Method and limits

- Linux x86_64; Python 3.12.14, pygame-ce 2.5.7, pyresidfp 0.17.0. SDL dummy audio/video, native reSIDfp enabled. Timed trials are serial. Offline/UI trials are pinned to CPU 0; live main/worker are allowed CPUs 0 and 1. No test suite or profiler ran alongside the timings.
- Baselines are immutable release trees: v0.2.23 (`c339922`) and v0.2.26 (`bffa1af`). The main final batch uses the delivered renderer, channel recorder and centered-list layout. A final two-line sample-wheel input handler was added afterward and covered by input tests and a further matched scrolling batch. Offline audio results come from the earlier optimization batch; all audio, SID and sequencer source files were verified identical to the delivered files. Version order alternates by trial. Detailed raw stage timings, ranges, counters and environment are included under `validation/v0.2.27/performance/`.
- Input is `autumn-at-five-synthwave-mix_v5-pw-sweep.sidpulse`, with 224 PW commands and no ADSR row commands. The common workload is a temporary format-6 copy with only row A/D/S/R/PW fields removed. All versions therefore receive the same common data. The original v5 file is also exercised unchanged on current versions. `first-light.sidpulse` provides a second audio workload.
- GUI timing uses a deterministic active playback snapshot, synthetic scope data and advancing rows of the first pattern. Live timing runs the actual song and worker. Each version uses its default responsive layout, so the newer views include more fields than v0.2.23. The results cover these workloads and sizes, not every song, dialog, graphics driver or machine.
- Profiling is separate from timing. Cached rendering is verified against direct drawing, and undo/save/monitor behavior has regression coverage. The v5 input was not modified.
- Two expected GUI records were absent when the final main batch exited. Those two trials were measured again and appended, with explicit notes in the raw data. No existing measurements were replaced or discarded. The completed main batch contains 144 records; the final scrolling follow-up contains 20.

Input SHA-256: `f07f88f4283ce02f6c8d2d5c1cf07e2ed3c6756af992c9073a014f4fc89c7b33`.

Reproduce with `scripts/benchmark_releases.py`; see `docs/PERFORMANCE.md`.

## Recording and scrolling in the final build

These checks exercise the final channel-recording UI and changing selections, beyond a static instrument page.

| Workload | v0.2.26 ms/frame | v0.2.27 ms/frame |
|---|---:|---:|
| Scrolling instrument, 960x1080 | 4.249 (4.190-4.355) | 1.446 (1.438-1.542) |
| Scrolling samples, 960x1080 | 4.467 (4.418-4.615) | 1.361 (1.350-1.445) |
| Armed Record automation view, 960x1080 | Not available | 2.957 (2.913-2.991) |

Live PW dragging to channel 2 for 15.0s: UI CPU 23.1%, audio process CPU 11.7%, 61.9 FPS, 0 gaps, 0 missing frames, 0 late callbacks, 0 over-budget blocks. The harness varied the slider every frame and began a new touch after each pattern pass; 3 takes were committed during the measured run including warmup, with 4 rows in the last capture.

## Inline recorder and v8 follow-up

The initial sections above preserve the earlier v5 measurements. This follow-up
compares the initially delivered v0.2.27 (`fbe9017`) against the inline recorder
revision on the unchanged v8 input. All runtime hashes and 75 raw records are
under `validation/v0.2.27/inline-revision/`. Both versions keep M/S and scopes
enabled. Three serial trials alternate the version order; no tests, export
analysis or profilers ran alongside measured trials. The environment remains
Linux x86_64, Python 3.12.14, pygame-ce 2.5.7 and pyresidfp 0.17.0, SDL dummy.

### Intermediate UI CPU milliseconds per frame

Median and range across three fresh processes, 400 measured frames each,
at 960x1080. The recording comparison is old popup versus new inline pane.

| View | Previous v0.2.27 | Revised v0.2.27 | Median change |
|---|---:|---:|---:|
| pattern | 3.027 (2.932-3.091) | 2.909 (2.870-3.025) | -3.9% |
| instrument | 1.828 (1.805-1.908) | 1.918 (1.798-1.986) | +4.9% |
| info | 2.044 (2.032-2.201) | 2.211 (2.006-2.347) | +8.2% |
| samples | 1.361 (1.337-1.379) | 1.350 (1.343-1.379) | -0.8% |
| scroll-instrument | 1.441 (1.423-1.515) | 1.450 (1.441-1.520) | +0.6% |
| scroll-samples | 1.364 (1.356-1.554) | 1.388 (1.350-1.437) | +1.7% |
| record-pw | 2.932 (2.897-3.141) | 1.634 (1.561-1.805) | -44.3% |

### Native audio CPU milliseconds per block

The 2048-frame case renders 200 seconds, covering the full 189.89-second
v8 arrangement and the start of its next loop. The 512-frame case renders
15 seconds. This includes conditioning, meters, activity and scope snapshots.

| Case | Previous v0.2.27 | Revised v0.2.27 | Median change |
|---|---:|---:|---:|
| v8-2048-200s | 6.592 (6.567-6.625) | 6.546 (6.538-6.670) | -0.7% |
| v8-512-15s | 1.720 (1.698-1.742) | 1.726 (1.699-1.747) | +0.4% |

### Live playback and recording

Each trial measures 15 seconds after warmup. CPU is the median percentage
of one logical core, reported separately for UI/main and audio worker.
Counters are totals across all three trials, including late callbacks.

| Case | Version | UI CPU | Audio CPU | Gaps | Missing frames | Late callbacks | Over-budget blocks |
|---|---|---:|---:|---:|---:|---:|---:|
| info-2048 | baseline | 17.5% | 20.6% | 0 | 0 | 0 | 0 |
| info-2048 | candidate | 17.0% | 20.1% | 0 | 0 | 0 | 0 |
| info-512 | baseline | 17.1% | 22.2% | 0 | 0 | 5 | 5 |
| info-512 | candidate | 17.2% | 22.7% | 0 | 0 | 4 | 3 |
| instrument-2048-record-pw | baseline | 24.0% | 21.1% | 0 | 0 | 0 | 0 |
| instrument-2048-record-pw | candidate | 16.0% | 21.7% | 0 | 0 | 0 | 0 |
| instrument-2048-record-attack | candidate | 14.6% | 20.7% | 0 | 0 | 0 | 0 |

The prior version has no ADSR recording, so the attack case is candidate-only.
Physical output devices, Windows scheduling and C64 hardware remain outside
these measurements. Trial ranges distinguish noise from persistent changes;
these results are not a guarantee for every machine or workload.

SQUEEZER v2.0 saves 1,165 bytes on v8 (about 4.3%) while preserving the
selected decoder and measured maximum replay cycles. Its added search costs
about four seconds of host export analysis. First Light retains its original
encoding; Autumn at Five examples save 45-49 bytes. See the complete
[A/B export table](../validation/v0.2.27/inline-revision/SQUEEZER-AB.md).

### Final UI revision: measured after button caching

This is the delivered UI comparison: five alternating-order trials, 400 frames
per process, the same v8 source, 960x1080 and default features enabled.
The first three-trial batch above is retained as intermediate evidence.

| View | Previous v0.2.27 ms/frame | Delivered revision ms/frame | Median change |
|---|---:|---:|---:|
| pattern | 2.943 (2.864–2.994) | 2.814 (2.752–2.893) | -4.4% |
| instrument | 1.830 (1.801–1.940) | 1.651 (1.640–1.736) | -9.8% |
| info | 2.034 (2.027–2.049) | 1.989 (1.975–2.017) | -2.2% |
| samples | 1.353 (1.341–1.393) | 1.332 (1.316–1.344) | -1.5% |
| scroll-instrument | 1.448 (1.435–1.455) | 1.360 (1.322–1.396) | -6.1% |
| scroll-samples | 1.365 (1.358–1.428) | 1.353 (1.322–1.359) | -0.9% |
| record-pw | 2.917 (2.891–3.063) | 1.348 (1.324–1.410) | -53.8% |

Values show median (minimum–maximum). The instrument view is 9.8% cheaper
to draw; scrolling instruments is 6.1% cheaper. The new inline PW recorder
costs 53.8% less UI CPU per frame than the old popup. These are render CPU
measurements, not percentages of total system CPU.

The initial Info-page increase did not persist in a five-trial follow-up
(2.047 to 2.030 ms/frame). Its drawing code and call counts were unchanged.
Profiling the instrument view identified repeat button bevel/text work.
The final bounded 128-image cache removes that work, including correct
bevel overdraw and live hit geometry. Pixel comparisons cover both themes,
small/half-HD windows, pressed states, colors and zoom invalidation.

A final live check used the delivered UI at both 2048 and 512 frames, plus
PW and attack recording. All seven cases had zero gaps, missing frames,
late callbacks and over-budget blocks. This is one additional trial per
case; the earlier three-trial counters above still apply, including its
occasional 512-frame lateness. PW-recording UI CPU was 25.5% versus 15.1%
of one logical core; audio-worker CPU was 21.9% versus 21.5%.

Final raw data: `inline-revision/final-ui/` and `final-live/`; intermediate
zoom follow-up: `interim-zoom-ui/`. There are 222 timing records across the
four revision batches. `runtime-buttons-sha256.json` identifies delivered
runtime files. Only the two UI drawing modules changed after the native
PCM comparison; audio, sequencer and exporter files match that snapshot.

### Native sound preservation

Baseline and revised playback produce identical raw PCM, conditioned PCM,
ordered SID writes/clocks and final sequencer state. The unchanged v8 runs
for 200 seconds, covering its full arrangement and a loop restart; each
of the four bundled examples runs for 12 seconds. Irregular render blocks
are 1, 17, 1024, 2048, 3, 256, 8192 and 512 frames. Hashes are under
`inline-revision/native-pcm/`. The comparison forks an initialized native
emulator solely to ensure identical starting tables. Production workers
still use spawn. Reproduce using `scripts/compare_native_pcm.py` with
`--baseline`, `--candidate`, `--input` and a fresh `--out` directory.

Final packaging removed one trailing blank line from the retained popup module.
Its parsed syntax tree is identical to the tested version.
`runtime-delivered-sha256.json` records this whitespace-only difference from
`runtime-buttons-sha256.json`; no executable behavior changed after the gates.
