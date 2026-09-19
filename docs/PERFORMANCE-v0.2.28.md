# SIDpulse Tracker v0.2.28 performance verification

Version-only follow-up to revised v0.2.27 (`236350b`). The only change under
`sidpulse/` is the `__version__` constant. Audio, UI, recording, compression
and bundled replay bytes are unchanged. Existing extensive measurements
remain in [the v0.2.27 report](PERFORMANCE-v0.2.27.md).

Three serial matched trials alternate baseline/candidate order using the
unchanged v8 song, M/S and scopes enabled. GUI cases use 960x1080 and 400
measured frames per process. The short audio check uses 2048-frame blocks
for five seconds per trial. No tests or other heavy jobs ran alongside.

| Workload | Unit | Revised v0.2.27 | v0.2.28 |
|---|---|---:|---:|
| pattern | ms/frame | 2.799 (2.777–2.891) | 2.892 (2.891–2.976) |
| instrument | ms/frame | 1.693 (1.672–1.757) | 1.666 (1.642–1.731) |
| record-pw | ms/frame | 1.337 (1.333–1.352) | 1.341 (1.331–1.347) |
| v8-2048-5s | ms/block | 6.393 (6.290–6.469) | 6.421 (6.417–6.875) |

Values are median (minimum–maximum). This is a short version-bump check,
not a new optimization claim or a replacement for the earlier long audio,
native PCM, live scheduling and bundled-example export checks. Runtime
hashes prove the implementation files remain identical except version text.
Raw records and environment are in `validation/v0.2.28/`.

Validation uses Linux x86_64, Python 3.12.14, pygame-ce 2.5.7, pyresidfp
0.17.0 and SDL dummy. Physical devices and Windows timing are not covered.
