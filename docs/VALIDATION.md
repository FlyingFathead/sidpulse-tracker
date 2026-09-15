# Checkpoint v0.2.12 validation

Validation for the 2048-sample default-buffer patch. Project format remains 6.

- Fresh/missing/invalid audio-buffer preferences resolve through
  `DEFAULT_BUFFER = 2048`; an explicitly saved supported value still wins.
- The staged slider still cancels without changing machine state and applies the
  next step from the new default (2048 -> 4096) when requested.
- Current help, README and the example preferences file report 2048 samples /
  approximately 42.7 ms per 48 kHz block.
- Existing v0.2.11 startup-splash behavior and historical validation remain
  unchanged below.

Validation:

- `python -m compileall -q sidpulse tests` passes.
- A direct isolated-preferences regression passes: no file -> 2048; explicitly
  saved 1024/4096 values are retained; invalid or malformed values -> 2048.
- The full pytest suite was rerun on the updated v0.2.12 tree after installing
  the declared development dependencies: 274 tests passed.

## Previous validation

# Checkpoint v0.2.11 validation

Linux, Python 3.12, pygame-ce 2.5.7, pyresidfp 0.17.0, SDL dummy video/audio.
**274 tests pass**, including 39 startup/audio-settings checks.

- Normal startup shows the splash repeatedly until explicit opt-out. Both OK
  and Play save the checked and unchecked states while preserving unrelated
  preferences. Missing, malformed and non-boolean flags default to showing it.
- Upgrades with v0.2.4/v0.2.10 first-run markers still show the new splash with
  an unchecked box. Existing markers are left intact and no longer consulted.
- --welcome overrides opt-out, displays its saved state and allows re-enabling.
  Keyboard focus, Shift+Tab, Space, Escape, mouse controls and preference-write
  failure handling are covered. Failed writes show a notice before demo playback.
- The real application entry point (without --headless-smoke or --welcome) was
  launched with clean settings and SDL dummy drivers. Its splash rendered;
  clicking Play demo song started native reSIDfp playback of Autumn at five.
- Actual screenshots were inspected at 1280x900 and at 480x360/360x360 with 300%
  UI zoom. Logo, version, both buttons and the small lower-left checkbox fit.
- Both source archives are assembled from the supplied v0.2.10 file set plus the
  splash preview. Overlaying the incremental reproduces the full release files;
  no removals, user preferences, songs, environments or Git state are included.
- Bundled song assets, native audio modules and export modules are byte-identical
  to the supplied source. Application version is 0.2.11; project format stays 6.

Windows and physical audio-device execution remain untested here. Dummy SDL
checks validate the UI/native playback path, not an actual sound device.

## Previous validation

# Checkpoint v0.2.10 validation

Linux, Python 3.12, SDL dummy video/audio. **255 tests pass.**

- Autumn at five round-trips through the native format and loads into independent
  editable documents. First light's original example files remain byte-identical.
- Both PAL and NTSC welcome PSIDs compile without warnings. py65 executes the
  entire 3,072-tick arrangement and its loop transition; every ordered SID write
  matches the native sequencer, including arpeggios, filter and delayed vibrato.
- The native reSIDfp preview is rendered through the application's output
  conditioner. The 96-second listening WAV has no clipped samples. Independent
  libsidplayfp renders of both PSIDs run for 100 seconds, including the loop,
  with nonzero audio and no clipped samples.
- The PRG tests execute the assembled loader and player with scripted CIA flags,
  keyboard input and KERNAL API stubs. They cover both clocks, no-timer idle,
  slow ticks, tempo changes, mismatch exit, RUN/STOP, saved zero page/CPU flags,
  menu/CLI export and atomic file replacement/backup failure handling.
- Reassembling the PRG loader reproduces the bundled binary byte for byte.
  An offline wheel build includes the welcome source and loader, excludes asset
  backups, and exports a PRG from outside the source checkout.
- Startup tests cover explicit welcome playback, first-run state, First light,
  disabled/initializing audio, startup notices, F8 cancellation and recovery.
  A real headless welcome playback launch succeeds. Welcome and PRG dialogs
  were visually checked at 1280x900 and 480x360.
- Full and incremental ZIPs are compared against the cleaned v0.2.9 snapshot.
  Overlaying the incremental produces the same release files as the full ZIP
  while retaining user songs, autosaves and environment/Git state. Archives
  exclude private project notes, Git bundles, backups and generated build files.

This update has not been run on Windows, in VICE or on physical C64 hardware.
CPU tests use ROM API stubs and cannot verify the complete machine environment.
The independent PSID audio render exercises libsidplayfp's C64 emulation; it does
not exercise the BASIC PRG wrapper. Native and exported PCM are not claimed to
be sample-identical. The project format stays at 6.

