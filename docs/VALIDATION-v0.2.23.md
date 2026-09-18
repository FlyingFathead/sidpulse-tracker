# SIDpulse Tracker v0.2.23 validation

## Outcome and scope

The final candidate passes **1084 tests**, zero failures, errors or skips
(181.88 seconds). Both headless launch/playback smoke checks pass.
The same 0.2.22 and 0.2.23 default-buffer workloads report zero PCM starvation,
missing frames and callback intervals above 1.5 blocks. Median mean block-render
times show no material throughput regression in these runs. This is evidence
for the measured configurations, not a guarantee of zero glitches on all hosts.

The feature adds named output selection, a temporary C-E-G-C diagnostic test,
refresh and staged reset defaults. Device names are persisted only after a
successful apply; missing saved devices fall back to system default. Linux and
Windows use the same pygame/SDL APIs. **Native Windows execution and physical
Linux/Windows output routing were not tested in this environment.**

## Environment and baseline

- Baseline: the preserved 0.2.22 source used for the preceding release.
- Candidate: 0.2.23, Python 3.12.14, pygame-ce 2.5.7, pyresidfp 0.17.0.
- Linux x86_64, 9 visible CPUs, SDL dummy audio/video. Same interpreter, host,
  demo projects, 48 kHz mono output, two-block reserve and 2048-sample default.
- Benchmarks ran serially, after the first regression suite. Offline runs used
  three repetitions per version with alternating version order. Render costs
  include SID, conditioner, meter and optional scope snapshot work.
- No runtime dependencies, native format (6), SID renderer, voice engine,
  sequencer, output conditioner, export sources or player binaries changed.
- Source SHA256 and raw measurements accompany this report. Absolute machine
  paths in test output are replaced by neutral placeholders.

## Regression evidence and the baseline test race

The original 0.2.22 suite returned **1050 passed / 1 failed** on this rerun.
The failure was `test_three_notes_f5_and_repeated_restart_do_not_freeze`; the
same original test also failed when run alone. Its assertion required observing
`playing` with fewer than 5000 generated samples immediately after F5. The worker
primes a two-block reserve and publishes snapshots at 60 Hz, so a valid restart
can pass that small window before the test sees it. The reported failure showed
continuing playback rather than a stalled worker.

The corrected check waits until at least 24000 samples have elapsed and then
requires an observable rewind after each restart, retaining the stopped-to-playing
check for the first start. It does not change production transport behavior or
extend the existing timeouts. **The corrected 15-restart check passes against
unchanged 0.2.22 application code**, and the complete candidate suite passes.
Original failure output and the corrected baseline result are both included.

The 33 added device checks cover strict/migrated/Unicode preferences, playback-only
enumeration, stale and busy devices, restoration of exact unconsumed PCM, paused
state, retained counters, test pitch/level/fades/duration, real diagnostic-tone
starvation accounting, config-save errors, cancel during apply, reset/cancel/save,
mouse/keyboard selection, refresh and resized controls. Real spawned SDL tests
exercise named output opening, song time held during a test, auto-return and
manual stop, failed switching, config reload and shutdown during a tone.

The dialog and picker were visually checked at 1280x900 and 480x360. Screenshots
use explicitly supplied UI fixture device names; they are not a hardware inventory.

## Matched real-time checks

Five scenarios, **60 seconds per version / 120 seconds combined**, all with
`--assert-clean` and 2048 samples. A late interval is greater than 64 ms.
CPU uses busy Python arithmetic; GIL hold blocks the UI interpreter for 100 ms
periodically; UI churn changes pages, resizes and edits notes during playback.

| Scenario | Duration | 0.2.22 max callback interval | 0.2.23 max callback interval | Missing frames / late intervals (both versions) |
|---|---:|---:|---:|---:|
| idle_no_scopes | 12 s each | 49.89 ms | 43.38 ms | 0 / 0 |
| idle_scopes | 12 s each | 43.87 ms | 47.79 ms | 0 / 0 |
| cpu | 12 s each | 42.55 ms | 44.27 ms | 0 / 0 |
| gil_hold | 12 s each | 45.10 ms | 43.27 ms | 0 / 0 |
| ui_churn | 12 s each | 44.43 ms | 46.96 ms | 0 / 0 |

Startup, explicit pauses and output-open transitions are not counted as ordinary
playback underruns. A deliberate test or device change can briefly interrupt
output while SDL closes/reopens it. This feature does not claim gapless routing.

## Matched offline render cost

