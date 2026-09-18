# SIDpulse Tracker 0.2.22: performance and regression evidence

Date: 2026-09-18. Baseline: the supplied, unmodified **0.2.21** archive.

## Result

The candidate isolates the existing audio worker and SDL callback in a spawned process, and reduces Python work in PCM handling. The default remains 2048 samples at 48 kHz, with the same two-block reserve. No audio-quality reduction or increased buffering was used to obtain these results.

The baseline passed **1023 tests**; the candidate passed **1051 tests**, with **zero failures, errors or skips** in each run. Across the seven candidate real-time scenarios (168 measured seconds), there were **zero software starvation episodes, zero missing PCM frames and zero callback intervals above 1.5 blocks**. This is a bounded Linux/SDL-dummy test result, not a guarantee for every device or operating system.

## Reproduced scheduling failure

The baseline already uses a render thread. However, its SDL callback needs Python’s GIL, and the pinned pyresidfp 0.17.0 clock binding does not release that GIL. More threads or asyncio alone do not isolate audio from GIL-holding UI/native operations.

A controlled native call holds the UI process GIL for 100 ms approximately every 350 ms. This is a synthetic scheduling probe, not a claim that the user’s exact real-world glitch was reproduced. In the baseline, PCM remains queued while the callback itself is delayed. The old empty-queue counter therefore reports zero gaps despite severe timing failures.

| Controlled GIL-stall test | 0.2.21 | 0.2.22 candidate |
|---|---:|---:|
| Measured duration | 12 s | 30 s |
| Longest callback interval | 140.48 ms | 44.22 ms |
| Intervals above 1.5 blocks (64 ms) | 34 | 0 |
| Empty-queue gap count | 0 | 0 |

A separate baseline experiment also ran the unmodified engine in another process: its worst callback interval was 47.79 ms and there were zero intervals above 64 ms during the same 12-second stress. This isolates the benefit of process separation from the PCM-loop optimizations.

Commands now incur IPC scheduling, and display telemetry refreshes at up to 60 Hz. The unchanged PCM reserve does not imply that end-to-end keyboard-to-speaker latency was measured here.

## Render throughput

Each row renders 30 seconds of a bundled song without an audio device or UI; native SID initialization and power-up settling are outside the timed region. Times include sequencer/native rendering, host conditioning, metering and scope snapshots where enabled. This measures producer throughput, independently of callback scheduling. These are one-pass measurements on this host, not universal speedup guarantees.

| Song | Block | Scopes | Baseline mean | Candidate mean | Less render time |
|---|---:|:---:|---:|---:|---:|
| first-light | 512 | off | 1.044 ms | 0.785 ms | 24.8% |
| first-light | 512 | on | 2.077 ms | 1.767 ms | 14.9% |
| first-light | 2048 | off | 3.732 ms | 2.959 ms | 20.7% |
| first-light | 2048 | on | 7.836 ms | 7.088 ms | 9.5% |
| autumn-at-five | 512 | off | 0.972 ms | 0.832 ms | 14.4% |
| autumn-at-five | 512 | on | 2.023 ms | 1.920 ms | 5.1% |
| autumn-at-five | 2048 | off | 3.844 ms | 3.196 ms | 16.9% |
| autumn-at-five | 2048 | on | 7.682 ms | 7.299 ms | 5.0% |

A 2048-sample block has a 42.667 ms production budget. All four default-buffer rows had zero over-budget blocks in both versions. At 512 samples (10.667 ms), Autumn at five with scopes had one over-budget block in each version; this is disclosed rather than presenting the small-buffer run as universally clean. An over-budget producer block is not automatically a device underrun because queued reserve can absorb it.

The Info page enables three extra display-only SID emulators. Those scopes and the native sampling mode are preserved. Their cost remains visible in the measurements.

## Real-time candidate scenarios

All tests below use the default 2048-frame buffer and real native SID synthesis, with SDL’s dummy audio driver. UI scenarios run the actual pygame renderer at a nominal 60 FPS. No CPU-heavy benchmark/test suite ran concurrently with these measurements.

| Scenario | Time | PCM gaps | Missing frames | Late callbacks | Worst interval |
|---|---:|---:|---:|---:|---:|
| idle_no_scopes | 12 s | 0 | 0 | 0 | 44.34 ms |
| idle_scopes | 12 s | 0 | 0 | 0 | 43.33 ms |
| ui_pattern | 12 s | 0 | 0 | 0 | 42.58 ms |
| ui_info | 12 s | 0 | 0 | 0 | 45.38 ms |
| cpu | 30 s | 0 | 0 | 0 | 47.51 ms |
| gil_hold | 30 s | 0 | 0 | 0 | 44.22 ms |
| ui_churn | 60 s | 0 | 0 | 0 | 48.29 ms |

`ui_churn` alternates Info/pattern pages every 25 UI frames, resizes every 60 frames, and enters a live note every 30 frames. `cpu` runs continuous Python arithmetic in the UI process. `gil_hold` injects the controlled 100 ms GIL holds described above. Baseline comparison measurements are supplied for every scenario.

Callback lateness is defined explicitly as an interval above 1.5 nominal blocks, not every small departure from 42.667 ms. It is a scheduling diagnostic, not a hardware xrun measurement. The dummy driver’s timer behavior does not reproduce WASAPI, ALSA, PipeWire, PulseAudio or physical device scheduling. Baseline callback timestamps are captured by an external wrapper; candidate timing comes from the same threshold inside the isolated audio process and is returned in telemetry. Counter reset/measurement windows include approximately 0.1 s of settling.

