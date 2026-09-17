# SIDpulse Tracker File Squeezer

**v0.2.21 source candidate. Export-only; enabled by default.** Applies to `.sid`
and `.prg`, never the editable `.sidpulse`, preview, undo, editor pattern numbers,
or native format version. This is a resident representation, not a disk cruncher
that expands the full song into another RAM buffer.

## Controls and source preservation

```text
SIDpulse Tracker File Squeezer
[x] Squeeze song
    [x] Condense duplicate patterns
    [x] Condense identical instruments
    [x] Discard unused patterns, instruments and samples
    [x] Pack repeated voice/timing data; choose smaller player

Analyze       Save + export       Export only       Cancel
```

The existing SID/PRG dialog, keyboard controls, destinations and overwrite checks
remain. Missing/invalid preferences default on. The master switch retains the
sub-option values. Confirmed choices live in machine `export_squeeze` preferences,
not the song. Earlier candidate `compact`/`phrases` opt-outs and the old
`export_squeezer` container are read where present. Cancelling does not save edits.
Analyze can take several seconds: the host compiler tries alternatives and
executes the selected player for verification.

### Responsive pre-analysis (v0.2.21)

The dialog is drawn immediately, before the analysis job starts. A pinned bar
above the scrollable controls sweeps the theme's `SLIDER` fill colour back and
forth, with no knob or draggable surface. It stays visible at high zoom and
small window sizes. The elapsed time is real, but the bar is **indeterminate**:
there is no fabricated percentage or ETA for the optimizer's variable workload.

Status follows the actual compiler phases: Pre-analyzing, Recording playback,
Checking source preservation (when needed), Squeezing song, Verifying playback
(when a compact candidate qualifies), Preparing export and Preparing PRG.
Recording status includes the count of musical ticks already processed.

A coordinator thread copies the song and owns a private pipe and a spawned Python
compiler process. The display thread only draws and polls immutable status.
The worker does not call pygame, open audio, write files or save preferences.
Explicit `spawn` avoids forking an already multithreaded SDL/audio application.
All process startup, pipe reads and termination/joins occur off the display thread.

While analysis is active, options and Analyze/Save/Export controls are disabled;
Cancel remains available by mouse, Escape or the default focused button. Cancel
terminates/discards that job without saving anything. Window events and quit
confirmation remain responsive. A failed worker produces a visible error and
allows retry instead of leaving the activity bar running indefinitely. Quitting
also cleans up a job temporarily hidden under another modal.

The same path handles explicit Analyze and a Save/Export that requires changed
options to be recompiled. The requested save/export continues only after success
and comparison with the original song snapshot. A cancelled or superseded result
cannot open a file browser, save preferences or replace a later dialog.

CLI compilation remains synchronous and does not start a process or draw a bar.
The Python compile functions accept an optional `progress(phase, detail)` callback;
callbacks do not change the selected player or the resulting bytes.

Cleanup uses a deep copy. Identical patterns/instruments compare all stored
musical fields, ignoring display names. It preserves order-list positions and
therefore Bxx/Cxx destinations. Only patterns outside the playlist are unused;
referenced instruments and the implicit initial instrument are retained. A second
trace of the original source verifies that any performed cleanup preserved
playback. Save + export saves the complete original project, never this copy.

The current SID-only sequencer has no PCM trigger/playback. Its unplayed PCM bank
can be dropped from the export copy; the native bank stays intact. The legacy
exporter already omitted native instrument/pattern/sample banks from the binary.
Those cleanup statistics are **not** claimed as additional target-byte savings.
The substantive gains come from the playback encoding below.

## Reusable channel phrases without a new editing workflow

The compiler records the existing sequencer's complete ordered tick trace. It
then compares these complete resident alternatives:

* The exact legacy tick-record representation.
* Single or independent voice/global byte streams, using the earlier packer and
  a new static phrase-bank, byte-cost-based refinement.
* Independent register-value streams: one stream for each written SID register,
  plus an explicit conductor. This lets pulse/frequency or other repeated values
  share storage even when adjacent register values vary.
* Counted channel phrases, with raw write packets or shared register-order
  templates. Each voice has its own phrase cursor. A separate conductor retains
  the tick timing and exact order of voice/global runs.

Thus a changing lead need not duplicate the bass/drum passage. Source pattern
boundaries are not storage identities. A distinct fill stays distinct, and a
phrase boundary never implies a note retrigger or an instrument reset. Reuse is
based on actual executed events, not a guess from matching note names. No writes
are sorted, dropped or quantized; repeated writes and explicit gate delays remain.
The channels have independent **data positions**, not independent musical clocks.

This does **not** yet add a native note/instrument-program synthesis engine. It
still represents the existing sequencer's resolved actions. Translating those
programs into compact native synthesis instructions remains separate work.

## Actual byte costs and bounded search

For byte streams, a static immutable bank is assembled from useful literal
fragments with exact substring/overlap sharing. Dynamic programming chooses
literal packets versus references by encoded cost, considering every match
length 4..127. References cost three bytes; literals cost their length plus one.
Unreferenced bank spans are removed and all absolute addresses rebuilt.

For counted channel phrases, a bank stores pointers to shared event packets.
A four-byte descriptor contains phrase length, repeat count and its absolute
address. Both length and repeat count are 1..255. Different channels can use
different lengths. KMP computes the true shortest period of candidate passages,
including non-power-of-two lengths and a final partial repeat. Descriptor-cost
reparsing tries ordinary lengths and counted repetitions; unused bank intervals
are discarded. Longer passages/repeat counts use multiple bounded descriptors.
Register-order templates store common register sequences once and separate their
values, without changing ordering. The raw-packet alternative remains available.

