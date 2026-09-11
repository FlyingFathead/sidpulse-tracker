# v0.2.10

- Add direct PRG export in File > Export PRG and --export-prg. The BASIC-loadable
  program uses the compiled SID player, checks PAL/NTSC compatibility, follows
  CIA tempo changes and returns to BASIC with RUN/STOP. No external assembler
  or disk-image utility is required. Include PAL/NTSC welcome PRG examples.
- Make Autumn at five the welcome song: a 96-second, 80 BPM arrangement with
  filtered triangles, slow attacks, gentle arpeggios and delayed melody vibrato.
  Its patterns, instruments and song notes are an editable bundled .sidpulse.
- Add --play-welcome-song to load and start it without the welcome dialog.
  Wait for audio initialization and startup notices; accepting autosave recovery
  cancels pending intro playback. --silent still opens the editable arrangement.
- Keep First light and its PAL/NTSC examples unchanged. --example always opens it.
- Include the native welcome project in installed packages and both source ZIPs.
  Source deliveries contain no Git history bundles or private project notes.

# Earlier UTF-8 preset fix

- Read user presets explicitly as UTF-8, matching the writer. Preserve accented
  and other Unicode instrument names on Windows with a non-UTF-8 text default.
- Add preset round-trip regression checks using a simulated Windows-1252 default.

# v0.2.9 — README and docs update

- Remove developer-machine usernames, hostnames and private checkout-path references
  from tracked project documentation; use repository-relative or generic paths.
- Update README/checkpoint installation and delivery examples for v0.2.9.
- No functional runtime, audio, dependency or `.sidpulse` format changes.

# v0.2.8

- Replace the Ctrl+F2 text popup with a 1–256 row slider and a centered yellow
  three-digit value field underneath. Slider and typed values stay linked.
  Only clicking the value field starts typing; accept up to three decimal digits.
- Stage the new length until OK; Cancel/Escape preserves the pattern. Reject
  values outside 001–256. Resize the pattern that opened the dialog, even if
  playback-follow changes the viewed pattern. One undo restores removed notes
  and filter rows together.

# v0.2.7

- Make restart on repeated F5 a saved machine preference, OFF by default.
  F5 starts a stopped song and otherwise shows Info without resetting playback.
  Enable Restart on repeated F5 in F12 or Settings Menu > F5 restart option.
  Ctrl+F5 always restarts. Update help and the preferences example accordingly.

# v0.2.6

- Fix the reproduced GIL/SDL callback deadlock during playback transitions and
  device close. Device control releases the GIL while waiting for callbacks.
- Every F5 press restarts the complete song, including during playback.
- Accept all piano keys in both F2 NOTE subcolumns; Caps Lock previews from
  every voice field without editing its value.
- Add crash logs for Python, audio threads/callbacks and native faults, plus
  thread dumps after a 15-second UI stall. Keep the Windows console after errors.
- Add autosave On/Off, a 1–60 minute slider (default 5), folder selection and
  Create folder / Retry. Auto-create the Git-ignored autosave directory; warn
  with OK if unavailable. Keep timestamped, atomic recovery projects separate
  from normal saves. Offer recovery after unclean exit, skipping live instances.
- F11: order-number gutter and narrow black pattern-number column, pattern
  names alongside, and complete pattern bank with row counts and unused status.
  Type three decimal digits to apply and advance; Delete shifts following order
  entries up. Tab switches panels; bank Enter opens the pattern in F2.
- Project format remains 6; 0.2.5 projects remain compatible.

# v0.2.5

- Keep QWERTY audition active while editing instruments. Only clicking a yellow
  value field opens manual entry, including preset drafts and sequence length.
- Always confirm New project and quitting, with Cancel initially selected.
  Quit buttons say Save & Quit / Discard & Quit / Cancel as appropriate.
- Add Clear all pattern data and Clear all instruments below New project.
  Both default to Cancel and perform one undoable edit on acceptance.
- Support empty instrument banks and preserved references to empty slots in
  native playback and .sidpulse format 6. Read formats 1–5; reject incomplete PSID
  exports with a useful error.
- Organize help in aligned columns, with indented entries and ruled headings.
- Prevent left-edge label clipping; put Save user preset below the instrument
  list on a solid dock with space before the footer.
- Show local modified dates in green in the file browser. Default on; toggle in
  F12 or through file_browser_show_modified in preferences.json.

# v0.2.4

- Replace short mixer-Sound chaining with continuous SDL callback output and
  a bounded PCM reserve. Count actual software starvation episodes, excluding
  startup, pauses and idle silence.
