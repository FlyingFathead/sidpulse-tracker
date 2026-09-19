# SQUEEZER v1.0 / v2.0 comparison

Every source was byte-checked before and after export. All options are enabled;
only the squeezer version changes. v8 has three alternating-order trials per
target/version; the four bundled examples each have one trial per target/version.
Compiler CPU timings include exact replay verification and run serially.

| Song | Target | v1.0 bytes | v2.0 bytes | Saved | CPU seconds v1 / v2 | Max replay cycles v1 / v2 |
|---|---|---:|---:|---:|---:|---:|
| autumn-at-five-ntsc.sidpulse | PRG | 3,930 | 3,881 | 49 | 2.664 / 2.960 | 5,576 / 5,577 |
| autumn-at-five-ntsc.sidpulse | SID | 3,617 | 3,568 | 49 | 2.619 / 2.876 | 5,574 / 5,580 |
| autumn-at-five-synthwave-mix_v8-pw-sweep.sidpulse | PRG | 27,121 | 25,956 | 1,165 | 23.459 / 27.486 | 7,510 / 7,510 |
| autumn-at-five-synthwave-mix_v8-pw-sweep.sidpulse | SID | 26,808 | 25,643 | 1,165 | 23.565 / 27.643 | 7,512 / 7,512 |
| autumn-at-five.sidpulse | PRG | 3,913 | 3,868 | 45 | 2.612 / 2.859 | 5,570 / 5,576 |
| autumn-at-five.sidpulse | SID | 3,600 | 3,555 | 45 | 2.507 / 2.888 | 5,574 / 5,582 |
| first-light-ntsc.sidpulse | PRG | 6,715 | 6,715 | 0 | 5.622 / 6.673 | 4,151 / 4,151 |
| first-light-ntsc.sidpulse | SID | 6,402 | 6,402 | 0 | 5.382 / 6.738 | 4,212 / 4,212 |
| first-light.sidpulse | PRG | 6,809 | 6,809 | 0 | 5.364 / 6.578 | 4,353 / 4,353 |
| first-light.sidpulse | SID | 6,496 | 6,496 | 0 | 5.686 / 6.729 | 4,414 / 4,414 |

The selected v2.0 encoding is never larger in these comparisons. The v1.0
v8 SID is byte-identical to the previous delivered compiler. PRGs add startup
version credits in the existing text allocation, so their loader text changes.
All compact outputs pass two complete loop traversals, reinitialization,
ordered SID/timer writes, gate delay, memory ownership and cycle-budget checks.
The replay maximum is an instruction-level measurement, not C64 hardware or
analog SID equivalence. Export analysis is slower because v2.0 retains all
v1.0 candidates and adds its overlap search. No squeeze work runs in normal
tracker playback. Raw records are in the sibling squeezer folders.
