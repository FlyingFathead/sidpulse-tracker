# SQUEEZER v2.0.2: indexed blocks and phrases

Introduced in SIDpulse Tracker v0.2.30. New installations default to v2.0.2;
explicit saved choices remain respected. v1.0, v2.0 and v2.0.1 are retained for
A/B comparison. The compiler includes their encodings as fallback candidates.
No editable song, instrument definition, native playback or automation behavior
is changed by this export-only feature.

## Why another representation helps

v2.0.1 shares literal data and sequences of packet instructions. Nevertheless,
each ordinary reference still costs three bytes and each phrase call costs four.
On the unchanged v8 stress arrangement, the best v2.0.1 register representation
contains 1,930 ordinary references and 504 calls to 158 phrase entries. Of those
calls, 369 execute once; their full addresses repeatedly occupy the stream.

v2.0.2 gives frequent literal blocks and single-execution phrases short IDs.
The dictionary stores a block's length and address once. Stream occurrences need
one byte. A zero dictionary length means a phrase entry rather than raw bytes.
Long repeated phrases still use v2.0.1's four-byte counted call.

The deterministic ranking uses occurrence counts and estimated savings:
`2 * occurrences - 3` for literal references and `3 * occurrences - 3` for
single-execution phrase calls. It retains at most 112 entries, with stable
address/length tie breaking. This is a bounded heuristic, not a global optimum.
The final candidate cost includes the complete dictionary, player and state.

## Packet format

| Tag | Meaning | Encoded bytes |
|---|---|---:|
| `00` | repeat count 1–255, phrase address LE16 | 4 |
| `01`–`0F` | inline literal length followed by its bytes | 1 + length |
| `10`–`7F` | dictionary entry 0–111 | 1 |
| `80` | return from the current phrase | 1 |
| `81`–`FF` | raw literal reference, length in low 7 bits, address LE16 | 3 |

There are three 112-byte dictionary arrays: lengths, low addresses and high
addresses. They reside directly after the entry header in the loaded image.
The arrays are immutable during playback. Long inline literals split into
15-byte chunks; phrase boundaries, shared suffix entries and all call links
are relocated accordingly. A dictionary phrase cannot call another phrase.
An indexed literal can appear inside a phrase without changing its return state.

The 6502 player distinguishes a one-byte dictionary call from a four-byte
counted call when returning, so both use the same existing per-stream state.
There is no additional per-stream mutable state, recursion or decompression
buffer. The song is decoded in place.

## RAM, CPU and evidence

For the register layout, the resident player grows from 741 to 1,161 bytes:
336 dictionary bytes and 84 bytes of decoder code. Its mutable state remains
217 bytes, already included in that player size. SID uses two owned zero-page
bytes and at most four stack bytes; the PRG wrapper adds its existing overhead.

On the unchanged native v8 stress input, packet data falls from 20,627 to
18,962 bytes. After the 420-byte larger player, the net saving is **1,245 bytes**.
SID file size falls from 21,492 to **20,247 bytes**. Measured maximum SID player
cycles increase from 8,172 to **8,287**, about 1.4%. See the release performance
report for PRG numbers, resident allocation, host RAM and repeated timings.

Every selected compact export executes the assembled player through complete
ordered SID-write, timer, loop and reinitialization checks. Dedicated tests also
compare all call cycles, writes, workspace and dictionary immutability against
an independent NMOS 6502 implementation, for all three stream modes at both
link addresses. This establishes ordered musical-event equivalence, not analog
SID identity or identical cycle spacing between every register write.

## Investigated but not shipped: arithmetic packets

A prototype used `start + delta * index` modulo 256 to replace exact arithmetic
packets. It did not infer curves or quantize automation. Applied to the best
v2.0.1 stress representation, its best whole-packet rewrite saved just one data
byte, before paying for new decoder code and per-stream state. A less compact
seed saved 114 data bytes but remained much larger overall. This route was
rejected for this release; no arithmetic decoder is included in the runtime.
This does not rule out a future run search across different packet boundaries.

## Reference study and acknowledgments

Thanks to **Lasse Öörni and the creators and contributors of GoatTracker** for
ideas on efficient music representation. The supplied **GoatTracker 2.77** source
archive was inspected; both supplied copies have SHA-256
`96c2bd6a6ab3aca2f5bb18b1c764ac6ea69ac245cae14002a72cd87c554561ef`.
Relevant areas are `src/greloc.c`'s `packpattern`, `findtableduplicates`,
`isusedandselfcontained`, and song-specific player feature selection.

Thanks also to **Luxocrates** for the supplied explanation,
[How Rob Hubbard’s C64 music player worked](https://www.youtube.com/watch?v=1YWe811rehU),
which discusses Rob Hubbard's player and Anthony McSweeney's annotated analysis.
The following are our design conclusions from those references:

| Reference idea | SIDpulse application or limitation |
|---|---|
| Omit unchanged instrument/effect fields | Needs exact state and reset semantics. Never remove a repeated SID write merely because its value matches. |
| Pattern IDs instead of repeated addresses | The new dictionary applies this general indirection principle to already resolved literal blocks and phrases. |
| Independent variable-length voice phrases | Existing voice/register layouts and one-level phrase calls already support sharing below editor-pattern boundaries. |
| Entry points inside an existing phrase | v2.0.1 already shares exact suffixes with a common return. |
| Validate table control flow before deduplication | Our host verifier checks literal bounds, phrase entries, return boundaries and no nested calls. |
| Duration events, persistent effects and transposition | Potential future native music-bytecode work, requiring exact equivalence for note articulation, reset, vibrato, pulse and filter state. Not implemented here. |
| Remove unused player features | All current layouts compete by full resident size; deeper song-specific code generation remains future work. |

These are independently implemented data-format ideas. No GoatTracker or Hubbard
player code, music data, third-party archive or supplied transcript is copied into
the release. A native note/effect interpreter could provide larger gains, but
would be a separate implementation with a substantially wider equivalence burden.

## Export comparison

All four versions are analyzed. **Show all versions** defaults on (four columns
on wide screens, two on narrow screens). Uncheck it for the best three valid
results. The Boolean `export_show_all_versions` defaults to `true` when missing
or invalid; checkbox changes save immediately and survive cancelling export
and restarting. The dropdown always offers every version.
An explicit larger choice stays selected even when it falls outside Top 3.
Switching these views never recompiles. A visible, draggable right-hand scrollbar
exposes overflow; footer actions stay fixed. Each metric's global minimum is
highlighted. Overall selection ranks valid file size, then resident bytes,
then measured maximum cycles. Complete ties retain the current choice if tied,
otherwise the newest tied version. Unknown CPU is displayed as a dash.
The comparison preference remains default-on and can be disabled.
