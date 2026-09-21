# v0.2.39 rendering performance

Baseline: v0.2.38 with CI checkpoint-001. Candidate: v0.2.39 checkpoint-001.
Both used the same Python 3.12.14 environment, SDL dummy drivers, one pinned CPU,
scopes enabled and the unmodified `autumn-at-five-synthwave-mix_v9-pw-sweep.sidpulse`.
The benchmark simulates playback position changes and measures drawing work;
it does not measure a physical audio output device or desktop compositor.

Five serial trials per variant and size, 32 warm-up frames then 200 measured
frames each. Trial order alternates. No tests or other benchmarks ran alongside
these trials. Median CPU milliseconds per frame, with trial ranges in parentheses:

| View | v0.2.38 baseline | v0.2.39 fit on | v0.2.39 fit off |
|---|---:|---:|---:|
| F2 960×1080 | 2.664 (2.564–2.889) | 2.339 (2.247–2.488) | 2.748 (2.557–3.143) |
| F2 800×600 | 1.281 (1.235–1.402) | 1.586 (1.437–1.641) | 1.310 (1.248–1.442) |
| F2 960×540 | 1.336 (1.275–1.426) | 1.391 (1.281–1.510) | 1.377 (1.305–1.506) |
| F2 1280×900 | 2.784 (2.717–3.067) | 2.770 (2.635–2.940) | 2.759 (2.670–2.793) |
| F5 960×1080 | 2.203 (2.155–2.463) | 2.272 (2.124–2.736) | 2.205 (2.168–2.499) |

At 800×600, fitting costs about 0.305 ms/frame more than the baseline, around
24% of this small rendering workload or 1.8 percentage points of one CPU core
at 60 FPS. This is the clearest overhead: the fitted view draws a third voice.
At 960×1080 the fitted font reduced measured drawing cost in these trials;
the 1280×900 and F5 ranges overlap, so no speedup is claimed there. Differences
at 960×540 and with fitting off are within trial variation.

Across the fitted F2 cases, median per-trial wall-clock p95 stayed below 3.6 ms.
Two of the 1,000 fitted 960×1080 frames exceeded 16.67 ms; the other fitted F2
cases had none. The baseline also had isolated late frames in other cases.
These measurements show no sustained large rendering regression, but cannot
promise zero scheduler stalls or predict every machine's desktop performance.

The grid preserves row spacing, bounds its glyph/cell/button caches, and reuses
fonts and hit rectangles on steady frames. Tests explicitly reject new font
construction on those frames. Audio, sequencing, SID backends, sample synthesis
and export implementations are byte-identical to the baseline.

Raw [environment](../validation/v0.2.39/pattern-fit/environment.json) and
[75 trial records](../validation/v0.2.39/pattern-fit/results.jsonl) are included.
Reproduce from the project directory with an untouched baseline checkout:

```bash
python scripts/benchmark_pattern_fit.py \
  --baseline ../baseline-release --candidate . \
  --input examples/autumn-at-five-synthwave-mix_v9-pw-sweep.sidpulse \
  --out ../pattern-fit-results --repetitions 5
```

The Linux harness requires CPU-affinity support and refuses to reuse its output
directory. It verifies the input song did not change.
