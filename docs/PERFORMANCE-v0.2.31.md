# v0.2.31 performance and validation

The matched measurements show no material SID-only rendering regression from
v0.2.30. The default 2,048-sample live buffer had no gaps, missing frames, late
callbacks or over-budget blocks in any measured variant. Small-buffer stress
results include scheduling outliers and are reported below, rather than hidden.

## Method

- Immutable baseline: supplied v0.2.30 archive, separately extracted.
- Identical original synthwave demo for baseline/candidate comparisons, without
  changing its automation, instruments, orders or settings.
- Separate candidate PCM-on/off measurements use the same drum-replacement
  project; only the override switches differ. This is a feature-cost check,
  not a claim that disabling samples is an optimization.
- All scopes enabled. Five serial offline/UI repetitions, alternating version
  order. Audio trials render 24 seconds at 48 kHz. UI trials measure 300 frames
  after warm-up, at 1280×900 and 960×1080. Three serial 16-second live trials
  per variant/buffer, after warm-up. No tests, profilers or other heavy jobs
  ran alongside timing trials. CPU affinity is fixed and recorded.
- Linux x86-64, Python 3.12, pygame-ce 2.5.7, pyresidfp 0.17.0, NumPy; exact
  environment, hashes and individual observations are in
  `validation/v0.2.31/performance/environment.json` and `results.jsonl`.
- SDL dummy audio/video measure scheduling and CPU. They do not certify
  physical device latency, audible dropouts, Windows or macOS performance.
  Cached UI figures exclude first import/initial waveform construction.

## Offline audio CPU

Median milliseconds per block, including rendering, output conditioning,
metering, scopes and activity. Budgets are 42.67 ms (2048) and 10.67 ms (512).

| Buffer | v0.2.30 | v0.2.31, same SID song | PCM overrides off | PCM overrides on |
|---|---:|---:|---:|---:|
| 2048 | 6.642 | 6.606 | 6.416 | 6.517 |
| 512 | 1.700 | 1.692 | 1.699 | 1.724 |

SID-only cost is about 0.5% lower, within normal run variation. PCM adds
approximately 1.6% / 1.4% over its own disabled control, respectively.

## UI rendering CPU

Median milliseconds per frame; the 60 Hz budget is 16.67 ms.

| View | Size | v0.2.30 | v0.2.31 |
|---|---|---:|---:|
| Pattern | 1280×900 | 2.780 | 2.787 |
| Pattern | 960×1080 | 2.812 | 2.820 |
| Instrument | 1280×900 | 2.068 | 2.051 |
| Instrument | 960×1080 | 1.710 | 1.707 |
| Info/scopes | 1280×900 | 2.123 | 2.116 |
| Info/scopes | 960×1080 | 2.017 | 2.016 |

Existing views are within roughly 0.3% on the slower side, with other views
slightly faster. The new populated F3 waveform initially cost 1.920 / 2.314 ms
at the two sizes. Profiling found the per-frame 512-line waveform drawing loop.
Caching the raster, while keeping selection and markers live, reduced those
medians to **1.595 / 2.083 ms** (17.0% / 10.0% lower). Matched empty-bank
controls in that final series were 1.199 / 1.319 ms in the candidate and
1.227 / 1.358 ms in the baseline. The new waveform has an explicit measured
cost and remains well inside the frame budget.

Raw before/profile/after data: `waveform-profile-before.txt`,
`performance/results.jsonl`, `waveform-cached-results.jsonl`. This was the only
change to a measured rendering path after the main series; it was measured with
five more alternating repetitions. Its UI/undo tests were rerun.

## Live playback

UI and audio are separate processes. Values are median percentage of one CPU
core. Counter columns sum all three repetitions for each row.

| Buffer / variant | UI CPU % | Audio CPU % | Gaps | Missing frames | Late callbacks | Over-budget blocks |
|---|---:|---:|---:|---:|---:|---:|
| 2048 / baseline | 17.04 | 20.18 | 0 | 0 | 0 | 0 |
| 2048 / candidate SID | 17.39 | 20.12 | 0 | 0 | 0 | 0 |
| 2048 / PCM off | 17.91 | 20.55 | 0 | 0 | 0 | 0 |
| 2048 / PCM on | 17.91 | 21.19 | 0 | 0 | 0 | 0 |
| 512 / baseline | 17.12 | 22.68 | 0 | 0 | 14 | 6 |
| 512 / candidate SID | 16.54 | 22.11 | 0 | 0 | 6 | 2 |
| 512 / PCM off | 17.61 | 22.81 | 1 | 512 | 11 | 5 |
| 512 / PCM on | 17.38 | 23.24 | 0 | 0 | 6 | 2 |

UI pacing was approximately 62 fps in every variant (pygame's millisecond
frame limiter). There were no engine errors. The 512-sample outliers occur
across old/new and enabled/disabled variants, consistent with shared-host
scheduling variation; that is an inference, not proof of a particular cause.
Keep the default 2048 buffer unless the target machine is tested at smaller
sizes. No feature was disabled to obtain the default result.

## Audio preservation and correctness

All eight SID-only fixtures (two songs × two chip models × two clocks) match
exactly in raw PCM, conditioned PCM, SID register writes, clock calls and final
transport state. Native analog lookup tables were initialized once and
inherited by serial validation workers; independent fresh processes initialize
different analog tables, so their PCM hashes are not a valid bit-for-bit test.
The application still uses spawn for its audio/export workers.

Full regression: **1,502 passed**. After final waveform/keyboard/cancellation
work, **205 focused tests passed**, including sample import, packed odd frame
counts, trim bounds, root/pitch, mute/cut, waveform mouse/undo/save, exact WAV
loop lengths, MP3 gapless decoding, failed-output preservation, background
import, and independent C64 decoder interruption. See `regression.txt`.

C64 checks are separate from host performance. The full demo's 6,912 ticks
fit 35,327 bytes of loaded RAM. Music call maximum: 7,892 measured CPU cycles;
conservative combined bound: 17,178 cycles. Sample NMI maximum: 109 cycles,
with a 246-cycle PAL sample interval. The entire PAL/8580 export was emulated
for 195 seconds through its loop; PAL/6581 and both NTSC models ran for 32
seconds. `c64/emulation.json` records signal statistics and hashes. These checks
do not replace physical C64 listening or integration testing.

## Reproduce

```bash
python scripts/benchmark_pcm_release.py --baseline /path/to/v0.2.30/sidpulse-tracker \
  --candidate . --song examples/autumn-at-five-synthwave-mix_v9-pw-sweep.sidpulse \
  --pcm examples/autumn-at-five-synthwave-pcm-drums.sidpulse --out /path/to/fresh-results
python scripts/compare_sid_fingerprints.py --baseline /path/to/v0.2.30/sidpulse-tracker \
  --candidate . --out /path/to/fresh-fingerprints
python -m pytest -q
python scripts/build_pcm_player.py --check
```

The last command needs 64tass only for source/binary verification; normal
exports use the bundled binary. Tests use the optional development dependencies.
