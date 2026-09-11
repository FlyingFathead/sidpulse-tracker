# SIDpulse Tracker v0.2.10

Autumn at five is the new welcome track. It is a native, editable .sidpulse
arrangement with 16 named patterns, 32 bars, eight triangle instruments, slow
envelopes, arpeggios and delayed vibrato. Duration: 96 seconds at 80 BPM.

--play-welcome-song loads and plays it directly; --welcome shows Play / Skip.
First light remains unchanged and --example opens it. Startup audio readiness,
warnings and autosave recovery are respected. The project format stays at 6.

File > Export PRG and --export-prg create a BASIC-loadable C64 program with the
same compiled music as PSID. The wrapper handles CIA timing, PAL/NTSC mismatch
and RUN/STOP exit. PAL and NTSC welcome exports are supplied in both formats.
See docs/PRG_EXPORT.md for usage and limits.

The full and incremental source archives are based on the cleaned v0.2.9
snapshot. They contain no Git history bundles, private project notes, autosaves,
user songs or environment directories. See docs/VALIDATION.md for actual checks.

## Previous checkpoint

# Checkpoint Charlie: SIDpulse Tracker v0.2.9

Documentation-only patch over v0.2.8. Public README/checkpoint/project notes no
longer contain developer-machine usernames, hostnames or private checkout paths.
Installation and handoff instructions use repository-relative or generic locations.
No functional runtime, audio, dependency or `.sidpulse` format behavior changes.

The incremental updates v0.2.8 without overwriting `user_songs`, `.venv` or `.git`.
Both archive forms extract under `sidpulse-tracker/` in the user's chosen parent
directory. See docs/VALIDATION.md.

## Previous checkpoint

# Checkpoint Charlie: SIDpulse Tracker v0.2.5

Patch over v0.2.4. Native format 6 reads formats 1–5.

- Instrument value entry opens only from a click on the yellow value field.
  QWERTY continues auditioning through field focus, sliders and graph editing.
- New project, Clear all pattern data and Clear all instruments always confirm
  with OK / Cancel, Cancel selected. Clear operations undo as a single edit.
- Always confirm quitting, including clean projects and window close. Use
  Discard & Quit, and Save & Quit for unsaved changes; default to Cancel.
- Help has aligned columns, indented explanations and ruled category titles.
- Fix instrument label clipping and reserve a solid dock for Save user preset.
- Green local modified dates in the file browser, enabled by default and
  configurable via F12 or file_browser_show_modified in preferences.json.
- Empty instrument banks save losslessly. Pattern references remain intact and
  silent until their slots are populated. PSID reports incomplete instrument use.

The incremental updates v0.2.4 without overwriting user_songs, .venv or .git.
The full archive contains restorable history. See docs/VALIDATION.md for checks
and the remaining Windows/physical-device testing limitations.

## Previous checkpoint

# Checkpoint Charlie: SIDpulse Tracker v0.2.4

Patch over v0.2.3. No project-schema change (format 5).

- Continuous SDL PCM output replaces mixer Sound chaining; useful gap counting.
- Per-voice native waveform monitors, linked General ADSR graph, menu buttons,
  centered voice/instrument text and footer rules.
- Simple audio-buffer slider; current samples/ms and OK/Cancel. Default 1024.
- Fix reproduced variable SID attacks with scheduled ADSR hard restart shared
  by native playback and the executable PSID register stream.
- First-launch logo welcome, intro-song Play/Skip, persistent first-run marker.
- Center header values vertically; center Order/Pattern/Row both ways; add padding.
- Updated PAL/NTSC First light PSID examples; musical source remains unchanged.
- Windows first-time setup lists requirements.txt and asks Continue? [Y/n].
  Ready environments start directly; N cancels before installation.

The incremental updates v0.2.3 without overwriting user_songs, .venv or .git.
The full archive contains restorable history. Physical-device/Windows testing
remains outstanding. See docs/VALIDATION.md for measurements and limitations.

## Previous checkpoint

# Checkpoint Charlie: SIDpulse Tracker v0.2.3

2026-09-10. Windows launcher patch over v0.2.2.

- `run.cmd` invokes the adjacent `run.ps1`, forwards arguments and exit status.
- Execution-policy override is confined to the child PowerShell process.
- PowerShell retains Python/venv/dependency setup and application startup.
- The dependency probe uses stdin and quiet missing-package detection to avoid
  PowerShell 5.1 native-argument quoting and first-install stderr problems.
- README Windows instructions now start with `.\run.cmd`.
- Windows CI includes the wrapper and first-run setup; it has not run here.
- Application version is 0.2.3. Native schema remains 5, compatible with 0.2.2.

Full and incremental archives use the `sidpulse-tracker/` root. The incremental
updates v0.2.2 and excludes user_songs, .venv and .git. Shipped tags are unchanged.

## Historical v0.2.2 checkpoint


2026-09-10. Patch over v0.2.1.

- Fixed rendering hover help for empty instrument slots, including after
  resizing and clicking. Browsing never creates instruments as a side effect.
- Button labels centered horizontally/vertically, with a one-pixel outline
  and consistent raised/pressed bevel, including M/S and waveform controls.
- Seven instrument-program On/Off buttons preserve values while bypassed;
  keyboard, mouse, undo, saves, user presets, native playback and PSID supported.
- Native format 5 loads formats 1–4. New user presets use format 2 and load 1–2.
- First light composition and compiled audio data are unchanged.

Full and incremental ZIPs extract under `sidpulse-tracker/`. The incremental
updates v0.2.1 with no file removals and never contains user_songs. The full ZIP
includes restorable Git history and original release tags. See docs/VALIDATION.md.

## Historical v0.2.0 checkpoint


2026-09-10. First light is now a 46.08-second SID arrangement, with a real PSID.

- F5 plays; F2 shows patterns; F6 loops the selected pattern; F8 stops.
- F4: General / Motion instrument pages. Arps, waveform/pitch tables, pulse
  movement, delayed vibrato, gate timing and retrigger work in playback/audition.
- Ctrl+Shift+F2: editable CTRL CH / FILTER rows. Ctrl+F2 remains pattern length.
- Ctrl+Shift+E: PSID export with a native-save offer. F12: PSID released/loop.
- Shift+F9: song notes; Shift+Enter adds a line. All text and music stay in .sidpulse.
- Native format 3 reads older format 1/2 files, with safe defaults and backups.

The single PAL SID exporter uses a bundled original 6510 player at $1000 and
shares repeated tick instructions. First light: 21,154 bytes, 2,305 tick records,
979 unique records, finite 12-order arrangement. The compiler reports unsupported
commands, backward order loops and memory/cycle limits instead of dropping data.
Whole-song repetition is available in F12. No SID import/digi/MIDI/PRG yet.

Full and incremental ZIPs extract under `sidpulse-tracker/` in the user-selected parent directory.
The incremental ZIP updates v0.1.1; no file removals are needed. The full ZIP has
complete Git history in bootstrap-history.bundle. Your user_songs directory is
never in the overwrite set. See docs/VALIDATION.md for actual checks and limits.