## Previous validation

# Checkpoint v0.2.9 validation

v0.2.9 is a README/docs cleanup over v0.2.8.

- Tracked text contains no developer username, workstation hostname, home-directory
  checkout path or private working-directory reference.
- README install/update examples use the archive location chosen by the user and the
  repository-relative `sidpulse-tracker/` directory.
- Version metadata is 0.2.9. No functional runtime, audio, dependency or native
  project-format behavior is changed by this patch.

## Previous validation

# Checkpoint v0.2.8 validation

Linux, Python 3.12, SDL dummy video/audio. **232 tests pass.**

- Ctrl+F2 opens the new linked slider/value dialog. Dragging reaches 001 and
  256; only clicking the yellow field activates typing. Three-digit input
  updates the slider; a fourth digit and nonnumeric text are ignored.
- Invalid 000/999 values cannot apply. OK resizes, while Cancel/Escape leave
  the project unchanged. One undo restores removed notes and filter rows.
- The dialog captures the original pattern so playback-follow changing the
  viewed pattern cannot redirect the resize to another pattern.
- Controls fit 1280×900, 480×360 and 800×600 at the tested zoom levels. The field
  stays centered under the slider and clear of the buttons. The application
  screenshot was inspected for spacing, alignment and readable labels.
- Full and incremental ZIPs pass extraction and launch checks. The incremental
  overlays 0.2.7 while preserving songs, autosaves and the Python environment.
- Windows execution remains untested here. This patch changes the pattern-length
  dialog; the audio engine and saved project format are unchanged.

## Previous validation

# Checkpoint v0.2.7 validation

Linux, Python 3.12, SDL dummy video/audio. **224 tests pass.**

- F5 policy is checked in stopped, playing and paused states, with the option
  On and Off. Ctrl+F5 always queues a restart at order 0, row 0.
- Missing or malformed preferences default Off. Mouse and keyboard toggles
  persist across launches, preserve other preferences, and do not dirty songs.
- Native restart/deadlock regressions explicitly enable the option and pass.
- The full and incremental ZIPs pass extraction and launch checks. The update
  overlays 0.2.6 and preserves user songs, autosaves and the Python environment.
- Windows execution remains untested here. The audio engine itself is unchanged
  from 0.2.6; this patch changes transport policy and its saved setting.

## Previous validation

# Checkpoint v0.2.6 validation

Linux, Python 3.12; SDL dummy video/audio. **210 tests pass.**

- Reproduced three-note/F5 freeze in the old path: the worker held Python's GIL
  in pygame AudioDevice.pause while SDL waited for a callback needing the GIL.
  A forced in-flight callback independently reproduced the same deadlock.
- Safe pause/close now pass that forced callback test in bounded subprocesses.
  The exact note/F5/stop/shutdown stress scenario completed 100 cycles (~21 s).
  Suite regressions include 15 F5 restarts and 120 switches between two sparse
  patterns of different lengths while editing and using F5/F6.
- All 29 physical piano scancodes work through both F2 NOTE positions in all
  three voices. Caps Lock previews from all nine voice fields without edits.
- Autosave tests cover five-minute timing, unchanged snapshots, new projects,
  dirty status, original-file preservation, one-minute/custom/disabled settings,
  live-instance exclusion, unclean recovery load/skip, write failure and retry.
- A caught main-thread exception writes a report and an emergency .sidpulse;
  an audio callback failure is logged once and its output silenced. A short
  native-watchdog deadline verifies persistent thread-stack capture.
- F11 tests exercise contiguous three-digit input, automatic next-row advance,
  Delete/undo, appending at the first --- row, rejecting out-of-range IDs, and
  selecting an unused pattern from the bank and opening it in F2.
- F11 and autosave controls fit 480×360, 980×780 and 1440×1050. Actual screenshots
  were inspected for black number columns, names, dim --- entries and settings.
- Full/incremental archives pass extraction and launch. The update overlays the
  actual 0.2.5 full ZIP; user_songs/autosave/.venv/.git sentinels remain intact.
  The full Git bundle restores to the release commit.

The pinned pygame-ce Windows wheel contains pygame/SDL2.dll at the path used by
the new control helper. Windows runtime and physical-device execution remain
untested here. No claim is made that every reported Windows failure shares the
reproduced deadlock; persistent reports support further diagnosis. Format 6 is
unchanged from 0.2.5.

## Previous validation

# Checkpoint v0.2.5 validation