- Add separate native per-voice scopes in playback panels, with centered text.
- Add the linked draggable ADSR graph to General, beside the numeric sliders.
- Render main/submenu choices as outlined bevelled buttons; separate footer groups
  with horizontal rules and center instrument field text vertically.
- Replace raw audio-buffer entry with a staged slider and OK/Cancel. Default
  1024 samples; show buffer duration in milliseconds and retain saved preferences.
- Prepare scheduled SID envelope retriggers using register-only hard restart;
  remove the reproduced approximately 34 ms variation in regular percussion attacks.
- Share restart preparation with PSID export and regenerate PAL/NTSC examples.
- Add first-run welcome with the original SVG logo, version, First light and
  Play intro song / Skip intro song buttons. Remember completion in first-run.json.
- Vertically center header values, center Order/Pattern/Row horizontally and
  add inner padding to Song Name/File Name/Instrument.
- Windows setup checks the installed runtime and requirements, prints requirements.txt
  and asks Continue? [Y/n] before installing Python or packages. N cancels setup.

# v0.2.0 — 2026-09-10

- Give each voice a visible vertical gutter and scalable, bevelled M/S toggle buttons.
- Preserve Harry's original SVG logo; display it in About and README.

- Recompose First light: 46.08 seconds, 12 orders, eight patterns, nine SID instruments.
- Add native instrument arpeggios, waveform/pitch tables, pulse movement,
  delayed vibrato, gate timing and retrigger, including keyboard audition.
- Execute E/F/G/H/J/Q0y/SCx/SDx with documented SID-specific units and memory.
- Add sparse shared-filter pattern rows, Ctrl+Shift+F2 focus and undoable editing.
- Export actual PSID v2NG with original 6510 replay code and deduplicated records.
  Validate ordered writes by CPU execution and render the .sid through libsidplayfp.
- Extend native format to v3, retaining older-file migration, extension banks,
  Unicode multiline song notes and atomic save/backup behavior.
- Add native-save offer in GUI export, paired CLI export/source saving, released
  metadata and whole-song loop options, explicit unsupported-feature diagnostics.

# Changelog

## 0.1.1 — 2026-09-10

- First light song playback on one native 6581/8580 SID. Audio-sample-clocked
  rows/ticks, fixed voice lanes, instrument memory and gate/release/cut handling.
- F5 song/Info, Ctrl+F5 restart, F6 pattern loop, Shift+F6 current order,
  F7 playback mark/current row, Ctrl+F7 mark, Ctrl+F6 pattern from row,
  F8 stop, Shift+F8 pause, and Scroll Lock/Ctrl+F tracing.
- Playback continues through page changes, help, resize and focus loss.
  Musical edits are delivered as snapshots at the next row boundary.
- Live Axx/Bxx/Cxx and absolute Txx effects; all other commands remain explicitly
  unsupported and preserved. No new C64 export claims.
- Settle SID startup DC, add host DC removal and 5 ms transport ramps.
  Default audio buffer 2048 samples; selectable 256..8192 with persistent
  machine preferences, queue-gap/late-wake/render-load counters.
- Cache repeated text surfaces to reduce GUI work on slower machines.
- Project format 2 adds tempo; old files load with tempo 125. Source data is
  preserved and older application versions reject the newer format clearly.


## 0.1.0 – 2026-09-10

First native SIDpulse Tracker editor and keyboard-jazz milestone.

- Implemented pygame-ce shell, Schism-style persistent header and function-key pages.
- Added scalable text/layout, adaptive scrolling at 50–300% zoom, and fullscreen.
- Added explicit editor operations, 128-entry undo/redo, three-voice patterns/orders,
  Schism physical note mapping, instrument digits, note cut/off, row/block operations.
- Added version-one `.sidpulse` projects, guarded loading, atomic saves and backups.
- Added native reSIDfp 6581/8580 keyboard audition, three-voice note allocation,
  independent audio worker, PCM-fed scope and RMS/peak meter.
- Added SID instrument controls and waveform buttons; retained a separate sample bank.
- Added starter instruments/project, launch scripts, tests, Git bootstrap/remote scripts.
- Added central registry of 247 command groups / historical shortcuts with context,
  routing, applicability, implementation, binding and visibility flags.
- Added grey unavailable menus/shortcuts, contextual F1 topic navigation, and an
  optional small bottom help strip responding to focused/hovered controls.

Sequencing, executable effects/macros, PSID/PRG export, sample/digi conversion and
MIDI are explicitly pending. This release is the first handoff review point,
not the full roadmap MVP.

- Single-SID [M]/[S] voice monitoring and blue-grey CTRL CH / FILTER reserve.
- Declarative effects help catalog with explicit pending/mapping/digi/NA status.