The search is deterministic and bounded: at most 64 indexed positions per key,
127-byte / 255-word phrase limits, two byte-bank refinements per mode, and capped
host-side word-refinement work. The original seeds remain candidates. Segmentation
is cost-optimal for the indexed byte-bank matches; dictionary discovery and word
repeat discovery are heuristics, **not a global minimum-size proof**.

Selection counts code, embedded state, data, wrapper, zero page and owned stack.
It requires a strictly smaller file and no increase over legacy resident RAM.
It chooses the smallest eligible resident result; ties prefer smaller files and
lower conservative cycle estimates. Only the selected player is exported. A
smaller but too-slow candidate is rejected; the legacy encoding remains the final
fallback. Unhelpful compression never justifies dropping notes or truncation.

## Verification and timing contract

Every candidate's independent data decoder reconstructs the original ordered
ticks, delays and timer/idle information. A selected compact candidate then runs
its actual assembled machine code in a bounded, dependency-free instruction
verifier before export. It checks a complete pass, a complete second pass for
looping songs, all slow-tempo idle calls, termination and reinitialization.

The verifier checks ordered SID writes, explicit 32-cycle gate-delay tokens,
ordered CIA latch/control writes, memory ownership, return/stack discipline and
instruction cycles. Each callback, including init/re-init and stop, must fit
80% of its CIA period **after adding a 128-cycle margin**. A CPU-budget failure
tries another layout. A semantic mismatch aborts; it is not silently hidden by
fallback. Bundled player images are also checked against their SHA-256 manifests.

This is **not a full C64 emulator**. The reserve does not prove scheduling safety
under arbitrary VIC DMA, other IRQs, game/demo work or sample playback. Compressed
and legacy players differ in within-tick instruction/write spacing. Ordered
musical equivalence is not a claim of cycle-identical writes, sample-identical
PCM, or universally identical real-SID attacks. Independent CPU and native
GUI/audio/VICE/hardware release checks are described in
[the validation record](VALIDATION-v0.2.19.md).

## Resident memory and bytecode

| Component | Bytes / address |
|---|---:|
| Legacy player | 512 bytes; ZP $F8..$FB; 2 owned stack bytes |
| Single byte-stream player/state | 406 bytes; ZP $F8..$F9; 4 stack bytes |
| Five byte-stream player/state | 474 bytes; ZP $F8..$F9; 4 stack bytes |
| Register-value player/state | 580 bytes; ZP $F8..$F9; 4 stack bytes |
| Counted raw channel player/state | 462 bytes; ZP $F8..$FB; 4 stack bytes |
| Counted template player/state | 474 bytes; ZP $F8..$FB; 4 stack bytes |
| PSID load / init / play | $1000 / $1000 / $1003 |
| Compact PRG wrapper / music load | 435 bytes / $09B4 |
| Legacy PRG wrapper / music load | 2,047 bytes / $1000 |
| Whole PRG-owned ZP / stack | 4 / up to 7 bytes |

State is already inside the player size; it is not counted twice. The PRG's
printer uses all four ZP bytes even with a two-byte-ZP music decoder. This release
corrects that earlier accounting omission. The wrapper's title, clock check,
CIA polling and RUN/STOP restoration are unchanged from the latest v0.2.18.

Byte-stream packets use tags 1..127 for literals and $81..$FF for a length plus
LE16 pointer to an immutable literal slice. No recursive references or history
window exists. Single/register conductors encode register IDs and values (or a
value-stream read), gate delay, tick end, song end, timer change and empty-tick
runs. The five-stream conductor encodes ordered voice/global runs instead.

Counted streams use `[length, repeats, address-lo, address-hi]` descriptors and a
zero terminator. The address references a literal pointer-word bank. Those words
point to immutable write packets or timing schedules, optionally using shared
register-order templates. Decode state is fixed and does not grow with song size.

All images must end below $A000. The existing 18,000-tick guard and unsupported/
backward-order-flow restrictions remain. PSID's 124-byte header and PRG's two-byte
load prefix are not resident song data. Reported RAM excludes unrelated screen,
BASIC/KERNAL workspace, external callers and ROM-internal stack usage; it is not
a claim about total machine free memory.

## CLI, measurements and rebuilding

```bash
python -m sidpulse song.sidpulse --export-sid song.sid
python -m sidpulse song.sidpulse --export-prg song.prg
python -m sidpulse song.sidpulse --export-sid song-legacy.sid --no-squeeze-song
python scripts/benchmark_squeeze.py --json squeeze-measurements.json
```

CLI export preserves the existing native-save behavior. It does not read GUI
preferences; defaults and explicit `--squeeze-*` / `--no-squeeze-*` flags make
scripted runs reproducible. Python API: `compile_song(song, squeeze=False)` or
`compile_prg(song, squeeze=SqueezeOptions(...))`. Neither preview nor ordinary
project saves invoke the export squeezer.

Bundled example measurements are in
[SQUEEZE_MEASUREMENTS-v0.2.19.json](SQUEEZE_MEASUREMENTS-v0.2.19.json). Existing
prebuilt example SID/PRG files are historical fixtures; re-export native projects
to exercise the new compiler. No external cruncher or assembler is needed at
runtime. For developers, `python scripts/build_squeeze_players.py --check` uses
64tass to independently rebuild all ten linked compact players, their metadata
and the compact PRG wrapper. Linux CI now includes that check.
