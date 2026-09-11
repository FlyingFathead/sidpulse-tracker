# PSID export v0.2.1

For a BASIC-loadable C64 program, use [PRG export](PRG_EXPORT.md). It wraps this
same compiled player and music stream; supported effects and limits are shared.

Ctrl+Shift+E or File > Export PSID compiles the current document, offers a native
save, then asks for the .sid destination. Export-only leaves the dirty flag and
project filename intact. F12 supplies released text and optional whole-song loop.
CLI `--export-sid PATH` always saves a sibling .sidpulse (override with
`--save-project PATH`). Existing files are backed up before atomic replacement.

The header is PSID v2NG, one song, data offset $007C, explicit load/init $1000,
play $1003, CIA speed bit 0 set, PAL/NTSC and preferred 6581/8580 flags. Extra SID
addresses are zero. Title/author/released use 32 CP1252 bytes; truncation or
substitution is reported and never changes the full native text. Header fields
follow the [HVSC SID specification](https://www.hvsc.c64.org/download/C64Music/DOCUMENTS/SID_file_format.txt).

## Compiler and player

The same Sequencer and VoicePrograms used for host playback emit ordered SID
writes for each musical tick. The compiler runs them without PCM synthesis.
Identical complete tick records share one address; a two-byte pointer sequence
retains event order. Gate transitions and deliberate repeated writes are kept.
Ordinary unchanged modulation/filter writes may be omitted by the shared engine.
This is an initial size/CPU compromise, not the final table-based event player.

The original 512-byte 6510 player image is bundled; its readable source is
`sidpulse/export/player.asm`. Optional rebuild:

```
64tass --nostart -o sidpulse/assets/player.bin sidpulse/export/player.asm
```

Each record contains CIA period LE16, idle-call count, pair count and register /
value pairs. Register token $19 means the gate-settling delay; it never reaches
SID. At tempos below the capacity of one 16-bit CIA interval, one musical tick
uses two CIA calls. Changed tempo latches are force-loaded to avoid an old-tempo
tick. Init zeroes SID, initializes pointers and plays the first tick. End cuts
the three oscillators; subsequent calls return. Loop mode restarts the compiled
stream before the terminal cut, preserving the chip's natural analog state.

The engine and export agree on musical ticks and ordered register writes.
Host PCM and C64 replay are not claimed to be sample-identical: native rendering
schedules tick boundaries at sample resolution, whereas actual 6510 instructions
consume cycles between SID writes, and CIA periods round to clock cycles. Real
SID models and libsidplayfp versions also have different analog characteristics.

## Supported music and limits

A/B/C, absolute T, E/F (normal/fine/extra-fine), G, H, J, Q0y, SCx and SDx are
supported, plus every F4 native program and control-row field. The effect help
catalog gives precise SID mappings and keeps unsupported legacy commands visible.
Instrument arps are replaced by Jxy for that row; Hxy overrides instrument vibrato.
No independent per-voice PCM volume or panning is invented.

- One PAL or NTSC SID at $D400; 6581 or 8580. No multi-SID, digi, MIDI or SID import.
- Fixed load range $1000..$9FFF (36 KiB); larger output is rejected before writing.
- Sixteen-bit pointers and at most 125 register/delay pairs per record.
- Compiler guard: 18,000 musical ticks; repeated order/row visits are rejected.
  Preview may play backward Bxx loops. For this exporter use finite orders and
  whole-song loop in F12. Pattern/order reuse through distinct orders is supported.
- Conservative per-call estimate `400 + 90 * pair_count` must fit the CIA period.
  This covers player instructions; it is not a whole-system C64 load guarantee.
- Generic extension macros/filter-program banks have no executable semantics yet
  and block export. Unreferenced PCM bank data stay in the native file with an
  export notice. Unsupported effects report pattern, row and voice.
- Current export settings: released, loop and optional load_address=$1000.
  Other settings are retained natively but rejected at compilation.

## Reproducing validation

`tests/test_psid.py` executes the actual assembled payload in py65, checks every
SID write against the shared engine, verifies timing words, loop/stop behavior,
owned memory writes and cycle budgets. py65 is a development-only dependency.

An optional independent audio check uses
[libsidplayfp](https://github.com/libsidplayfp/libsidplayfp), which emulates the
C64 CPU/CIA/SID from the exported .sid. With development headers installed:

```
c++ scripts/render_psid.cpp -lsidplayfp -o /tmp/render_psid
/tmp/render_psid examples/first-light.sid /tmp/first-light.raw 47
```

Output is mono 48 kHz signed 16-bit native-endian PCM. The supplied listening WAV
was made from this exported PSID path, not from a substitute synthesizer. See
VALIDATION.md for results and hardware/Windows limits.

PAL uses 985248 Hz and NTSC 1022727 Hz for note-register and CIA-period calculations. Musical ticks remain 2.5 / tempo seconds. Both clock variants of First light are supplied in examples/. F12 loop now applies to preview as well as export.
