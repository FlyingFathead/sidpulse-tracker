# v0.2.19 candidate — automatic channel phrases

The default-on SID/PRG squeezer now compares counted per-channel phrase banks,
shared register-order templates, independent register-value streams and byte-cost
optimized static phrase banks. The editor still uses normal combined patterns.
Native songs, preview semantics and the native format are unchanged.

On the bundled PAL examples, complete First light exports are **6,496-byte SID /
6,809-byte PRG**; Autumn at five is **3,600-byte SID / 3,913-byte PRG**. The original
unsqueezed SIDs were 22,552 and 11,174 bytes respectively. These are actual output
and resident-memory improvements, without a whole-song decompression buffer.

The compiler checks byte reconstruction and executes the selected machine-code
player through original ordered writes, timer/idle behavior, full loops and
reinitialization. Smaller but too-slow layouts fall back. Semantic mismatches abort.
The exact legacy encoding remains available by unchecking Squeeze song or using
`--no-squeeze-song`. Existing source-copy cleanup and all checked defaults remain.

Reproducible benchmarks, native CPU tests and a canonical 64tass/CI rebuild gate
are included. This is **not a fully validated public release**: see
[the exact test results and remaining GUI/audio/hardware gates](VALIDATION-v0.2.19.md)
and [encoding/options](SQUEEZER.md). Different intra-tick decoder instruction timing
still requires real-target audio validation.
