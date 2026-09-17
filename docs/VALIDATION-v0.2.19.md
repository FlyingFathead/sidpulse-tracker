# SIDpulse Tracker v0.2.19 — implementation and validation

Date: 2026-09-17. **Local source candidate, not a published/tagged release.**
Implementation baseline: the latest supplied v0.2.18 full source candidate.
Native source/song format remains 6. No GitHub push, remote CI pass, release,
Windows run, VICE run or hardware listening is implied.

## Measured complete exports

The same bundled native arrangements, PAL, whole-song looping enabled. All sizes
are bytes, including SID headers or the standalone PRG wrapper. The v0.2.18
column was recompiled from that candidate, not copied from an earlier answer.

| Song / format | Legacy squeeze off | Latest earlier v0.2.18 | v0.2.19 | Reduction vs legacy |
|---|---:|---:|---:|---:|
| First light / SID | 22,552 | 8,638 | 6,496 | 71.20% |
| First light / PRG | 24,477 | 8,951 | 6,809 | 72.18% |
| Autumn at five / SID | 11,174 | 4,717 | 3,600 | 67.78% |
| Autumn at five / PRG | 13,099 | 5,030 | 3,913 | 70.13% |

Resident SID music footprint: First light **22,434 -> 6,380** bytes; Autumn at five
**11,056 -> 3,482** bytes. Resident PRG footprint, including its wrapper: First light
**24,486 -> 6,818**; Autumn **13,108 -> 3,922**. PSID headers / PRG load prefixes are
not counted as RAM. Code and embedded decoder state are counted once, with owned
zero page and replay/loader stack added. Screen, unrelated BASIC/KERNAL workspace,
other callers and ROM routines' internal stack use are outside this footprint.
The full song is not expanded into another buffer at startup or during playback.

First light selects counted per-channel phrases with register-order templates;
Autumn selects independent register-value streams with an optimized static bank.
The PRG wrapper is unchanged from the latest v0.2.18 (435 bytes); additional gains
here are music representation, not another removal of the same wrapper padding.
The earlier checkpoint-001 was a different candidate; it is not the v0.2.18 column.

[Complete PAL/NTSC measurements and hashes](SQUEEZE_MEASUREMENTS-v0.2.19.json).
Reproduce using `python scripts/benchmark_squeeze.py --json measurements.json`.
The bundled `.sidpulse` files and historical prebuilt SID/PRG fixtures are unchanged.

## Automated tests actually run

Python 3.13.5 environment:

* Existing dependency-light baseline selection: **431 passed, 3 skipped**.
* Final optimizer/channel/player-manifest/updater selection: **123 passed, 1
  skipped**. The skip is the optional independent py65 module.
* Attempted full suite using `python -m pytest -q --continue-on-collection-errors`:
  **539 passed, 8 skipped, 21 failed, 17 collection errors**. This is **not a
  full-suite pass**. Failures/collection errors report missing pygame, pyresidfp
  or py65, including the audio-worker assertion carrying the missing-pyresidfp
  exception. Skipped native integrations have not been reported as passes.

The focused tests cover exact shortest periods (including prime lengths and
partial tails), fixed-bank segmentation versus exhaustive byte-cost search,
randomized bank reconstruction/liveness, counted repeats beyond 255, all 32
checkbox combinations, independent bass/drum sharing, interleaved writes, global
controls, slow calls, both player link addresses, all five decoder families,
full loops, stop/re-init, deliberate corruption, semantic fail-closed behavior,
CPU-budget fallback, source preservation and explicit preference migration.
Updater tests cover CRLF, known multiple baselines, refusal of unknown edits and
symlinks, backups, idempotence, obsolete-file removal and rollback after failure.

Four existing PAL/NTSC legacy SID SHA-256 goldens remain exact with squeeze off.
`python -m compileall -q sidpulse scripts tests` passed. New canonical metadata
parser/manifest checks passed. No new runtime dependency is required.

## Independent machine-code checks

A local C 6510 instruction oracle, adapted from the supplied **sidreloc 1.0** CPU
source, passed **76 cases, 180,292 replay calls and 420,532 ordered SID/CIA writes**.
It executed actual assembled binaries, not just their Python data decoders.

