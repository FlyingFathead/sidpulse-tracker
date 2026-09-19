# SIDpulse Tracker v0.2.30 performance

Matched checks use the unchanged native v8 stress arrangement and all four
bundled examples. The v8 input SHA-256 is
`91032c512875fa96636d21ba05bacda2a309e4e67a30ee96f42b1f47e7c58430`.
No source song was changed. Trials run serially, with alternating order and no
concurrent tests, profilers or other benchmark jobs.

Environment: Linux x86_64, Python 3.12.14, pygame-ce 2.5.7, pyresidfp 0.17.0,
SDL dummy audio/video. Native comparisons use immutable **v0.2.29 (`e4e38c1`)**.
M/S controls and scopes stay enabled. Three trials for v2.0.1/v2.0.2, shared comparison and native workloads;
one current-build preservation trial for unchanged v1.0/v2.0. Their repeated
baselines remain in the v0.2.29 report. Timing
values below are median (minimum–maximum). RSS uses a fresh process per export.

## Stress-song export sizes and C64 playback

All versions replay 6,912 musical ticks / about 189.89 seconds. Every compact
export passes complete ordered-write, timing, loop, memory and reinit checks.

| Target | Squeezer | File B | Owned resident B | Player/state B | Song data B | Max C64 cycles/call |
|---|---|---:|---:|---:|---:|---:|
| SID | 1.0 | 26,808 | 26,690 | 580 | 26,104 | 7,512 |
| SID | 2.0 | 25,643 | 25,525 | 580 | 24,939 | 7,512 |
| SID | 2.0.1 | 21,492 | 21,374 | 741 | 20,627 | 8,172 |
| SID | 2.0.2 | 20,247 | 20,129 | 1,161 | 18,962 | 8,287 |
| PRG | 1.0 | 27,121 | 27,130 | 580 | 26,104 | 7,510 |
| PRG | 2.0 | 25,956 | 25,965 | 580 | 24,939 | 7,510 |
| PRG | 2.0.1 | 21,805 | 21,814 | 741 | 20,627 | 8,259 |
| PRG | 2.0.2 | 20,560 | 20,569 | 1,161 | 18,962 | 8,192 |

v2.0.2 saves **1,245 bytes** beyond v2.0.1, about 5.8% of the SID file
and owned resident allocation. Packet data shrinks by 1,665 bytes while the
register player grows by 420 bytes, including a 336-byte immutable dictionary.
It saves 5,396 bytes beyond v2.0 and 6,561 bytes beyond v1.0 on this input.

This trades some C64 work for space. The SID maximum rises from 8,172 to 8,287
cycles, about 1.4%. The PRG maximum falls from 8,259 to 8,192 cycles, about 0.8%.
Link-address-dependent branch/page crossings contribute to these differences. These maxima
exclude external IRQs, VIC DMA and PRG polling; they are not total machine CPU
utilization. Every selected call passes the 80%-of-CIA-period check with a
128-cycle margin. Earlier methods remain selectable.

Resident bytes include loaded player/state, song, wrapper, owned zero page and
call stack. They exclude SID's 124-byte header and PRG's two-byte load prefix.
They are not a measure of all free C64 RAM. State is counted only once.

## Host export work and RAM

