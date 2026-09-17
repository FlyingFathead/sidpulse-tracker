# v0.2.18 squeezer validation

Status: **tested export-core candidate; desktop/audio/hardware release gates remain open**.
Source baseline: uploaded v0.2.17 snapshot. Measurements use the same native
songs and settings with `squeeze=False` versus default-enabled squeezing.
No GitHub push, tag, remote CI pass, hardware test or listening result is implied.

## Measured sizes

| Native example | Export | Legacy bytes | Squeezed bytes | Saved | Resident bytes, legacy → squeezed |
|---|---|---:|---:|---:|---:|
| first-light | .sid | 22,552 | 8,638 | 61.70% | 22,434 → 8,520 |
| first-light | .prg | 24,477 | 8,951 | 63.43% | 24,486 → 8,958 |
| first-light-ntsc | .sid | 22,504 | 8,742 | 61.15% | 22,386 → 8,624 |
| first-light-ntsc | .prg | 24,429 | 9,055 | 62.93% | 24,438 → 9,062 |
| autumn-at-five | .sid | 11,174 | 4,717 | 57.79% | 11,056 → 4,599 |
| autumn-at-five | .prg | 13,099 | 5,030 | 61.60% | 13,108 → 5,037 |
| autumn-at-five-ntsc | .sid | 11,082 | 4,581 | 58.66% | 10,964 → 4,463 |
| autumn-at-five-ntsc | .prg | 13,007 | 4,894 | 62.37% | 13,016 → 4,901 |

Resident accounting includes loaded music code, embedded decoder state, song
data, the PRG wrapper when present, owned zero-page bytes and the maximum
project-owned call-stack depth. It is not a claim about total C64 free RAM:
BASIC/KERNAL workspace, the screen, ROM routines' internal stack use and other
callers are outside this music-footprint figure. PSID's 124-byte host header
and PRG's two-byte load prefix are not loaded song RAM.

## Checks actually performed

**431 passed, 3 skipped** in the available dependency-free pytest subset.
The skips are the new pygame and py65 modules and one existing GUI test.
This is not the result of running the complete dependency-backed suite.

```bash
python -m pytest -q tests/test_squeeze.py tests/test_checkpoint_0213.py \
  tests/test_activity.py tests/test_editor.py tests/test_envelope_geometry.py \
  tests/test_file_browser.py tests/test_incremental_update.py tests/test_note_octave.py \
  tests/test_pcm_stream.py tests/test_preset_encoding.py tests/test_project.py \
  tests/test_song_loop.py tests/test_text_edit.py tests/test_squeeze_6502.py \
  tests/test_squeeze_gui.py
```

An independent C 6510 instruction emulator, adapted locally from the supplied
sidreloc CPU core, executed **104 cases / 118,904 logical ticks**. Its bus was
instrumented for ordered SID writes, CIA latches, owned writes, cycle counts
and stack depth. Tests covered both decoders at both link addresses, PAL/NTSC,
loop/stop/re-init, incoming decimal mode, changing tempos, slow-tick idle calls,
randomized interleaving and packet page crossings. Explicit gate-settling tokens
retained at least the requested delay between surrounding SID writes.

The actual compact and legacy BASIC wrappers also executed against scripted
CIA underflows, RUN/STOP input and RTS stubs for KERNAL calls. Music writes,
clock-mismatch exit, zero-page restoration and interrupt/carry restoration
passed. This is **not** cycle-exact CIA/VIC/SID emulation or execution in VICE.
The local sidreloc-based harness and its native shared library are not runtime
dependencies and are not included in the source release.

The opt-out PSID path passed all four existing PAL/NTSC SHA-256 golden tests.
Pure tests additionally check source equality, duplicate/unused source objects,
implicit instrument memory, order-jump addressing, preference migration,
CLI opt-out, atomic output paths, reference validity and preflight errors.
A 17,408-tick repeating fixture that exceeded the old memory budget now compiles
into a 5,998-byte SID without shortening it.

A local auxiliary assembler reproduced both original legacy binaries exactly
and assembled/reproduced the five new images. `64tass` itself was unavailable;
its independent rebuild check remains pending. Python compilation checks passed.
The companion JSON records the tested binary hashes and per-case measurements.

## Still required before a stable/public release

Run the complete pytest suite with the pinned development/runtime dependencies,
including `tests/test_squeeze_6502.py` and `tests/test_squeeze_gui.py`. Then run the
headless startup checks, inspect the dialog at low/high zoom, and exercise S/E,
Cancel, checkbox persistence, save failures and both file destinations.

Run `python scripts/build_squeeze_players.py --check` with 64tass installed.
Compare native/libsidplayfp audio and listen under matching PAL/NTSC VICE and,
where available, real C64 hardware. In particular check percussion attacks,
hard restarts, sync/ring effects and tempo transitions.

Packed output preserves logical ticks, CIA period/idle counts, ordered SID
writes and explicit gap tokens. It does **not** preserve cycle-for-cycle spacing
between all writes within a tick. The memory-saving decoder is slower than the
flat legacy decoder; a conservative per-call check falls back to legacy encoding
when packing is not safe under that check. This does not guarantee CPU headroom
for an unrelated demo/game, badlines or other interrupts.

The build environment had no pygame-ce, py65, pyresidfp, libsidplayfp, 64tass or
VICE, and dependency downloads failed. Those checks have not been reported as
passing. No full-suite or audible-equivalence claim is made.
