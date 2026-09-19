# SQUEEZER v2.0.1 — repeated packet sequences as shared subroutines

Released with SIDpulse Tracker **v0.2.29**. This is an export-only addition:
native song formats, source instruments, automation and preview synthesis are
unchanged. Both **v1.0** and **v2.0** remain selectable and are still considered
as fallbacks by v2.0.1. This is resident compression; the song is never expanded
into a second C64 RAM buffer.

## Why another layer helps

v1.0 shares literal byte slices and also tries independent register streams and
counted channel phrases. v2.0 improves the host search for overlapping literal
fragments without changing that decoder. Both can still repeat a long sequence
of three-byte reference packets even though their underlying literal bytes are
already shared. v2.0.1 stores that sequence once and calls it from each use.

A read-only examination of the supplied v9 PRG found **4,059 literal references**:
12,177 bytes of reference packets beside a 12,490-byte literal bank and 304 bytes
of literal packets. Repeated groups occurred at several packet lengths. Their
potential savings overlap and must not be added together. This motivated sharing
encoded packet sequences, not just searching the literal bank more aggressively.

That v9 PRG occupies 25,986 loaded bytes; the supplied v7 PRG occupies 26,034.
The 48-byte difference compares different song revisions, so it is **not** a
controlled optimizer improvement. The measurements below use the exact same
native v8 source for all versions instead.

## Packet format and execution

| Packet | Bytes | Meaning |
|---|---:|---|
| Literal | `length, bytes…` | Length 1..127; read the following literal bytes |
| Literal reference | `0x80 + length, lo, hi` | Read 1..127 bytes from an immutable literal slice |
| Phrase call | `0, repeats, lo, hi` | Run a shared packet body 1..255 times |
| Phrase return | `0x80` | Repeat the body or resume after its four-byte call |

The addresses are little-endian and are linked after the complete layout is
known. A phrase body contains ordinary literal/reference packets and one return.
It cannot call another phrase. An identical suffix can enter partway through an
existing body and share its return. Longer repeated passages use multiple calls.

These are data-interpreter subroutines, not recursive 6502 JSR chains. Every
stream has its own repeat count and return pointer. Fixed state grows by three
bytes per stream. No extra call-stack depth, history buffer, note retrigger or
instrument reset is introduced at a phrase boundary. Streams retain independent
positions; the conductor retains one shared musical clock and exact write order.

## Search and actual memory cost

For each of the single, five-stream and register-stream layouts, the compiler
tries the smallest existing seed and a plain seed when different. It identifies
identical token sequences of 1, 2, 3, 4, 6, 8, 12, 16, 24, 32, 48, 64, 96 and
128 packets. Profit estimates count disjoint occurrences, four bytes for every
call, one return and the stored body. Adjacent repeats share a call, up to 255.
Overlapping matches in a constant run cannot inflate the estimated gain.

A deterministic greedy selection claims non-overlapping occurrences, then shares
identical body suffixes and rebuilds addresses. The search stops before this
extra pass for inputs beyond 32,768 packets or four million decoded bytes; older
candidates remain available. These are host search bounds, not song truncation.
The search is a heuristic, not a proof of globally optimal compression.

| Layout | Earlier player + state | Phrase player + state | Included mutable state |
|---|---:|---:|---:|
| Single stream | 406 B | 492 B | 17 B |
| Five streams | 474 B | 572 B | 57 B |
| 26 register/conductor streams | 580 B | 741 B | 217 B |

These sizes apply at both bundled link addresses. State is already included;
do not add it twice. The register player costs **161 extra bytes**, including
78 bytes of additional state. Its song-data saving must exceed that cost.

PSID adds a 124-byte nonresident header. PRG adds a two-byte nonresident load
prefix and a 435-byte resident compact wrapper. Compact SID ownership includes
2 zero-page bytes and up to 4 stack bytes; PRG ownership includes 4 and up to 7.
The report counts all these owned resident bytes. It does not count unrelated
screen/OS/caller RAM or promise that the remainder is all available to a demo.

## Verification and CPU tradeoff

An independent data decoder first reconstructs all original streams. It rejects
nested calls, zero repeats, bad links, missing returns, nonliteral references,
trailing packets and expansions beyond the original length. Before exporting,
the actual machine code verifies every ordered SID write, CIA write, explicit
gate-delay request, idle call, loop traversal, stop and reinitialization.

Instruction-level tests compare every callback's cycle count against an
independent py65 NMOS implementation across all three modes, both link addresses
and loop modes. Each selected callback must fit 80% of its CIA period after a
128-cycle margin. Semantic failures abort export; timing failures try another
candidate. The ten earlier player images remain byte-identical.

The new calls reduce RAM but add work at phrase boundaries. A lower output size
is not a claim of lower playback CPU. The UI compares measured worst-case **music
routine** cycles separately; PRG polling, other IRQs and VIC DMA are outside that
number. The verifier is not a full C64 emulator. Ordered musical equivalence does
not establish cycle-identical within-tick SID writes or sample-identical output
from different real SID chips.

## Measurements and findings

The release measurements and raw-record links are in
[PERFORMANCE-v0.2.29.md](PERFORMANCE-v0.2.29.md). They include the unchanged v8
stress song and all four bundled native examples, SID and PRG, three serial
trials, file size, resident ownership, maximum C64 cycles, compiler CPU/wall time
and isolated-process peak host RAM. Historical v2.0 measurements remain in
[PERFORMANCE-v0.2.28.md](PERFORMANCE-v0.2.28.md) and its linked records.