| Target | Analysis | CPU seconds | Wall seconds | Peak process RSS MiB |
|---|---|---:|---:|---:|
| SID | 1.0 | 23.455 (23.455–23.455) | 23.488 (23.488–23.488) | 52.87 (52.87–52.87) |
| SID | 2.0 | 27.398 (27.398–27.398) | 27.415 (27.415–27.415) | 60.37 (60.37–60.37) |
| SID | 2.0.1 | 28.610 (28.439–28.852) | 28.672 (28.454–28.858) | 64.07 (63.93–64.38) |
| SID | 2.0.2 | 28.838 (28.646–29.003) | 28.854 (28.650–29.017) | 64.07 (64.01–64.36) |
| SID | All four | 39.955 (39.892–40.030) | 39.961 (39.936–40.034) | 64.45 (64.35–64.48) |
| PRG | 1.0 | 23.299 (23.299–23.299) | 23.304 (23.304–23.304) | 53.30 (53.30–53.30) |
| PRG | 2.0 | 27.343 (27.343–27.343) | 27.344 (27.344–27.344) | 60.48 (60.48–60.48) |
| PRG | 2.0.1 | 28.592 (28.370–28.879) | 28.612 (28.374–28.892) | 64.08 (64.07–64.42) |
| PRG | 2.0.2 | 29.048 (28.856–29.066) | 29.075 (28.876–29.087) | 64.21 (64.19–64.33) |
| PRG | All four | 39.762 (39.607–39.778) | 39.776 (39.622–39.782) | 64.35 (64.31–64.64) |

The default comparison shares source recording, candidates and completed
verification. Its cost is below four independent full analyses. Each
comparison's four export hashes match independently compiled outputs exactly.
Switching completed columns performs no compilation. Turning comparison off
limits work to the selected version. Peak RSS is the whole temporary compiler
process, including Python and imports, not permanent editor memory or C64 RAM.

## Bundled native examples

| Song | Target | v1.0 file B | v2.0 file B | v2.0.1 file B | v2.0.2 file B | v2.0.1 max cycles | v2.0.2 max cycles |
|---|---|---:|---:|---:|---:|---:|---:|
| autumn-at-five-ntsc.sidpulse | SID | 3,617 | 3,568 | 3,568 | 3,568 | 5,580 | 5,580 |
| autumn-at-five-ntsc.sidpulse | PRG | 3,930 | 3,881 | 3,881 | 3,881 | 5,577 | 5,577 |
| autumn-at-five.sidpulse | SID | 3,600 | 3,555 | 3,555 | 3,504 | 5,582 | 5,883 |
| autumn-at-five.sidpulse | PRG | 3,913 | 3,868 | 3,868 | 3,817 | 5,576 | 5,820 |
| first-light-ntsc.sidpulse | SID | 6,402 | 6,402 | 6,402 | 6,402 | 4,212 | 4,212 |
| first-light-ntsc.sidpulse | PRG | 6,715 | 6,715 | 6,715 | 6,715 | 4,151 | 4,151 |
| first-light.sidpulse | SID | 6,496 | 6,496 | 6,496 | 6,456 | 4,414 | 10,673 |
| first-light.sidpulse | PRG | 6,809 | 6,809 | 6,809 | 6,769 | 4,353 | 10,544 |

v2.0.1/v2.0.2 are repeated three times per target; earlier versions receive one
current-build preservation trial. Repeated output bytes are deterministic.
Smaller older layouts remain candidates: a version label does not promise a
particular decoder will win for every song.

## Native tracker CPU

960×1080 UI checks use 400 measured frames after warm-up. Audio checks use
15-second native renders at 2048 and 512 frames. Live checks run for 15 seconds
per trial with the real audio subprocess and SDL dummy callbacks.

