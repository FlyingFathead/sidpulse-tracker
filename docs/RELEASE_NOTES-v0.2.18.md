# SIDpulse Tracker v0.2.18 candidate

## Export-only File Squeezer

SID and PRG exports now offer a default-checked master switch and checked
suboptions for duplicate patterns, identical instruments, unused source objects,
and resident voice/timing compression. The original project and preview remain
untouched. Missing configuration keys default to enabled; confirmed GUI choices
persist in machine preferences. CLI exports default on independently.

The important saving is in **actual replay representation**, not only a disk
cruncher: shared literals are read in place, independent voices can reuse bytes,
and no uncompressed song buffer is allocated. Single/five-stream player images
include all mutable state. The compact PRG removes loader padding while retaining
its existing display, clock check and RUN/STOP behavior.

First light PAL SID: 22,552 → 8,638 bytes. First light PAL PRG: 24,477 → 8,951.
Autumn at five PAL SID: 11,174 → 4,717. Actual ratios depend on the arrangement.

The exporter keeps the legacy path byte-identical with `--no-squeeze-song`, and
falls back when tested packed layouts would cost more resident memory or exceed
its conservative CIA-call budget. It never solves an overflow by dropping music.

## Validation status

431 dependency-free pytest checks passed; 3 unavailable-dependency checks/modules
were skipped. An independent C instruction emulator passed 104 cases covering
118,904 logical ticks and both PRG wrappers' scripted startup/stop paths. This
is not the complete test suite, a VICE run, or a native/hardware listening test.

GUI/py65/native-audio dependencies were unavailable and could not be downloaded.
The full suite, interactive export dialog, 64tass reproducibility, VICE/audio and
hardware gates remain open. Per-tick writes/order/timing are preserved, but
intra-tick spacing is not cycle-identical. Treat this as a candidate for validation
before publishing a stable tag. No remote CI result or public release is implied.

See [design and controls](SQUEEZER.md), [full measurements](SQUEEZER_VALIDATION-v0.2.18.md),
and the [machine-readable record](SQUEEZER_VALIDATION-v0.2.18.json).

## Scope

Native format 6, dependencies, preview engine, existing editor behavior and audio
buffer settings are unchanged. This does not add PCM/digi playback, arbitrary SID
import, multichip support, a new native tracker replay engine, or provably optimal
compression. No extra runtime build/tool requirement is introduced.

The full source snapshot does not include font binaries. It uses a system
monospace fallback when the supplied tracker font is absent; incremental updates
retain an existing font and custom font preference.