## Numerical and regression checks

- **4,608,000 PCM frames matched exactly**: two bundled songs × both 6581/8580 models × PAL/NTSC × 12 seconds at 48 kHz, with irregular buffer partitions. Both raw PCM and conditioned PCM SHA-256 hashes match; ordered SID-write/cycle-call hashes and final transport state also match.
- The comparison warms the native emulator once, then runs both source trees from identical native starting state in isolated Linux test processes. Fresh native process starts can have different analog dither/table state, so unrelated fresh-start PCM hashes are not used as an equivalence oracle. The test-only fork happens before SDL or Python worker threads; production playback always uses spawn.
- The optimized conditioner also matches the unmodified 0.2.21 recurrence bit for bit for random/extreme/DC samples, fades, clipping and eight block sizes. A separate FIFO test verifies that samples generated during SID gate-cycle calls are preserved across uneven reads and reset.
- A negative-control test deliberately stalls native rendering for 250 ms while the real SDL dummy callback drains the queue; the detector must report missing frames and a starvation episode. A full-queue delayed-callback test verifies the independent late counter. Recovery, resets and starvation episodes are covered.
- Existing tests cover native synthesis, instrument activity, audition, playback/pause/restart, buffer changes, mute, keyboard routing, file workflows, export analysis, C64 replay verification, squeezer encodings and recovery. New tests cover process lifecycle/no orphan, the Alt+F12 binding, persisted true/false settings, staged cancellation, small-window layout and nonmodal warning behavior.

| Suite | Tests | Failures | Errors | Skips | Elapsed |
|---|---:|---:|---:|---:|---:|
| Unchanged 0.2.21 | 1023 | 0 | 0 | 0 | 180.16 s |
| 0.2.22 candidate | 1051 | 0 | 0 | 0 | 173.44 s |

The supplied baseline archive files were compared byte for byte after the tests and remained unchanged. C64 compiler/player source and existing player binaries are unchanged in the candidate. No Windows execution, physical audio loopback, VICE/real-C64 check, or assembler rebuild was performed here. These remain separate release checks. Passing tests establish the stated coverage; they do not prove absence of every possible regression.

Both headless application startup checks also passed (First light and immediate welcome-song playback). A final focused run after the last renderer edits passed 68 tests. The explicit 6-second `--assert-clean` negative control returned exit 1 for the baseline (17 late intervals) and exit 0 for the candidate (zero late intervals); its JSON records are included.

The first full candidate pass exposed two startup-adapter cases with no telemetry fields yet. The warning path now handles that state; the full suite above is the successful rerun after the correction.

## User-visible controls

Alt+F12 opens audio settings. **Detect audio underruns / warn** defaults to ON and saves `audio_underrun_detection: true` or `false` in machine preferences. Off suppresses live detection notifications; raw telemetry remains available to Info and tests. A small reddish lower-left footer message expires after 12 seconds and never steals focus, opens a popup or overwrites editor status. Queue underruns and late callbacks have distinct wording. OK saves both options atomically; Cancel preserves existing settings.

## Reproduce

Use the project’s pinned runtime dependencies plus its development dependencies. From each source checkout, run the same command and keep separate output filenames:

```bash
python -m pytest -q -ra --junitxml=audio-regressions.xml
python scripts/benchmark_audio.py --repo . --mode offline --seconds 30 --output audio-throughput.json
python scripts/benchmark_audio.py --repo . --mode realtime --kind ui_churn --seconds 120 --frames 2048 --assert-clean --output audio-ui-stress.json
python scripts/benchmark_audio.py --repo . --mode realtime --kind gil_hold --seconds 30 --frames 2048 --assert-clean --output audio-gil-stress.json
```

For baseline comparisons, run the candidate benchmark script with `--repo` pointing at the untouched 0.2.21 checkout. `--assert-clean` writes the measurements and returns nonzero for PCM starvation, late callbacks or audio errors; the baseline synthetic GIL-stall test is expected to fail this gate. The scripts default to dummy SDL drivers unless driver environment variables are supplied explicitly. The GIL-stall helper supports Linux/POSIX and Windows, but only Linux was executed here.

Linux identical-state native comparison:

```bash
python scripts/compare_pcm.py --baseline ../baseline/sidpulse-tracker --candidate . --output-dir ./comparison-results
```

Create the output directory first. This numerical comparison does not open an audio device.

## Environment and raw evidence

Linux x86-64 VM; AMD EPYC 9V74 virtual CPU; 9 visible CPUs with an 8-CPU quota. CPython 3.12.14, pygame-ce 2.5.7 / SDL 2.32.10, pyresidfp 0.17.0, py65 1.2.0. The timings are local wall-clock measurements; sustained real-device playback was not audible or observable in this environment.

Source archive SHA-256: `e6647fbb1457a912cf24de8e7d15cc36a5b347aaaef8234b7c371357d8bf3efb`.

Raw JSON measurements, PCM fingerprints, JUnit reports and the evidence checksum manifest are in `docs/audio-performance-v0.2.22/`. The benchmark and comparison scripts are in `scripts/`.

Primary technical references: [Python threading/GIL documentation](https://docs.python.org/3/library/threading.html), [pyresidfp upstream](https://github.com/pyresidfp/pyresidfp), and [SDL queued-audio documentation](https://wiki.libsdl.org/SDL2/SDL_QueueAudio). SDL native queued output is a potential further architecture option; this change retains the existing continuous callback inside the isolated process.
