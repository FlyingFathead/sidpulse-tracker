# SIDpulse Tracker v0.2.32

**PCM validation correction:** v0.2.33 fixes audible switching artifacts that
these earlier byte/register checks did not rule out. The old volume-DAC
sample-neutralization comparison also affected the other SID voices. See the
[v0.2.33 correction and playback evidence](RELEASE_NOTES-v0.2.33.md).

The song-name header opens F12 with **Song title** highlighted; the instrument
header opens that instrument in F4. F4 has **Copy instrument / Paste instrument**,
including its assigned sample. Occupied slots require confirmation with Cancel
selected first. Copying across projects reuses identical sample data or assigns
a free sample slot, preserving existing sounds. Paste is one undoable edit.

F2 has **Select all** for all rows/voices and an **Arp** button per channel.
The unused EX column becomes AR, with **0 OFF / 1 ON / R instrument / . hold**.
These channel overrides persist across notes and patterns, leave F4 definitions
intact, and are shared by playback/audio/C64 exports. OFF also suppresses Jxy;
all existing effect codes and J00 memory retain their meanings. New AR data uses
format 9; other projects keep their earlier schema. See
[arpeggio automation](PATTERN_ARPEGGIO.md).

PCM notes on tracker CH1 or CH2 previously failed C64 export. The experimental
C64 player reserves physical CH3 for its sample voice. This release maps a
single tracker PCM channel to that voice during export, preserving the native
project's layout and the sequencing order of global effects. The other two
channels and filter routing rotate with it. No runtime channel routing is added.

**Auto-remap PCM to CH3** defaults on in the PRG/RSID export dialog. A yellow
warning triangle identifies actual PCM notes outside tracker CH3. Turning
remapping off produces an actionable error for those projects. PCM notes on
multiple tracker channels still exceed this static mapping scheme and are
rejected, including non-overlapping parts; no notes are silently omitted.

One channel may alternate between PCM and ordinary SID instruments. The CH1
kick/snare example and CH1 kick/SID-noise-hi-hat/snare example were exported and
run as actual BASIC-started PRGs in VICE. The mixed example's first pattern
contains 8 kicks, 8 snares and 16 SID hi-hats; every hit was checked. An A/B PRG
with identical music/code and neutral sample data isolates the kick and snare
from the SID hats. CH3-reference and version-comparison recordings match over
their complete common prefix; the CH2 rotation has correlation above 0.999999.
The full demo also exercises the actual phrase and indexed decoders in VICE.
The added CH2 Rubber saw bass example also passes export and VICE playback:
32 bass notes accompany the percussion, with bass-band energy within 0.4% of
a manually rotated reference. Its indexed PRG is 5,654 bytes.
The later **HERMO.ROM** tester uses all three tracker channels: 16 kicks,
16 snares and 32 SID hats on CH1, 64 bass notes on CH2, and 64 lead notes on
CH3 across two patterns. Its 6,490-byte PRG passes full event/sample verification
and actual PAL VICE playback with 8580 and 6581 models. An identical-address
sample-neutralized 8580 recording confirms all 32 PCM hits and the loop restart.
The original project remains unchanged. Its listening preview uses a constant
gain increase after removing boot silence; that gain is not applied to the PRG.
These checks cover emulation; physical C64 listening remains outstanding.

The original squeezer comparison is restored for digi-enhanced exports. Its
v1.0, v2.0, v2.0.1 and v2.0.2 candidates use the real existing algorithms and
share PCM preparation. **Show all versions** can be switched off for Top 3.
The same baked sample bytes are used by every candidate. Packing affects music
data losslessly; it does not reduce PCM quality. Verified literal packing is
available when denser candidates exceed timing budgets. Packing or squeezing
off retains PCM playback with uncompressed music data.

The supplied PCM demo's PRG sizes are 31,448 / 30,468 / 26,677 / 24,918 bytes
across those versions. Its v0.2.31 PRG was 35,329 bytes. The newest candidate is
29.5% smaller. Comparison performs additional offline work; it runs in a
cancellable background process. Music instruction cycles, sample NMI timing,
VIC reserve and loop restart deadlines are checked before export.

F3 now has a top-right **Auto-squeeze on import** button, enabled by default
and saved in config. F3 and F4 imports use 4,000 Hz / 4-bit conversion in the
background, retaining the original for Restore. Disabling it preserves import
quality. An import and its optional instrument assignment form one undoable
edit. Converted samples, original data, trims and root notes remain embedded
in the native project. Existing samples are unchanged when opening a project.

A mapped F4 instrument shows **Using sample number: name** and an explicit
**Unmap sample from this instrument** button. Waveform, ADSR, pulse and sync/ring
controls are hidden while mapped; their values and programs remain saved.
Arpeggio, pitch, vibrato, gate and retrigger remain editable under **PCM
programs**, since they affect sample playback. Unmapping and undo restore the
appropriate view without erasing settings.

Validation: the final broad run exercised 1,553 cases: 1,552 passed and one
exposed an empty-instrument-bank access. After that correction, all 126 affected
regression cases passed, including the failing case and the latest UI/AR work.
An earlier complete suite passed all 1,524 cases. Exact raw PCM, conditioned PCM,
SID writes/cycles and playback state match v0.2.31 across seven songs, including
200 seconds of the supplied mixed CH1 percussion example. UI images cover
640×480, 960×1080 and 1280×900. The final 108 matched performance trials retain
zero live audio gaps/missing frames; default-buffer audio cost stays within
2% of v0.2.31. Small-buffer scheduling outliers and C64 packing CPU tradeoffs
are documented rather than hidden.
Raw validation data is under `validation/v0.2.32/`; performance results are in
[PERFORMANCE-v0.2.32.md](PERFORMANCE-v0.2.32.md).

WAV/MP3 export, the file browser, extra-loop count (default 0), sample waveform
markers and the original SID-only export remain available. C64 digis still
modulate SID master volume, so their balance differs from host PCM and between
6581/8580 models. Sample root note, gain and existing pitch/gate programs are
preserved; the update does not silently retune or boost drums.
