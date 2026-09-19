# SIDpulse Tracker v0.2.29 performance

Matched checks use the unchanged native v8 stress arrangement and all four
bundled examples. The v8 input SHA-256 is
`91032c512875fa96636d21ba05bacda2a309e4e67a30ee96f42b1f47e7c58430`.
No source song was changed. Trials run serially, with alternating order and no
concurrent tests, profilers or other benchmark jobs.

Environment: Linux x86_64, Python 3.12.14, pygame-ce 2.5.7, pyresidfp 0.17.0,
SDL dummy audio/video. Native comparisons use immutable **v0.2.28 (`5e4f43c`)**.
M/S controls and scopes stay enabled. Three trials per configuration; timing
values below are median (minimum–maximum). RSS uses a fresh process per export.

## Stress-song export sizes and C64 playback

All versions replay 6,912 musical ticks / about 189.89 seconds. Every compact
export passes complete ordered-write, timing, loop, memory and reinit checks.

| Target | Squeezer | File B | Owned resident B | Player/state B | Song data B | Max C64 cycles/call |
|---|---|---:|---:|---:|---:|---:|
| SID | 1.0 | 26,808 | 26,690 | 580 | 26,104 | 7,512 |
| SID | 2.0 | 25,643 | 25,525 | 580 | 24,939 | 7,512 |
| SID | 2.0.1 | 21,492 | 21,374 | 741 | 20,627 | 8,172 |
| PRG | 1.0 | 27,121 | 27,130 | 580 | 26,104 | 7,510 |
| PRG | 2.0 | 25,956 | 25,965 | 580 | 24,939 | 7,510 |
| PRG | 2.0.1 | 21,805 | 21,814 | 741 | 20,627 | 8,259 |

v2.0.1 saves **4,151 bytes** beyond v2.0: about 16.3% of its compact SID-owned
resident allocation, or 16.2% of the SID file. The larger register player adds
161 bytes but removes 4,312 data bytes. Compared with v1.0, the net saving is
5,316 bytes. This is additional to v2.0's previous 1,165-byte improvement.

This saving costs C64 CPU: worst-case music-routine cycles increase by about
8.8% for SID and 10.0% for PRG on this song. The export panel makes that tradeoff visible and allows an
immediate choice of an earlier version. These maxima exclude external IRQs,
VIC DMA and PRG polling; they are not total machine CPU utilization. Every
selected call still passes the 80%-of-CIA-period check with a 128-cycle margin.

Resident bytes include loaded player/state, song, wrapper, owned zero page and
call stack. They exclude SID's 124-byte header and PRG's two-byte load prefix.
They are not a measure of all free C64 RAM. State is counted only once.

## Host export work and RAM

| Target | Analysis | CPU seconds | Wall seconds | Peak process RSS MiB |
|---|---|---:|---:|---:|
| SID | 1.0 | 23.526 (23.426–23.585) | 23.532 (23.432–23.587) | 53.18 (52.93–53.19) |
| SID | 2.0 | 27.658 (27.440–27.994) | 27.660 (27.454–27.996) | 60.46 (60.38–60.46) |
| SID | 2.0.1 | 28.653 (28.226–28.749) | 28.658 (28.229–28.771) | 64.30 (64.28–64.30) |
| SID | All three | 35.835 (35.757–36.088) | 35.840 (35.762–36.098) | 64.48 (64.41–64.64) |
| PRG | 1.0 | 23.602 (23.455–24.290) | 23.605 (23.458–24.291) | 52.88 (52.88–52.88) |
| PRG | 2.0 | 27.727 (27.431–28.072) | 27.738 (27.433–28.075) | 60.47 (60.47–60.49) |
| PRG | 2.0.1 | 28.388 (28.330–29.032) | 28.390 (28.368–29.047) | 64.14 (64.13–64.29) |
| PRG | All three | 35.377 (35.343–35.792) | 35.378 (35.346–35.798) | 64.64 (64.50–64.64) |

The default comparison shares source recording, candidates and completed
verification. Its cost is far below three independent full analyses. Each
comparison's three export hashes match independently compiled outputs exactly.
Switching completed columns performs no compilation. Turning comparison off
limits work to the selected version. Peak RSS is the whole temporary compiler
process, including Python and imports, not permanent editor memory or C64 RAM.

## Bundled native examples

