# v0.2.38 performance check

Matched serial comparisons against the supplied v0.2.37 full ZIP. The source
song, scopes, interpreter, CPU affinity and dimensions were held constant.
24 drawing trials and 16 spawned-worker playback trials; eight playback trials
use the candidate. No concurrent tests ran during timed measurements.

## Drawing CPU milliseconds per frame

| View | v0.2.37 median (range) | v0.2.38 median (range) |
| --- | ---: | ---: |
| info-1280x900 | 2.287 (2.162–2.324) | 2.355 (2.171–2.376) |
| info-960x1080 | 2.131 (2.064–2.180) | 2.183 (2.124–2.240) |
| pattern-1280x900 | 2.747 (2.726–3.002) | 2.749 (2.735–2.755) |
| pattern-960x1080 | 2.222 (2.140–2.237) | 2.732 (2.531–2.747) |

A longer 800-frame check in both version orders reproduced a modest cost at
960×1080 in F2: 2.252 → 2.635 ms CPU/frame (+0.383 ms,
about 2.30 percentage points of one core at 60 redraws/second).
This is a measured rendering increase, not a claim of faster drawing. Separate
profiles place the extra work mainly in rectangle drawing. The fixed view uses
larger requested glyphs and cell metrics. Font objects remain cached across
steady frames; no audio work was added to rendering.

## Live playback

Percentages use one logical core = 100%. Each cell below is the median of two
five-second measured runs, after worker startup and warm-up.

| View / buffer | Baseline UI + audio CPU | Candidate UI + audio CPU | Candidate gaps / missing frames / late callbacks |
| --- | ---: | ---: | --- |
| info-2048 | 40.82% | 40.13% | 0 / 0 / 0 |
| info-512 | 43.57% | 43.95% | 0 / 0 / 0 |
| pattern-2048 | 42.39% | 43.48% | 0 / 0 / 0 |
| pattern-512 | 45.73% | 49.02% | 0 / 0 / 2 |

Baseline totals: 0 gaps, 0 missing_frames, 1 late_callbacks, 3 over_budget_blocks.

Candidate totals: 0 gaps, 0 missing_frames, 2 late_callbacks, 3 over_budget_blocks.

## Limits and evidence

These are Linux SDL dummy-device checks, not physical audio or Windows tests.
Short hotfix checks cannot establish long-duration or under-load glitch freedom.
The known 512-sample export-contention limitation from earlier releases is not
retested or claimed fixed. Audio synthesis, sequencer, SID backend and export
files match v0.2.37 byte for byte. No sample rate, buffer default, note timing,
envelope or release-tail algorithm changed.

Raw results, longer checks, separate profiles and environment metadata are in
`docs/validation/v0.2.38/`. No remote publication occurred during packaging.
