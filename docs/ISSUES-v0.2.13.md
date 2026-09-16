# SIDpulse Tracker v0.2.12 review / v0.2.13 cp001 fixes

Review date: 2026-09-16. Baseline: supplied sidpulse-tracker-v0.2.12-full.zip.
The native Broken Machine song is a separate deliverable. This report does not
contain its lyrics or install the song into the repository.

## Summary

| ID | Finding | Classification | v0.2.13 action |
|---|---|---|---|
| SP-213-01 | Supported effects report "sequencing is pending" when entered | Confirmed UI-status bug | Fixed |
| SP-213-02 | Fixed 4/16-row shading misrepresents 12/48-row shuffle layouts | Confirmed display limitation | Added configurable project-local grid |
| SP-213-03 | Modulated long songs exceed this compiler's memory region | Confirmed exporter limitation, not native-format failure | Exact diagnostics added; compact replay still proposed |

No changes to audio-buffer defaults, SID emulation, lookahead, tick timing,
player binaries or project schema are included. No C64 memory limit was simply
raised, and no musical events were discarded to force an export to fit.

## SP-213-01: misleading effect-entry feedback

**Reproduce on v0.2.12:** in F2 select the effect field, enter H, and enter a
parameter such as 34; repeat with J47 or SD1. `Editor.enter_digit` labels the
history/status operation "stored; sequencing is pending", despite these
commands being executable by `VoicePrograms` and the PSID compiler.

**Affected code:** `sidpulse/commands/editor.py`, both effect-letter and
parameter-nibble branches. Actual capabilities are in
`sidpulse/playback/voices.py::supported`.

**Fix:** use that shared capability check through `Editor.effect_edit_label`.
For implemented commands the status says e.g. `Set effect parameter H34`.
For a genuinely unsupported parameter/subcommand it explicitly says stored and
unsupported in playback/export. This is a status change, not new effect support.

**Regressions:** effect and parameter entry; H/J/SD/Q0y/absolute T; negative
cases Q1y, T1x and Dxx. The feedback checks parameters, not merely letters.

## SP-213-02: 4/16 shading on a 12/48 shuffle

**Reproduce:** open a 48-row pattern intended as one 4/4 bar at twelve rows per
quarter note. v0.2.12 highlights every fourth row and every sixteenth row. The
filter lane independently uses the same fixed four-row beat subdivision. Notes
can be correctly timed while the screen suggests a different beat structure.

**Affected code:** `sidpulse/ui/renderer.py::pattern` and its filter-lane drawing.

**Fix:** `sidpulse/ui/pattern_grid.py::PatternGrid` drives both lanes. F12 adds
rows per beat (1..256) and beats per bar (1..32), in decimal. Defaults remain
4/4. Optional editor metadata preserves the grid per project without changing
format 6, musical data, tempo, speed, effects or output audio.

**Regressions:** defaults, 12/48 and 3/9 layouts, invalid values, bounds,
unknown nested metadata and native save/load. A real App/F12 integration test
is included but skipped here because pygame-ce is unavailable.

**Deliberate limits:** phase resets at pattern row zero. Meter is not inferred
from audio or speed. Changed display metadata needs Ctrl+S and does not mark
musical song data dirty. Follow-up: a project meter/beat map with explicit
pickup and pattern-phase handling could serve mixed-meter arrangements.

## SP-213-03: native song works, expanded PSID does not fit

**Reproduce:** compile the full Broken Machine v21 Shuffle source through
`sidpulse/export/psid.py::compile_song`. The native project loads, survives an
edit/undo/redo and traverses the entire sequencer without unsupported effects,
but the compiler expands modulation into a large set of unique tick records.

The current compiler reserves $1000 through $9FFF: **36,864 bytes**. This is
its current safe output layout, not a statement that every SID player or C64
program has that universal limit. PSID file/header bytes and the much larger
JSON source-file size are separate from the resident-player requirement.

Measured requirement for this v21 Shuffle arrangement:

| Component | Bytes |
|---|---:|
| Player | 512 |
| Unique tick records | 45,380 |
| Pointer sequence including terminator | 11,748 |
| Total resident requirement | 57,640 |
| Current budget | 36,864 |
| Excess | 20,776 |

