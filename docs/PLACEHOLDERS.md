# Remaining placeholders and disabled features in v0.2.11

The existing tracker layout is retained. The later reference mockup was withdrawn;
no mockup inspector, extra voice or new decorative controls were added. Voice
columns now have visible separators and actual scalable M/S toggle buttons.

| Visible area / feature | Status |
|---|---|
| Pattern EX column | Reserved and inactive. It does not store a fictional per-voice SID volume. |
| F3 sample bank | Displays/preserves existing bank data. PCM import, sample editing, digi conversion and sample playback are disabled. |
| Import SID / remap | Disabled. Opening a .sid does not reconstruct a .sidpulse project. |
| MIDI configuration | Disabled. MIDI input/output and mapping are future work. |
| General system configuration | Disabled. Working audio buffer controls are separately available in F12 / Settings. |
| Colour themes / fonts | Working in F12, Ctrl+F12 and Shift+F12. Shared palette overrides use preferences.json. |
| Generic macro / filter-program extension banks | Stored losslessly; no generic editor or executable semantics yet. Native F4 Motion programs do work. |
| Legacy effects shown as LATER / MAP? / DIGI in F1 | Stored when entered, but not executed. PSID export reports unsupported commands with their pattern/row/voice. |
| Stereo, panning and other single-SID-inapplicable commands | Kept in the reference/help registry as inactive or NA; no sound processing is performed. |

The fourth **CTRL CH / FILTER** lane is working automation, not a placeholder or
fourth oscillator. Arps, pitch/wave programs, pulse movement, vibrato, gate timing,
transport, native saving, song notes, PSID/PRG export, M/S buttons and the PCM meter
are implemented. The About window renders Harry's original SVG logo.

Exact shortcut visibility/availability flags are in assets/commands.json and
COMMANDS.md. Exact effect subsets and export limits are in EFFECTS.md and
PSID_EXPORT.md. Backward Bxx loops remain a preview feature; finite-order export
with optional whole-song looping is supported and clearly bounded.

ADSR, numeric sliders, arp/pitch drawing, 39 built-in presets, user preset saving, unused bank slots, PAL/NTSC and looping are implemented. The ADSR curve illustrates rate indices; it is not a measured oscilloscope envelope. Free-Hz pitch drawing and arbitrary envelope nodes are not implemented. The project still requires at least one instrument.
