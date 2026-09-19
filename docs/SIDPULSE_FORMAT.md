# .sidpulse formats 6 and 7

`.sidpulse` is the editable, lossless source document. `.sid` is the compiled
PSID export. They are separate files; export does not consume or change the source.

UTF-8 JSON root: `format: "SIDPULSE"`, `format_version: 6` (ordinary projects) or `7` (row automation), `song`, `editor`.
The song keeps title, author, multiline Unicode comments, SID model, PAL/NTSC clock,
speed, tempo, pattern bank/order list, SID instrument bank, separate sample and
extension macro/filter-program banks, initial shared filter and export settings.
Opaque extension banks and unknown nested editor metadata round-trip intact even
when not playable. Unfamiliar fields are preserved with their owning objects; structurally compatible
newer versions load with warnings. Invalid core structures still fail visibly. Non-finite JSON numbers are not written.

Patterns contain 1..256 rows of exactly three cells. Each cell stores note,
instrument, effect and parameter, plus optional row automation. Notes: null empty, -1 off, -2 cut, 0=C-0 through
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
program fields to their migration defaults and control rows to empty. Loading
never changes the input file. Saves use format 6 without row automation and
format 7 when an automation value or reset is present.

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


## Format 7 and version-aware loading (application 0.2.24)

Optional Cell fields: `attack`, `decay`, `sustain`, `release` (0..15), and
`pulse_width` (0..4095). Each also accepts null/omission (hold the running value)
and -1 (restore the instrument setting). Empty fields are omitted when saving.
The fields are runtime channel overrides; the instrument definition is unchanged.
They persist through notes/instrument changes until reset or transport restart.

`editor.saved_with_version` stores the SIDpulse Tracker version that wrote the
file, independently of `format_version`. Historical files without the field load
normally. The reader uses both version information and the actual contents:

- A newer saved-with version raises a compatibility notice while loading.
- A newer schema loads when the core song/three-voice structure is compatible.
- Unknown object fields are retained with the owning cell, control cell,
  instrument, pattern, filter or song; unknown root fields are retained too.
- Known edits, native saving, copy/paste and undo preserve associated extensions.
- Unknown features are not executed. Native playback/export uses supported
  features; export reports compatibility warnings. Existing unsupported macro
  banks and effects retain their explicit export rejection rules.
- Deleting/replacing an owning object also deletes/replaces its extension data.
  Native formats do not preserve deleted objects merely for future compatibility.
- Corrupt core data, incompatible row/channel structures and out-of-range known
  values still fail visibly without overwriting the original file.

Saving retained future-format data keeps its higher schema number and stamps the
current writer version. No unused automation is added to ordinary format-6 cells,
so those ordinary saves remain readable by v0.2.23. That historical application's
strict reader cannot interpret format-7 automation; tolerant loading is provided
by this update and is the contract for subsequent readers.

An unfamiliar field that a future release introduces should be added to the
known model and migrated explicitly. Do not discard extension dictionaries or
reduce the schema marker merely because the current reader cannot execute them.