The simpler Vocal_Edit companion compiles to a 15,240-byte PSID file. This is
not the full percussion/arpeggio arrangement squeezed into a smaller file.
It retains the separate lead/bass/backing editing arrangement instead.

**Diagnostic fix implemented:** preflight all record and sequence sizes before
assigning 16-bit addresses. `ExportMemoryError`, an `ExportError` subclass,
reports the exact component sizes, budget and excess. Existing callers still
catch it. The message states that the `.sidpulse` is unchanged and distinguishes
an editable source from a compiled memory-limited export.

**Regressions:** oversized synthetic song, exact component accounting, source
immutability, and byte-identical PAL/NTSC exports of First light and Autumn at
five. Existing player, ordered SID writes and gate-settling tokens are unchanged.

### Proposed actual export improvements, not implemented in this patch

1. **Compact tick encoding.** Prototype run-length encoded pointer runs and a
   compact command stream for repeated register sets. Profile both record and
   sequence pools: pointer compression alone cannot make this song fit because
   its unique-record pool already exceeds the current budget. Keep repeated
   SID writes and the ordered gate/restart/ADSR waits when they have hardware
   semantics; do not blindly remove writes that look numerically redundant.
2. **Native tracker replay on the C64.** Store patterns, instruments, arpeggio
   tables and modulation state instead of pre-expanding every tick. Implement
   the existing E/F/G/H/J/Q/SD/SC semantics, effect memory, lookahead/restart,
   filter controls, fractional CIA timing, PAL/NTSC and loop/reset behavior.
   This is the architectural fix, not a small constant change.
3. **Measure before changing the memory map.** A larger RAM layout needs an
   audited ROM/I/O/banking plan, zero-page/stack safety and separate standalone
   PSID versus BASIC-loadable PRG constraints. Merely moving LIMIT can make a
   broken binary, and still does not solve unbounded tick expansion.

Acceptance criteria for a compact exporter: ordered register/cycle traces
against the Python sequencer, representative effect-memory and loop cases,
py65/VICE execution, PAL/NTSC timing, attack/envelope measurements, real audio
comparison, and a size test on the unmodified full arrangement. A projected
compression ratio is not yet measured, so no successful-fit claim is made.

## Validation scope and remaining checks

**Executed:** 63 focused core/update tests pass, 1 UI integration test skipped;
compileall passes. Four existing PAL/NTSC exports are byte-identical. Both
v21 source files load and round-trip, edit/undo/redo succeeds, and all 5,873
sequencer boundaries including stop execute without unsupported warnings.
Lead/bass pitch and sample-clock trigger locations match the conversion maps;
the clean companion also retains all 148 backing-note triggers.

**Not executed:** actual pygame rendering, native reSIDfp audio listening,
Windows/PowerShell launch, physical audio-device checks and C64 hardware replay.
pygame-ce, pyresidfp and py65 were not installed; the install attempt failed on
DNS. The broader test-suite attempt stopped at missing-module collection errors.
Earlier v0.2.12 validation counts are historical, not evidence for this patch.

**Song limitation:** conversion preserves the provisional v19 pitch guide; it
does not repair all remaining transcription errors. Lead onset conversion
error is at most 10.570 ms, bass at most 2.645 ms, against that MIDI source.
Those are conversion measurements, not proof that the guide itself matches
the singer perfectly. Native ADSR lookahead can shorten a preceding release;
that is existing behavior, documented in PLAYBACK.md, not newly diagnosed here.

## Installation / rollback

The versioned incremental ZIP contains only changed/new files beneath
`sidpulse-tracker/`. Unzip from the checkout's parent for a direct overlay.
Direct unzip overwrites matching files without conflict checks or backups.

The separate versioned Python launcher is the recommended checked route. Its
default is check-only; `--apply` verifies the exact archive, version and baseline
content, accepts CRLF checkout normalization, rejects conflicting local files,
stages the patch, creates a sibling `sidpulse-tracker-update-backups/` snapshot,
and writes VERSION last. It refuses target symlinks/junctions and protected
paths. Injected write failure is tested to roll back replaced files.

It does not commit, push, install packages, change `.git` or touch songs,
autosaves, virtual environments and personal preferences. Re-running a complete
update is a no-op. The backup's RESTORE.json records replaced/new files and
hashes for manual recovery; review any later edits before restoring old files.
