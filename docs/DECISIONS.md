# Decisions recorded on 2026-09-10

Authority: PROJECT_DETAILS.md, canonical v4 handoff, and Harry's instructions
during the first implementation session. Later explicit direction wins over
earlier conflicting roadmap prose.

1. First deliverable: a real native editor with Schism-like GUI, keymapping,
   basic editing, lossless project save/load, and native SID keyboard audition.
   Review the feel before building the full sequencer/compiler.
2. Preserve the common song/status header and F-key page structure shown in the
   supplied Schism screenshots. Default palette follows the warm beige/black/
   green/yellow example. DejaVu Sans Mono is rendered at actual font size.
3. Resizing plus independent user zoom supersedes the older fixed 640x400-ish
   passage still present later in v4. More space exposes more rows; large zoom
   scrolls to the active voice rather than making text tiny to fit three lanes.
4. Three hardware SID voices by default. An optional fourth **GLOBAL** lane is
   a future control lane for the shared filter/master-volume/timing state, never
   an extra hardware oscillator. The first schema still stores exactly 3 voices.
5. **Instruments by default.** F4 has SID synthesis controls. Oscillator waveform
   selection belongs here and uses four Schism-style buttons. Vibrato, pitch,
   retrigger/gate programs and macro assignments belong to instrument behavior
   too, as their tick semantics are implemented. Vibrato shape is distinct from
   the SID oscillator waveform. Do not inherit fake single-SID panning controls.
6. F3 remains the independent sample bank for later PCM import and digi conversion.
   Instrument 01 and Sample 01 can coexist. Exportable digi techniques need a real
   timing/CPU/chip-model plan; merely storing PCM does not make it playable on C64.
7. Top-right level meter/scope uses real generated PCM, never randomized activity.
   This is mono because the first target is one SID. Scope is magenta; level
   information comes from DC-removed RMS/peak measurements of the same output.
8. `.sidpulse` is always the editable source. Exporting PSID must leave it intact
   and offer native Save/Save as for dirty/unsaved work. The .sid exporter comes
   after composition semantics; arbitrary SID remapping is later still.
9. Export compiler can deduplicate patterns/instruments/macros, encode empty-row
   runs and reuse repeated state. Measure byte cost and cycle cost separately.
   Decoder overhead may cost cycles; smaller is not automatically faster.
   Never omit semantically meaningful SID writes (especially GATE/ADSR) solely
   because a register value repeats. Host-vs-C64 register traces are the planned gate.
10. MIDI, collaborative editing, browser builds and multi-SID remain future work.
11. Unimplemented features remain visible as disabled grey menu selections.
    Their shortcuts report the pending feature without triggering a different action.
12. F1 stays context-sensitive quick help with a topic menu at the top. Number
    keys, Left/Right/Tab and mouse choose topics; Escape returns to the previous page.
13. A central command/shortcut registry stores destination, applicability,
    implementation, active-binding and independent visibility flags. It drives
    actual key dispatch and help/menu availability, not just a decorative table.
14. Optional bottom helper uses smaller scalable text and responds to focus/hover.
    Visibility is an editor setting; changing it does not alter song data.
15. Deliver frequent numbered "checkpoint charlie" ZIP pairs for hands-on review,
    with the same full/incremental/SHA-256 contract as project releases.

No PSID code, sample mixer, web frontend or fabricated C64 output is shipped in
this milestone. The immediate review question from v4 is whether this feels
like Impulse Tracker / Schism Tracker under the fingers.

16. Single SID is the first and only implemented target: three oscillator voices
    and one shared filter. The fourth visible area is labelled CTRL CH / FILTER
    in blue-grey. It reserves automation rows and links to working filter settings;
    it is not a fourth playable voice.
17. Each voice has [M] and [S] monitor buttons. Preserve Alt+F1..F3 for direct
    muting and Alt+F9/Alt+F10 for the current voice. Solo is exclusive and toggles
    back to the prior mute set; no source notes or export settings change. F2
    audition uses its actual pattern voice; F4 keyboard jazz allocates three voices.
18. Keep an explicit effects capability catalog. Inapplicable mono panning is
    different from an unimplemented effect or an undecided SID mapping. PSID is
    a replay-code container, not an IT effect engine. Never promise hardware
    support from a filename or reuse an IT letter silently with new semantics.

19. Harry approved the initial view and requested First light playback next,
    with the next checkpoint named v0.1.1. Playback is the priority; audio-buffer
    controls support any slow/overloaded PC and are not NUC-specific tuning.
20. Keep one SID. F5 starts a stopped song and otherwise shows Info. Repeated-F5 restart is configurable, off by default; Ctrl+F5 always restarts. F6
    loops a pattern, F7 uses the playback mark/current row, and F8 stops.
    UI page/focus/resize operations release audition keys without stopping song
    transport. Tracker time comes from PCM sample counts, not UI events.
21. Audio diagnostics report observed queue starvation, long worker scheduling
    intervals and render-time budget. They do not claim to identify every
    hardware/driver fault. Buffer preferences are per-machine, not per-song.

## v0.2.0: musical programs and PSID output (2026-09-10)

The user's latest request prioritizes instrument effects, patterns, a reimagined
First light, actual PSID output and lossless .sidpulse. Generic future extension
banks remain intact in the native format. Song notes belong there too; exported
PSID carries only its standard metadata. SID import remains future work.

The first compiler runs the shared tick semantics into deduplicated register
programs. An original fixed-address 6510 interpreter handles timing and writes;
it is deliberately bounded to single PAL SID output and finite order traversal,
with an optional whole-song repeat. This is a documented first exporter, with
explicit rejections rather than silent musical omissions. The generic optimized
instrument/event player envisioned in v4 remains a later compiler evolution.

Ctrl+F2 keeps Schism pattern length. Ctrl+Shift+F2 adds filter focus and
Ctrl+Shift+E adds PSID export; Shift+F10 continues the previously shipped Save As.
F4 General/Motion tabs retain the separate F3 sample namespace. New format 3
reads formats 1/2 and safely preserves all newly implemented program fields.

Harry clarified that voice tracks need visible separators and M/S must be real
scalable buttons. All voice columns now have continuous bevelled gutters; M/S
are lettered rectangular controls with raised/off and inset/coloured/on states.


## Checkpoint 0.2.1 (user-selected version)

Retain the existing tracker layout. Include separated voices in playback, native
PAL/NTSC and shared loop control, fixed post-fade audition, graphical instrument
sliders/ADSR/arp editing, real buttons and safe dialogs. Add scrollable unused slots
and Choose preset / No preset / Manual. Catalog has 39 built-in sounds in nine
categories plus a user bank. Themes/fonts are persistent machine settings; default
crimson and dark text on beige. About is framed/centred with an x and requested
blank line. No multi-SID or sample/digi importer is added. Full plus incremental
0.2.0-to-0.2.1 ZIPs are the deliverables. See INSTRUMENTS.md and APPEARANCE.md.