The export panel compares all three versions by default. It highlights minimum
file size, RAM and measured cycles separately and initially selects the smallest
valid file, breaking size ties by RAM and then measured cycles. Complete ties
show **Joint best** on every tied column. The current version is kept if tied;
otherwise the newer tied version is selected. Missing CPU measurements are shown
as a dash and are never treated as zero. Each column has **Use Squeezer v…**.

Comparison shares source recording, candidates and completed verification within
one immutable request. Switching completed results has no compiler cost. A saved
`export_compare_squeezers: false` choice runs only the selected version. Cancel
does not save changed settings. Only a continued export persists the choice.

## Reproduce and possible further work

```bash
python scripts/compare_squeezers.py --out comparison --isolated --write-exports
python scripts/compare_squeezers.py song.sidpulse --out stress-comparison --isolated --include-comparison --write-exports
python scripts/build_squeeze_players.py --check
```

The first command runs all bundled native songs. The second also times the
shared three-version analysis. All trials run serially and preserve source hashes.
An assembler is needed only for the optional rebuild check, not normal export.

Further gains might come from different phrase segmentation, bounded nested
calls, or native note/instrument/ramp instructions. None is implemented here.
Nested calls add state and worst-case work; native synthesis instructions require
reimplementing effect and automation semantics on the C64. Any future attempt
must count its full player/state cost and repeat the same write, RAM and CPU
checks. Merely splitting more code into routines does not guarantee a smaller
resident song.

## GoatTracker reference: compressing the instruction, not just its results

The supplied GoatTracker **v2.77** archive supersedes the earlier v2.72 excerpt.
Its manual, especially sections 3.4, 3.5, 3.6,
4.2 and 5, describes another useful level of reuse. Its packed patterns can avoid
repeating unchanged effect parameters. Instrument tables express modulation as
small programs with durations, speeds and jumps; the player generates changes.
Splitting long patterns can expose reusable pieces, and the relocator can remove
unused effects/player code and self-contained duplicate table segments.
Source reviewed: `GoatTracker_2.77.zip`, its `readme.txt` and `src/greloc.c`.
Archive SHA-256: `96c2bd6a6ab3aca2f5bb18b1c764ac6ea69ac245cae14002a72cd87c554561ef`.
This is a design study of the supplied release, not code imported into SIDpulse.

For SIDpulse, a future instruction representation could express a pulse ramp as
an initial value, increment and duration, instead of storing every resulting
value. A vibrato instruction could retain phase/speed/depth across rows until
changed or stopped. The native editing view could remain the same: this would
be an export representation with a separately verified C64 interpreter.

That differs from the v2.0.1 packet calls: those reproduce already-resolved
bytes exactly and do not understand notes or vibrato. Identical command text is
not sufficient to deduplicate execution. The supplied manual explicitly defines
which one-shot commands preserve an ongoing effect and which commands stop it;
SIDpulse must preserve its own rules, not import GoatTracker's semantics.

Likewise, skipping apparently unused pulse modulation is not automatically
lossless. Its internal phase may affect a later switch back to pulse waveform.
An optimization must maintain equivalent future state or prove a reset occurs
before that state can matter. Omitting SID writes also changes the current exact
ordered-write contract; a broader equivalence claim would require a separate
hardware-aware validation strategy. No such write elimination is enabled here.

Promising follow-up experiments are duration/delta instructions for exact ramps,
reusable native instrument programs and export-time removal of unused decoder
features. Compare complete player + data + workspace, worst-case cycles, loop and
reset behavior for every attempt. The current release retains all source data
and adds none of these unverified semantic optimizations.

### Findings from the v2.77 implementation

| Observation in GoatTracker | Relevance to SIDpulse | Status |
|---|---|---|
| Packed patterns retain command/parameter state and omit repeated changes | A native note/effect representation could be much smaller than resolved writes | Future interpreter work |
| Consecutive rests get run encoding when no instrument/effect change intervenes | Our conductor already packs empty ticks; packet calls also count repeats | Existing mechanism; keep evaluating boundaries |
| Duplicate table programs are merged only with compatible internal jumps and no external entry/exit | Reuse must preserve entry state and control flow, not just matching bytes | Current phrase bodies deliberately prohibit nested calls |
| Speed-table entries are shared; unused instrument fields can disappear | A native instrument representation could share scalar/program data | Not a saving available merely by cleaning the editable bank |
| Feature-use analysis controls assembled player sections | Our decoder could omit unused dispatch paths and inactive stream state | Separate candidate experiment; count code/state and timing |

The most contained next experiment for our current design is **exact arithmetic
run packets in register-value streams**: represent a proven sequence of values
with a start, delta and count while leaving the conductor's writes and tick
boundaries intact. It must reconstruct every original byte, including wrapping,
interruptions and split low/high register writes. This can be investigated before
a complete native instrument engine. It is not implemented in v2.0.1 and no byte
saving is claimed for it yet.

The v2.77 release history also records playback-timing changes and a preceding
fix for a packed-player feature combination. That reinforces the need for our
independent execution checks whenever decoder specialization changes code paths.
No GoatTracker source, player binary or example song is included in SIDpulse's
release archives.

## Acknowledgment

Thank you to **Lasse Öörni and the creators and contributors of GoatTracker**
for the documentation and optimization ideas that informed this investigation.
SIDpulse's implementation is independent; no GoatTracker code was incorporated.