Checks included every one of the ten compact linked images, full PAL/NTSC example
traversals and whole-loop passes, SID and compact-PRG music link addresses,
interleaved/global writes, exact gate tokens, repeated-phrase boundaries,
empty/slow ticks, init/re-init and non-looping termination. Each call was compared
against the original sequencer trace and the built-in verifier. Instruction cycle
counts agreed exactly between the two instruction implementations. Explicit gate
requests retained at least 32 cycles between surrounding SID writes. Song data
remained immutable, and writes stayed within player state, owned ZP/stack or the
specified SID/CIA registers.

The external oracle disables sidreloc's relocation analysis and instruments memory
writes. Its immediate-instruction/zero-page-STA timing and taken-branch page-cross
calculation were corrected for these cycle comparisons. It is a **CPU instruction
check, not a C64/CIA/VIC/SID simulator**, py65, or listening test. The native local
oracle binary is not shipped as an application dependency.

[Per-case results and image hashes](SQUEEZE_CPU_VALIDATION-v0.2.19.json).
The PRG checks in this pass execute the embedded music at its PRG address; this
pass did **not** rerun the complete BASIC wrapper's keyboard/KERNAL/CIA simulation.
The retained independent py65 PRG-loader tests remain part of the native release gate.

## Assembly status

A local restricted assembler reproduced the unchanged legacy music and
PRG loader images byte-for-byte. Existing single/five-stream images at both load
addresses and checkpoint raw/template images at $1000 also matched. It assembled
and reproduced the register-stream and relocated counted-channel players.

**64tass itself was unavailable.** Running the canonical build check reported its
missing executable; it did not pass. The new script rebuilds all ten compact
players, metadata and the compact wrapper with 64tass; Linux CI is configured to
run `python scripts/build_squeeze_players.py --check`, but no remote CI ran here.
Dependency downloads were attempted and failed due to unavailable DNS/network.

## Packaged-update checks

The actual generated updater/ZIP were checked against fresh copies of all three
accepted source trees: original v0.2.17, latest v0.2.18 and squeeze-checkpoint-001.
Check-only left every file unchanged; apply produced the intended target files;
repeat apply was a no-op. Known obsolete files were backed up and removed.
Private sentinel files in Git/environment/song/preferences paths survived. A
CRLF checkout was accepted, and an unexpected source edit was refused without
changing the checkout. The full archive was checked for duplicate/unsafe paths,
font binaries and private files. A fresh full-ZIP extraction completed actual CLI
SID and PRG exports and their native source saves.

## Remaining release gates

Run the complete pinned-dependency suite, including `test_channel_py65.py`, the
existing PRG/PSID tests and actual SDL dialog tests. Independently rebuild with
64tass. Verify GUI analysis, checkbox defaults/persistence, Cancel, native save,
export-only, overwrite/error handling, resizing and high zoom on supported hosts.
Run matching PAL/NTSC exports under VICE and perform audio/listening checks,
especially percussion attacks, hard restarts, sync/ring behavior, tempo changes
and complete loop transitions. Windows validation and remote CI remain outstanding.

Automatic compact-export verification reserves 20% of the timer interval plus a
128-cycle call margin. It does not model VIC DMA, unrelated IRQ/game code or analog
SID behavior. Packed players change **within-tick write spacing**. Ordered tick
and register equivalence is not sample-identical audio or a guarantee of no audible
hardware difference. No universal minimum-size or zero-regression claim is made.

## Applying the handoff

Use the uniquely versioned checked updater and incremental ZIP from the repository
parent. It accepts only known affected-file hashes from the uploaded v0.2.17,
the latest v0.2.18, or squeeze-checkpoint-001. It backs up overwritten/removed files,
refuses unknown local edits, and removes only hash-matched superseded candidate
files. Unrelated Git data, environments, songs, preferences and existing fonts
are not update targets. The full ZIP is a separate complete source snapshot.
Neither archive distributes font binaries; the existing monospace fallback remains.
