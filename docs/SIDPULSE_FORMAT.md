# .sidpulse format 6

`.sidpulse` is the editable, lossless source document. `.sid` is the compiled
PSID export. They are separate files; export does not consume or change the source.

UTF-8 JSON root: `format: "SIDPULSE"`, `format_version: 6`, `song`, `editor`.
The song keeps title, author, multiline Unicode comments, SID model, PAL/NTSC clock,
speed, tempo, pattern bank/order list, SID instrument bank, separate sample and
extension macro/filter-program banks, initial shared filter and export settings.
Opaque extension banks and unknown nested editor metadata round-trip intact even
when not playable. Unknown musical schema fields/versions fail visibly rather
than vanishing on the next save. Non-finite JSON numbers are not written.

Patterns contain 1..256 rows of exactly three cells. Each cell stores note,
instrument, effect and parameter. Notes: null empty, -1 off, -2 cut, 0=C-0 through
95=B-7. Pattern IDs 0..255; orders reference existing patterns. Instruments 1..99
have a separate namespace from samples. EX remains an unimplemented UI reserve.

Each pattern also has a sparse `controls` object, keyed by decimal row number.
A ControlCell has optional cutoff (0..2047), resonance (0..15), routing (0..7),
mode (LP/BP/HP bits 0x10/20/40), volume (0..15), and slide (-2047..2047).
Null means keep the running value. Zero is explicit. Slide persists until reset.
These values control one global SID filter, never a fourth sound voice.

Instruments store name, oscillator waveform 0x10/20/40/80, four ADSR nibbles,
12-bit pulse width, sync/ring, and the following native programs:

| Field | Values and meaning |
|---|---|
| arpeggio | 0..64 signed semitone offsets, -48..48; sequence loops |
| arp_speed | 1..255 ticks per arp step |
| wave_sequence | 0..64 waveform bytes; one step/tick, hold last |
| pitch_sequence | 0..64 signed semitone offsets, -48..48; one step/tick, hold last |
| pulse_depth | 0..2047 width units around base width |
| pulse_rate | 1..255 ticks per quarter of the pulse triangle |
| vibrato_speed / depth | 0..15; phase step speed*4/256, depth/16 semitone |
| vibrato_delay | 0..255 ticks before instrument vibrato begins |
| gate_ticks | 0 disabled, otherwise gate-off at that note-age tick |
| retrigger | 0 disabled, otherwise restart note/program at that interval |
| macros | Opaque future extension assignments, preserved exactly |

Song notes are full text in `song.comments`. F12 export options populate
`export_config.released` and boolean `export_config.loop`; unknown export settings
are preserved by native saves but rejected by the current compiler.

Version 1 loads with tempo 125; version 2 already has tempo. Both default new
program fields to disabled and control rows to empty. Saves always write format
6, which older builds deliberately reject. Loading never changes the input file.

Saves serialize and validate first, write a same-directory temporary file,
flush/fsync, back up the existing target as `.sidpulse.bak`, and atomically replace.
Files are capped at 8 MiB. Failed replacement leaves the old target intact.

Audio buffers, device diagnostics, mute/solo and playback marks are host/session
state. Unknown editor metadata is retained; cursor, zoom and helper visibility
are saved. No pickle or project-provided executable code is used.

Version 3 also loads. An explicit export_config.loop=false is preserved; missing loop settings use the looping default. Schema version 4 introduces PAL/NTSC acceptance and shared preview/export loop behavior. Appearance preferences and user presets are external machine files.

Schema version 5 adds seven boolean instrument fields: `arpeggio_enabled`,
`wave_sequence_enabled`, `pitch_sequence_enabled`, `pulse_enabled`,
`vibrato_enabled`, `gate_enabled`, and `retrigger_enabled`. False bypasses that
program while retaining every parameter and table. Missing switches in formats
1–4 default to true, preserving earlier sound. User-preset format 2 saves these
fields; preset format 1 remains readable. Versions before 0.2.2 reject new files
safely rather than playing disabled programs. File schema numbers are independent
of application versions.

Schema version 6, introduced in application 0.2.5, allows an empty instrument
bank and references to unpopulated instrument slots 1–99. This supports clearing
instruments without deleting any pattern data. Native playback treats these slots
as silent; adding an instrument back to a slot restores its pattern use. Native
saving preserves everything. The PSID compiler reports empty banks or references
to missing instruments in played patterns. Formats 1–5 remain readable.