| Song | Target | v1.0 file B | v2.0 file B | v2.0.1 file B | v2.0 max cycles | v2.0.1 max cycles |
|---|---|---:|---:|---:|---:|---:|
| autumn-at-five-ntsc.sidpulse | SID | 3,617 | 3,568 | 3,568 | 5,580 | 5,580 |
| autumn-at-five-ntsc.sidpulse | PRG | 3,930 | 3,881 | 3,881 | 5,577 | 5,577 |
| autumn-at-five.sidpulse | SID | 3,600 | 3,555 | 3,555 | 5,582 | 5,582 |
| autumn-at-five.sidpulse | PRG | 3,913 | 3,868 | 3,868 | 5,576 | 5,576 |
| first-light-ntsc.sidpulse | SID | 6,402 | 6,402 | 6,402 | 4,212 | 4,212 |
| first-light-ntsc.sidpulse | PRG | 6,715 | 6,715 | 6,715 | 4,151 | 4,151 |
| first-light.sidpulse | SID | 6,496 | 6,496 | 6,496 | 4,414 | 4,414 |
| first-light.sidpulse | PRG | 6,809 | 6,809 | 6,809 | 4,353 | 4,353 |

Every version/target is repeated three times. Output bytes are deterministic.
Smaller older layouts remain candidates: a version label does not promise a
particular decoder will win for every song.

## Native tracker CPU

960×1080 UI checks use 400 measured frames after warm-up. Audio checks use
15-second native renders at 2048 and 512 frames. Live checks run for 15 seconds
per trial with the real audio subprocess and SDL dummy callbacks.

| Workload | Unit | v0.2.28 | v0.2.29 |
|---|---|---:|---:|
| pattern | ms/frame | 2.774 (2.774–2.896) | 2.764 (2.764–2.842) |
| instrument | ms/frame | 1.650 (1.641–1.658) | 1.670 (1.665–1.700) |
| record-pw | ms/frame | 1.343 (1.326–1.380) | 1.359 (1.351–1.456) |
| v8-2048-15s | ms/audio block | 6.449 (6.413–6.459) | 6.449 (6.440–6.474) |
| v8-512-15s | ms/audio block | 1.701 (1.686–1.758) | 1.727 (1.679–1.760) |
| info-512 | UI core % | 17.160 (16.782–17.767) | 16.831 (16.764–17.705) |
| info-512 | Audio core % | 22.645 (22.589–22.997) | 22.466 (22.243–23.256) |
| record-pw-2048 | UI core % | 14.391 (13.634–15.110) | 13.760 (13.348–14.111) |
| record-pw-2048 | Audio core % | 21.323 (20.787–21.980) | 20.731 (20.466–20.986) |

Live scheduling totals across the three trials:

| Workload | Version | Gaps | Missing frames | Late callbacks | Over-budget blocks |
|---|---|---:|---:|---:|---:|
| info-512 | 0.2.28 | 0 | 0 | 8 | 6 |
| info-512 | 0.2.29 | 0 | 0 | 10 | 7 |
| record-pw-2048 | 0.2.28 | 0 | 0 | 0 | 0 |
| record-pw-2048 | 0.2.29 | 0 | 0 | 0 | 0 |

All native synthesis/audio/sequencer source files are byte-identical to v0.2.28;
their hashes are recorded. These measurements do not replace physical-device,
Windows, VICE or real-C64 testing. The earlier complete native PCM equivalence
checks remain relevant to unchanged synthesis code; this release does not claim
new cross-platform or analog SID audio equivalence.

## Comparison drawing

- Completed export panel, comparison off: **5.997 (5.936–6.447) ms/frame** at 960×1080, 400 frames per trial.
- Completed export panel, comparison on: **6.783 (6.783–6.817) ms/frame** at 960×1080, 400 frames per trial.

Drawing only reads completed results; it never runs the optimizer. These panel
figures measure the additional visible content and do not affect ordinary
pattern/instrument/audio playback when the export panel is closed.

## Raw evidence and reproduction

- `validation/v0.2.29/squeezer-stress/`: 24 isolated compiler records.
- `validation/v0.2.29/squeezer-examples/`: 72 isolated compiler records.
- `validation/v0.2.29/native/`: 42 matched UI/audio/live records, environment and
  unchanged native-code hashes.
- `validation/v0.2.29/comparison-draw.json`: three on/off rendering trials.
- `scripts/compare_squeezers.py --isolated --include-comparison` reproduces the
  export matrix; omit song paths for all bundled native examples.
- `scripts/benchmark_releases.py --worker task.json` runs each native case;
  all non-path task fields are retained in the raw records.

See [squeezer design and findings](SQUEEZER-v2.0.1.md) and
[validation](VALIDATION-v0.2.29.md). No improvement is claimed for unimplemented
native effect/ramp instruction schemes.
