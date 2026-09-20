# v0.2.32 performance and validation

The final 108 matched trials found no material app runtime regression in the
measured workloads. Default-buffer audio medians changed by +1.1% for SID and
-1.6% for PCM. Pattern drawing changed by -0.2% at 1280×900 and +2.7% at
960×1080. The mapped-sample F4 view is faster. All 30 final live trials had
**zero audio gaps and zero missing frames**. Default-buffer trials also had
zero late callbacks and zero over-budget blocks, including during PCM export
analysis. Small-buffer scheduling outliers are recorded below.

## Final method and limits

The immutable baseline is the separately extracted v0.2.31 full ZIP. Both
versions load identical, unmodified SID and PCM demo files from `examples/`.
All scopes stay enabled; the candidate includes the final AR column, Select
all, header navigation, F4 clipboard and mapped-instrument changes. Three
serial repetitions alternate version order: 20 seconds of offline audio at
each buffer; 900 warmed UI frames at each window size. Three 12-second live
repetitions per song/buffer/version, plus three per version with default-buffer
PCM export analysis active, measure UI and audio process CPU separately.
No tests, profilers or other heavy jobs ran alongside measured trials.

Environment: Linux x86-64, Python 3.12.14, pygame-ce 2.5.7, pyresidfp 0.17.0,
NumPy 2.3.5. Offline/UI workers use CPU 0; live workers use CPUs 0–1.
`validation/v0.2.32/final-performance/environment.json` records versions and
input hashes; `results.jsonl` preserves all 108 trials. Source songs were
checked unchanged. SDL dummy audio/video measure CPU and scheduling, not
physical device behavior or Windows/macOS performance. UI figures exclude
first import and initial waveform construction. Short shared-host trials
cannot promise an absence of dropouts on every machine.

## Final offline audio CPU

Median milliseconds per block, including render, conditioning, meters,
scopes and activity. Budgets are 42.67 ms (2048) and 10.67 ms (512).

| Song | Buffer | v0.2.31 | v0.2.32 | Change |
|---|---|---|---|---|
| SID | 2048 | 6.419 | 6.491 | +1.1% |
| PCM | 2048 | 6.605 | 6.501 | -1.6% |
| SID | 512 | 1.711 | 1.704 | -0.4% |
| PCM | 512 | 1.748 | 1.782 | +1.9% |

Initialized native audio comparisons are exact for raw/conditioned PCM, SID
register writes/cycles and final playback state across seven songs, including
200 seconds of the uploaded mixed CH1 percussion fixture. These comparisons
were repeated after the final AR implementation; older songs retain their sound.

## Final UI CPU

Median milliseconds per frame; the 60 Hz budget is 16.67 ms. Mapped F4 uses
instrument 03 in the same PCM demo and displays the requested sample controls.

| View | Size | v0.2.31 | v0.2.32 | Change |
|---|---|---|---|---|
| pattern | 1280x900 | 2.873 | 2.868 | -0.2% |
| pattern | 960x1080 | 2.760 | 2.835 | +2.7% |
| info | 1280x900 | 2.101 | 2.107 | +0.3% |
| info | 960x1080 | 2.050 | 2.006 | -2.2% |
| pcm-samples | 1280x900 | 1.604 | 1.593 | -0.7% |
| pcm-samples | 960x1080 | 2.090 | 2.093 | +0.2% |
| pcm-instrument | 1280x900 | 2.052 | 1.385 | -32.5% |
| pcm-instrument | 960x1080 | 1.699 | 1.554 | -8.5% |

The new import toggle is measured separately with the same loaded waveform:

| F3 size | Auto-squeeze on | Auto-squeeze off | On minus off, ms |
|---|---|---|---|
| 1280x900 | 1.593 | 1.687 | -0.095 |
| 960x1080 | 2.093 | 2.029 | +0.064 |

Import conversion runs as background work when a file is imported; it is not
part of drawing. These measurements cover the toggle's steady-state UI cost.

A separate six-trial AR toggle check sets CH1 to ON or OFF every eighth row
in otherwise identical temporary copies of the SID demo. Scopes remain on;
2048-sample blocks render 20 seconds per trial. Median audio CPU is
**6.409 ms/block OFF / 6.603 ms/block ON** (+3.0%).
ON and OFF intentionally differ in arpeggio sound; this check is separate from
the unchanged-song release comparison. Raw results, input hashes and exact
modifications are in `validation/v0.2.32/arp-performance/`.

## Final live playback

Median percentage of one CPU core. Counters sum three repetitions. Export
analysis stayed active during the measured trials and completed without errors.

| Workload | Version/song | UI CPU % | Audio CPU % | Gaps | Missing frames | Late callbacks | Over-budget blocks |
|---|---|---|---|---|---|---|---|
| live-info-2048 | baseline-sid | 16.76 | 20.48 | 0 | 0 | 0 | 0 |
| live-info-2048 | candidate-sid | 16.78 | 19.97 | 0 | 0 | 0 | 0 |
| live-info-2048 | baseline-pcm | 17.20 | 20.73 | 0 | 0 | 0 | 0 |
| live-info-2048 | candidate-pcm | 16.97 | 20.50 | 0 | 0 | 0 | 0 |
| live-info-512 | baseline-sid | 16.71 | 22.56 | 0 | 0 | 0 | 0 |
| live-info-512 | candidate-sid | 16.80 | 22.15 | 0 | 0 | 8 | 5 |
| live-info-512 | baseline-pcm | 16.92 | 23.06 | 0 | 0 | 7 | 8 |
| live-info-512 | candidate-pcm | 16.77 | 22.66 | 0 | 0 | 6 | 0 |
| live-pcm-export-2048 | baseline-pcm | 36.04 | 19.90 | 0 | 0 | 0 | 0 |
| live-pcm-export-2048 | candidate-pcm | 37.12 | 20.24 | 0 | 0 | 0 | 0 |

