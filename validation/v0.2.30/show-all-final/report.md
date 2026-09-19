
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