| Workload | Unit | v0.2.29 | v0.2.30 |
|---|---|---:|---:|
| pattern | ms/frame | 2.914 (2.902–2.954) | 2.890 (2.816–3.042) |
| instrument | ms/frame | 1.774 (1.684–1.787) | 1.736 (1.723–1.786) |
| samples | ms/frame | 1.358 (1.354–1.447) | 1.406 (1.376–1.422) |
| settings | ms/frame | 1.159 (1.132–1.230) | 1.204 (1.163–1.227) |
| help | ms/frame | 2.075 (1.901–2.104) | 1.986 (1.938–2.034) |
| orders | ms/frame | 1.961 (1.905–2.002) | 1.969 (1.931–2.037) |
| files | ms/frame | 1.017 (1.007–1.042) | 1.017 (0.989–1.022) |
| info | ms/frame | 2.048 (2.047–2.193) | 2.074 (1.982–2.092) |
| scrolling-instrument | ms/frame | 0.725 (0.722–0.730) | 0.737 (0.728–0.742) |
| scrolling-samples | ms/frame | 0.886 (0.879–0.897) | 0.910 (0.907–0.925) |
| record-pw | ms/frame | 1.355 (1.353–1.372) | 1.384 (1.375–1.387) |
| v8-2048-15s | ms/audio block | 6.426 (6.386–6.501) | 6.419 (6.392–6.464) |
| v8-512-15s | ms/audio block | 1.733 (1.710–1.773) | 1.713 (1.699–1.714) |
| info-512 | UI core % | 16.873 (16.710–17.063) | 16.868 (16.801–16.877) |
| info-512 | Audio core % | 22.579 (22.443–22.931) | 22.782 (22.318–22.861) |
| record-pw-2048 | UI core % | 13.246 (13.088–13.763) | 13.528 (13.511–14.017) |
| record-pw-2048 | Audio core % | 20.056 (19.998–20.866) | 20.463 (20.392–20.985) |

Live scheduling totals across the three trials:

| Workload | Version | Gaps | Missing frames | Late callbacks | Over-budget blocks |
|---|---|---:|---:|---:|---:|
| info-512 | 0.2.29 | 0 | 0 | 1 | 0 |
| info-512 | 0.2.30 | 0 | 0 | 1 | 0 |
| record-pw-2048 | 0.2.29 | 0 | 0 | 0 | 0 |
| record-pw-2048 | 0.2.30 | 0 | 0 | 0 | 0 |

This final native batch includes the shared scrollbars and supplied window icon.
The previous 42-record batch is retained as `native-before-scrollbars/`.
All native synthesis/audio/sequencer source files are byte-identical to v0.2.29;
their hashes are recorded. Across this final batch there are zero gaps, zero missing frames and zero
over-budget blocks in both versions. Each version has one late callback in
the 512-frame live case; the recording case has none. Small CPU differences
are reported with full trial ranges rather than treated as speedups.
These measurements do not replace physical-device,
Windows, VICE or real-C64 testing. The earlier complete native PCM equivalence
checks remain relevant to unchanged synthesis code; this release does not claim
new cross-platform or analog SID audio equivalence.

## Comparison drawing

- Completed export panel, off: **5.678 (5.663–5.760) ms/frame** at 960×1080, 400 frames per trial.
- Completed export panel, top3: **6.454 (6.434–6.531) ms/frame** at 960×1080, 400 frames per trial.
- Completed export panel, all: **6.864 (6.792–6.871) ms/frame** at 960×1080, 400 frames per trial.

Scrollbar drawing ablation at 960×540, three serial 400-frame trials per setting.
The off condition skips only scrollbar painting/geometry; all other features
stay enabled. This isolates its cost, rather than calling feature removal an
optimization. Files uses the worker’s initial empty browser view.

| Page | Bars not drawn (ms/frame) | Bars drawn (ms/frame) | Median difference (ms) |
|---|---:|---:|---:|
| pattern | 1.087 (1.078–1.118) | 1.094 (1.077–1.221) | +0.008 |
| instrument | 0.744 (0.735–0.833) | 0.757 (0.751–0.775) | +0.014 |
| samples | 0.841 (0.830–0.860) | 0.867 (0.854–0.867) | +0.026 |
| settings | 0.601 (0.597–0.605) | 0.629 (0.613–0.693) | +0.027 |
| help | 0.779 (0.775–0.813) | 0.772 (0.772–0.821) | -0.007 |
| orders | 0.642 (0.636–0.685) | 0.658 (0.651–0.695) | +0.016 |
| files | 0.519 (0.499–0.545) | 0.499 (0.499–0.517) | -0.020 |