At 512 samples, one candidate SID run accounts for all eight late callbacks
and five over-budget blocks; the other two have neither. PCM stress trials
also show late callbacks in both releases. No queued audio was exhausted.
Shared-host scheduling is a plausible explanation, not an established cause.
The default buffer retains substantial headroom in these measurements.

## Earlier measurements and regression investigation

The initial 160-trial series is retained in `validation/v0.2.32/performance/`:
five alternating repetitions of offline audio/UI, three live repetitions,
300 warmed UI frames and the same songs/buffers/scopes. It preceded the last
header, clipboard, Select all and AR additions. All 30 earlier live trials
also had zero gaps/missing frames. Candidate default-buffer trials had no
late callbacks; PCM export analysis had one over-budget block without a gap.
The initial PCM 512-sample candidate had 42 late callbacks, 38 in one run,
versus 17 for the baseline. Those observations have not been discarded.

The initial 1280×900 pattern batch appeared 11.5% slower (2.799 → 3.121 ms).
Before changing code, both versions were profiled serially. Draw-rectangle,
blit, pattern, text and helper work remained the leading costs, with matching
hot-path call counts. A longer seven-pair, 900-frame comparison without code
changes measured **2.798 → 2.812 ms/frame** (+0.5%). The apparent regression
did not reproduce, and the final batch above also stays at baseline. Raw
profiles and all 14 repeated trials remain in `pattern-check/`. No requested
feature was disabled and no speculative optimization was applied.

## C64 packing: size and CPU tradeoff

This is separate from host app performance. Full PCM demo, PAL:

| Encoding | PRG bytes | Maximum measured music cycles | Combined conservative bound |
|---|---:|---:|---:|
| v0.2.31 resident streams | 35,329 | 7,892 | 17,178 |
| v0.2.32 / v1.0 | 31,448 | 7,672 | 16,716 |
| v0.2.32 / v2.0 | 30,468 | 7,672 | 16,716 |
| v0.2.32 / v2.0.1 | 26,677 | 8,357 | 18,153 |
| v0.2.32 / v2.0.2 | 24,918 | 8,385 | 18,211 |

The smallest candidate saves 29.5% versus the previous release and uses
6.2% more maximum music-decoder cycles. The v1.0/v2.0 choices reduce both
size and maximum music cycles relative to v0.2.31. The comparison exposes
that choice. Sample NMI cost remains at most 109 CPU cycles, within the
246-cycle PAL sample interval. Every export verifies its complete music,
loop restart, sample nibbles and combined PCM/VIC deadline; unsafe candidates
cannot be exported. Channel remapping adds no C64 routing instructions.

## Correctness and reproduction

The final broad regression exercised 1,553 cases: 1,552 passed and one exposed
an empty-bank access in the new mapped-instrument UI. That access was guarded;
all 126 affected regression cases then passed, including the failing case,
header/F4 clipboard, mapped instruments, AR, pattern clipboard, scrollbars
and program switches. The earlier complete suite had 1,524 passes. Exact
run counts and the correction are in `final-regression.json`.

Focused PCM checks cover PAL/NTSC, loop/stop, instrument memory, trim/gain/pitch,
undo, embedding, import, every packer, asynchronous comparison and independent
py65 interruption inside all three decoder families. All bundled player images
reproduce with 64tass. Actual VICE PRGs cover the uploaded CH1 examples, CH2/CH3
arrangements, CH2 bass and actual phrase/indexed decoders. The three earlier
user PRGs reproduced byte-for-byte from the final playback code. UI inspection
covers 640×480, 960×1080 and 1280×900. Physical C64 listening remains untested.

The final HERMO.ROM tester has PCM/SID percussion on CH1, bass on CH2 and leads
on CH3 across two patterns (15.36 seconds). Its 6,490-byte indexed PRG verifies
769 music calls, with maximum measured music cost 8,745 cycles and conservative
combined bound 18,966 cycles. Both PAL 8580 and 6581 VICE runs cover the complete
song and loop restart. The identical-address sample-neutralized 8580 comparison
confirms all 32 kick/snare hits: difference RMS is 187–238 for kicks and 114–140
for snares, in 16-bit recording units. SID writes for 32 hats, 64 bass notes and
64 lead notes are checked by the compiler. Detailed source hashes, timings and
per-hit results are in `hermo-rom-export.json` and `hermo-rom-emulation.json`.

Reproduce the final serial benchmark from a fresh output directory:

```bash
python scripts/benchmark_pcm_update.py --baseline /path/to/v0.2.31/sidpulse-tracker \
  --candidate . --song examples/autumn-at-five-synthwave-mix_v9-pw-sweep.sidpulse \
  --pcm examples/autumn-at-five-synthwave-pcm-drums.sidpulse \
  --out /path/to/fresh-results --repetitions 3 --live-repetitions 3 --ui-iterations 900
```

For the focused pattern check, `scripts/benchmark_releases.py --worker task.json`
accepts `kind=gui`, `page=pattern`, `size=[1280,900]`, `iterations=900`, scopes on,
CPU affinity `[0]` and the same original SID demo. Profile each version first,
then alternate seven serial pairs. AR toggle tasks use `kind=audio`,
`frames=2048`, `seconds=20`, scopes on and the modified temporary songs described
in `arp-performance/method.json`. Raw task metadata is preserved with each
observation; private absolute source paths are omitted.