Linux, Python 3.12; SDL dummy video/audio. **187 tests pass.**

- Actual mouse/key events verify QWERTY audition across General, ADSR, Motion and
  Arp/pitch parameter focus, and inside preset drafts. Typing and Enter leave
  instrument entry closed. Clicking yellow fields opens entry; sliders do not.
- New/Clear commands and quitting tested with clean/dirty projects, window-close
  events, Enter/Escape cancellation and clicked acceptance. Confirmation buttons
  remain inside 480×360, 980×780 and 1440×1050 viewports.
- Clear-pattern undo/redo preserves arrangement, pattern dimensions/names and
  every other bank. Clear-instrument undo preserves all pattern data. An empty
  bank round-trips through format 6, renders on all pages, stays silent in native
  playback and can be repopulated. PSID reports an empty bank explicitly.
- Timestamp formatting uses a controlled file modification time. Default,
  persistence, toggling and malformed-preference fallback are covered.
- Help columns/rulers, complete field labels, the preset button dock, file dates
  and confirmation buttons were inspected in application screenshots.
- Existing continuous-stream audio, native envelope timing, save/load and 6510
  export execution regressions pass. No audio-output backend changes in this patch.
- Both archives are checked by extraction and launch. The incremental overlays
  the actual 0.2.4 full ZIP; tracked bytes match and user_songs/.venv/.git sentinels
  survive. Full-bundle Git restoration resolves to the release commit.

Windows and physical audio-device execution remain untested here. This patch
does not add new claims about their performance. New native saves require 0.2.5;
older format 1–5 projects still load.

## Previous validation

# Checkpoint v0.2.4 validation

Linux, Python 3.12. **162 tests pass.** SDL dummy video/audio are used here.

- Continuous PCM callback tests preserve every sample through uneven callback
  sizes, count starvation episodes, and recover without dropping queued PCM.
  Eight seconds of native playback with 806 UI redraws, repeated page switches
  and resizes produced zero callback starvation episodes with a 1024 buffer.
  A further 50-second run with 4,355 UI redraws also recorded zero audio gaps.
  The earlier short-Sound queue repeatedly drained in the same redraw workload.