UI memory after warming seven pages in fresh processes (three trials, audio disabled).
Resident and peak values use Linux VmRSS and VmHWM from one process-status snapshot:

| Version | Resident MiB | Peak MiB |
|---|---:|---:|
| 0.2.29 | 43.22 (43.18–43.38) | 43.22 (43.18–43.38) |
| 0.2.30 | 43.34 (43.33–43.35) | 43.34 (43.33–43.35) |

The median resident difference is about 0.12 MiB, within the baseline trial
range; this does not establish a meaningful memory increase or reduction.
This includes the supplied icon: decoded and scaled once at startup. It adds no
per-frame decoding. The promo GIF/MP4 are repository media, never loaded by the
tracker. RSS includes Python, SDL, fonts and graphics caches; it is separate from
the C64 resident-memory figures above.

Drawing only reads completed results; it never runs the optimizer. These panel
figures measure the additional visible content and do not affect ordinary
pattern/instrument/audio playback when the export panel is closed.

## Raw evidence and reproduction

- `validation/v0.2.30/squeezer-stress/`: 22 isolated compiler records.
- `validation/v0.2.30/squeezer-examples/`: 64 isolated compiler records.
- `validation/v0.2.30/native/`: 90 matched UI/audio/live records, environment and
  unchanged native-code hashes.
- `validation/v0.2.30/scrollbar-draw.json`: 42 scrollbar drawing records.
- `validation/v0.2.30/ui-memory.json`: six isolated UI memory records.
- `validation/v0.2.30/comparison-draw.json`: three trials each for comparison off, Top 3 and all versions.
- `scripts/compare_squeezers.py --isolated --include-comparison` reproduces the
  export matrix; omit song paths for all bundled native examples.
- `scripts/benchmark_releases.py --worker task.json` runs each native case;
  all non-path task fields are retained in the raw records.

See [squeezer design and findings](SQUEEZER-v2.0.2.md) and
[validation](VALIDATION-v0.2.30.md). No improvement is claimed for unimplemented
native effect/ramp instruction schemes.

## Final Show all preference follow-up

Compared against the initially delivered v0.2.30 (`3caa048`), with three serial
alternating-order trials. Rendering uses 400 frames at 960×1080; audio and live
checks run five seconds per trial, with scopes and M/S enabled. Completed export
results are reused; neither drawing nor changing this preference recompiles.

| Workload | Unit | Previous v0.2.30 | Final v0.2.30 |
|---|---|---:|---:|
| export-default | ms/frame | 6.677 (6.615–6.678) | 6.992 (6.962–7.166) |
| export-top3 | ms/frame | 6.613 (6.612–7.014) | 6.566 (6.540–6.828) |
| export-all | ms/frame | 7.132 (7.057–7.192) | 7.001 (6.952–7.014) |
| pattern | ms/frame | 2.790 (2.771–2.846) | 2.790 (2.691–2.933) |
| audio-2048 | ms/block | 6.531 (6.395–6.984) | 6.388 (6.365–6.496) |
| info-2048 | UI core % | 16.796 (16.361–16.826) | 16.908 (16.726–16.991) |
| info-2048 | Audio core % | 20.337 (19.770–20.744) | 19.973 (19.585–20.185) |

Values are median (range). Default export drawing now includes four cards instead
of three; the explicit modes keep identical visible content in both versions.
The preference is read only on opening the export menu and written only when
the checkbox changes. Native playback and compiled music bytes are unchanged.

| Version | Gaps | Missing frames | Late callbacks | Over-budget blocks |
|---|---:|---:|---:|---:|
| previous | 0 | 0 | 0 | 0 |
| final | 0 | 0 | 0 | 0 |

Raw follow-up records and environment: `validation/v0.2.30/show-all-final/`.
The earlier performance data remains as measured; its Top 3 default describes
the initial delivery. These dummy-driver checks do not cover physical hardware.