Median of the mean block time from three 8-audio-second runs per case; milliseconds.
Negative change means lower measured time. These small differences should not be
advertised as a new speed optimization: the synthesis/conditioning path is unchanged.

| Song | Samples | Scopes | 0.2.22 ms | 0.2.23 ms | Change |
|---|---:|---|---:|---:|---:|
| first-light | 512 | off | 0.777 | 0.785 | +1.05% |
| first-light | 512 | on | 2.017 | 1.881 | -6.77% |
| first-light | 2048 | off | 3.120 | 3.021 | -3.17% |
| first-light | 2048 | on | 7.366 | 7.182 | -2.50% |
| autumn-at-five | 512 | off | 0.795 | 0.771 | -3.02% |
| autumn-at-five | 512 | on | 1.839 | 1.810 | -1.55% |
| autumn-at-five | 2048 | off | 3.055 | 3.016 | -1.28% |
| autumn-at-five | 2048 | on | 6.936 | 6.852 | -1.21% |

At the default 2048 samples all measured blocks remained within the 42.67 ms
budget. At 512 samples, one candidate first-light/scopes-off block in repetition 3
measured 14.04 ms, beyond its 10.67 ms budget; baseline repetitions had no such
block. That case's median mean changed by +1.05%. The slow block occurred in the
unchanged native-render path; these data do not establish its cause. We retain
the outlier and do not claim that small buffers are immune to scheduling jitter.

## Numerical sound and export preservation

Across two songs x two SID models x PAL/NTSC, **4,608,000 frames** are bit-identical
between versions from matched native initial state. Raw PCM, conditioned PCM,
ordered SID write/cycle hashes and final sequencer state all match in eight cases.
The numerical harness warms native tables once and forks isolated render jobs
before creating SDL/Python audio threads; this is Linux-only analysis. Production
playback continues to use spawn on both platforms. The unchanged renderer,
conditioner, sequencer and voice-engine source hashes are recorded below.

Native project format, export source and existing player binary assets are
byte-for-byte unchanged. The complete regression suite includes exporter and
6502 replay tests; no VICE/physical C64/Windows or assembler rebuild is claimed.

## Reproduction

From the candidate checkout, with a separate 0.2.22 checkout available:

```bash
./.venv/bin/python -m pytest -q --junitxml=candidate-tests.xml
./.venv/bin/python -m sidpulse --headless-smoke --example
./.venv/bin/python -m sidpulse --headless-smoke --play-welcome-song
./.venv/bin/python scripts/benchmark_audio.py --repo . --mode realtime \
  --kind gil_hold --seconds 12 --frames 2048 --assert-clean --output candidate-gil_hold.json
./.venv/bin/python scripts/benchmark_audio.py --repo ../baseline-0.2.22 --mode realtime \
  --kind gil_hold --seconds 12 --frames 2048 --assert-clean --output baseline-gil_hold.json
./.venv/bin/python scripts/benchmark_audio.py --repo . --mode offline \
  --seconds 8 --output candidate-offline.json
mkdir -p pcm-comparison
./.venv/bin/python scripts/compare_pcm.py --baseline ../baseline-0.2.22 \
  --candidate . --output-dir pcm-comparison
```

Repeat real-time runs with `idle_no_scopes`, `idle_scopes`, `cpu`, and `ui_churn`.
Repeat offline runs three times per version with alternating order. The benchmark
uses SDL dummy unless the environment explicitly selects another driver. Physical
routing validation still requires listening to two actual outputs, saving and
restarting, testing while paused/playing, and checking disconnect/reconnect behavior
on Linux and Windows. Refresh discovers connected outputs; seamless hot-unplug
recovery during ordinary playback is not promised.

API basis: [SDL named/default output](https://wiki.libsdl.org/SDL2/SDL_OpenAudioDevice)
and [output enumeration](https://wiki.libsdl.org/SDL2/SDL_GetAudioDeviceName).

## Unchanged sound-path SHA256

- `sidpulse/sid/backend_residfp.py`: `256b6df0ce868108ad95af56aa54f60ae6bb634baef3bfd84095a07b1598437d`
- `sidpulse/audio/output.py`: `cc24184020e6747e539bb25e0543c3fb2ea60e0505d002dea94425ac4e258b5d`
- `sidpulse/playback/sequencer.py`: `b7b9edb1be2160be17cdadcbc44af71e5a55a204faba3925ed52580cd91cb45f`
- `sidpulse/playback/voices.py`: `b2919562e569c08d3c885df8afd72de5ea4cc3032b64a6e94072468a4e86f7a5`

Raw evidence: [audio-validation-v0.2.23](audio-validation-v0.2.23/).