- Native scopes isolate the selected voice, stay independent of audible PCM
  (allowing the emulator's tiny analog-noise variation), and track model/clock
  changes. Scope rendering is requested only while Info is visible.
- General-page envelope dragging updates the saved ADSR values; slider changes
  reposition the graph handles. Undo restores both through the shared model.
- Audio slider: mouse drag, keyboard steps/focus, cancel without changes,
  explicit apply/persistence, preference-write failures and resized dialogs.
  Default is 1024; an explicitly saved buffer remains selected.
- Native ENV3 regression measures real attack onset, beyond register parity:
  PAL/NTSC, tempos 125/137/255, and repeated loop restarts. Regular attacks
  previously varied by about 34 ms; tested attacks now reach ENV3 >=200 within
  5 ms (typically 2–3 ms at tempo 125).
- Existing exported 6510 execution tests still match all ordered SID writes.
  Both updated PSIDs were independently rendered for 48 seconds through
  libsidplayfp, producing audio in early/middle/late sections and loop restart.
  PAL export: 22,552 bytes. NTSC export: 22,504 bytes. Source duration: 46.08 s.
- First launch loads First light; Play waits for audio startup if needed; F8
  cancels a pending intro; Skip persists the marker. Subsequent normal launches,
  explicit project opening, --welcome and headless checks are covered.
- Audio/welcome/header screenshots inspected at normal and small viewport sizes.
- Windows Python/version probes exercised with installed and missing packages;
  requirements are read directly, and interpreter path parsing checked. CI covers
  declining setup, accepting setup, and a ready environment. Windows/WinGet
  execution and physical audio-device timing have not been tested here.

Restart preparation can shorten the previous note's tail. Retriggers with less
than 40 ms available and unscheduled keyboard notes retain native chip behavior;
this patch does not claim to cure every possible host/device dropout.
The .sidpulse schema is unchanged. Package extraction/update checks compare
tracked files and preserve user_songs, .venv and existing Git state.

## Previous validation

# Checkpoint v0.2.3 validation

This patch changes the Windows launcher, README, release metadata and CI.
The 135-test Linux application suite passed for v0.2.2; application behavior and
native schema are unchanged in this launcher patch. A Linux headless launch
checks the updated version. No new Windows runtime result is claimed.

- CMD wrapper reviewed against Microsoft PowerShell -File/ExecutionPolicy docs.
- Windows line endings, adjacent quoted script path, argument forwarding and
  exit-status forwarding checked in both release ZIPs.
- Embedded Python dependency probe exercised with installed pinned packages
  and an empty environment. Both return the expected code without stderr.
- Full archive and incremental over v0.2.2 must match tracked files and keep
  user_songs/.venv intact. The full history bundle includes unchanged old tags.
- Windows CI now exercises `run.cmd --headless-smoke --example`, including
  creating a fresh virtual environment. That CI job has not run here.

## Retained v0.2.2 validation


Linux; Python 3.12, pygame-ce 2.5.7, pyresidfp 0.17.0 and py65 1.2.0.
**135 automated tests pass.**

The reported empty-slot crash was reproduced by moving the pointer over the
actual slot hit rectangle before rendering. The new regression failed with
KeyError before the fix. It now covers slots 05, 08, 16, 18 and 99, mouse clicks,
resizing through 1440x1050, 980x780, 480x360 and 1280x960, and Enter/creation
while the mouse remains over the bank. Browsing preserves the original song.

Each of the seven program switches has sound-register checks: Off matches a
neutral program; On restores the original sound; parameters remain intact.
Project saves and user presets round-trip each disabled switch. Old projects
load with switches On. Invalid non-boolean switches fail validation. Each
exported PSID is executed in py65 and every ordered SID write compared with
the host sequencer. Mouse/arrow/Enter toggles, undo and shared roll-page state
are covered. First light's compiled PSID remains byte-identical to v0.2.1.

Actual application screenshots were visually inspected for centered button
labels, one-pixel outlines and raised/pressed bevels. SDL dummy video/audio
are used for automated checks; physical-device and Windows testing is pending.
Full and incremental-over-v0.2.1 archives are checked by extraction, tracked
file comparison, CLI export, native audio startup, and pointer/resize checks.

## Retained v0.2.1 validation


Linux; Python 3.12, pygame-ce 2.5.7, pyresidfp 0.17.0 and py65 1.2.0.
**114 automated tests pass.** The retained tests cover editor operations, shortcuts,
resize/zoom, project backups/migrations, native audio and 6510 export.

New regression coverage includes:

- Mouse slider gestures with bounds, one-step undo, and numeric entry from both
  clicks and highlighted fields. Dragged ADSR decay/sustain updates, serialization
  and undo. Drawn arps interpolate skipped mouse events; step deletion works.
- Raised tab focus with Tab/arrows/Enter; Enter opens Presets/Manual; draft changes
  stay out of the song until Add. Cancelling numeric entry returns to the draft.
- Empty slots and creation into a chosen slot, cancellation of deletion, remapping
  of used instrument IDs, deep-copied factory presets and persistent user presets.
  All 39 categorized built-ins validate as SID instruments.
- Ctrl+Q button mouse actions and default cancellation; About close button.
  Theme/font persistence and valid/invalid colour overrides.
- PAL and NTSC both produce native audio, the expected A4 frequency register,
  correct PSID clock flags and CIA timer latch. Project round trips retain clock.
- Natural song looping restores speed, tempo, filter/volume and tick programs;
  explicit old loop=false remains false. Keyboard audition produces audio after
  a zero-volume ending. Held-note edits reach the native ADSR register state.
- Actual exported 6510 code executes in py65 with every ordered First light SID
  write compared to the shared host sequencer; memory and cycle budgets checked.

Both First light exports were independently rendered for **48 seconds** using
libsidplayfp 2.6.0, executing the PSID C64 code. Each has sustained audio in early,
middle, late and restarted-loop sections. Musical length is 46.08 seconds in both
clock modes; composition and instrument data are unchanged from 0.2.0.

| Export | Bytes | Tick records | Unique records | Compiler cycle bound |
|---|---:|---:|---:|---:|
| PAL | 21,148 | 2,304 | 978 | 3,910 |
| NTSC | 21,094 | 2,304 | 976 | 3,820 |

Screenshots are captured from the actual pygame application. Full and incremental
over-0.2.0 extraction must match tracked source files, preserve user_songs, launch
native playback with clickable M/S controls and reproduce the bundled CLI export.
The full ZIP includes restorable Git history and release tags.

Host tests use SDL's dummy audio device. No physical C64, real sound-card latency,
Windows runtime test or remote CI run is claimed. Native and independent emulator
PCM are not claimed sample-identical: CPU write timing and analogue models differ.
The ADSR graph illustrates chip rate settings; it is not a measured envelope.

Run `python -m pip install -e '.[dev]'`, then `python -m pytest -q`.
Independent rendering instructions are in PSID_EXPORT.md. No extra runtime
library is needed for export beyond the existing application dependencies.
