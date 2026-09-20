# Changelog

## v0.2.38

- Fix whole-page font shrinking on entry to F2/F5 when fitting extra channels.
- Preserve the selected font when a complete voice and essential rows fit;
  narrower pattern views follow the selected channel automatically.
- Retain the minimum-size fallback for small windows and large zoom.
- Rendering-only hotfix; audio, sequencing, fitting and exports are unchanged.

## v0.2.37

- Centered file browser selection, with stable mouse double-click targeting.
- F5 Info −/+ and header triangle buttons skip song orders without restarting audio.
- Exact frozen reference kick/snare in the built-in Wavetable drums category.
- Install/check FFmpeg before Windows CI media tests.
- Matched 2048/512 performance checks; see RELEASE_NOTES-v0.2.37.md.

## v0.2.36

- Suspend redundant stopped-state synthesis and redraws, preserve release tails
  and command wake-up, and vectorize display metering during playback.
- Add serial baseline/candidate runtime checks with 2048 default / 512 stress.
- Lower spawned compiler priority on POSIX during export contention; retain
  measured 512-sample export underruns in the performance report.
- Settle offline SID candidates before fitting; exclude the startup decay.
- Fit drum pitch decay with weighted least squares and compare short attacks,
  multi-resolution spectra, native onset energy and snare noise/body balance.
- Keep generated instruments frozen and compatible with normal SID/PRG replay.
- Rename native project Save As to **Save as .sidpulse...**.
- Introduce the tracker before development priorities in README, and document
  both Git-clone and release-ZIP installation.
- Include the fitted reference drum project and measurements; preserve both
  DIGI methods and all four SQUEEZER versions, defaulting to v2.0.2.

## v0.2.35

- Restore packed volume DIGI as method #1 and the default, preserving display enables.
- Keep waveform-DAC DIGI as method #2 with its explicit display-blanking warning.
- Add an export method selector, persistent preference and --digi-method CLI option.
- Preserve current trigger/remapping/squeezer behavior and close the bias voice on stop.
- Keep sample-to-SID synthesis preferred and the three-choice export popup.
- Move the changelog into docs/ and include incremental-update cleanup.

## v0.2.34

- Move arpeggio/checkpoint guides into docs/, fix links, and remove obsolete root notes.
  Include cleanup for obsolete files left by incremental ZIP extraction.
- Add the PCM export warning with Continue as DIGI / Synthesize all samples / Cancel.
  Recommend synthesis, audition all replacements, preserve slots and source samples,
  and apply the complete batch as one undoable edit before reviewing ordinary SID export.
- Add W waveform automation with numeric/letter aliases and instrument/table reset.
- Add persistent sync and ring modulation FX in the previously unassigned SID macro range.
- Preserve envelope gate, waveform-table age, instrument settings and PCM isolation.
- Integrate column selection, edit masks, clipboard, undo, help, native format 10 and export.
- Preserve saved cursor fields across the layout change and fit the additional column.
- Include the supplied synthwave kick and snare reference WAVs unchanged.

## v0.2.33

- Repair experimental C64 PCM with a stabilized waveform DAC, neutral-state
  retention, mixer startup ramp and explicit PCM/SID ownership handoff.
  Blank the display and sprites during playback; expose the tradeoff in export.
- Add selected-range normalization and a 0–200% relative volume dialog.
  Preserve originals, trim markers, storage format, undo and embedded saves.
- Add saved normalization before/after squeezing options and the F3 experimental notice.
- Add cancellable sample-to-SID waveform/pitch table fitting, source/result
  audition, a 99-slot instrument browser, overwrite confirmation and undo.
- Add instrument Freeze/Unfreeze and persistent sample-synthesis provenance.
  Generated instruments start frozen; pattern automation and playback remain active.
- Keep the existing WAV/MP3 export, loop count, PCM mappings, best-of-version
  music squeezing and SID-only player. No new dependency is required.


## v0.2.32

- Make header song/instrument fields open F12/F4; highlight Song title.
- Add F4 instrument copy/paste, including assigned samples, occupied-slot
  confirmation, and a single undo step. Preserve conflicting sample slots.
- Add F2 Select all and persistent per-channel arpeggio OFF/ON/default in
  the previously unused EX column, now AR. Preserve existing effect meanings.
  Save format 9 only when arpeggio row commands are present.
- Restore real squeezer version comparison and Top 3 for PCM-enhanced PRG/RSID
  exports; include phrase and indexed C64 music decoders with timing checks.
- Auto-remap one tracker PCM channel to hardware CH3 during export; rotate
  SID voices/filter routing, warn with a triangle, and preserve the project.
- Support alternating PCM drums and ordinary SID instruments on that channel.
- Add default-on F3 **Auto-squeeze on import** with a saved preference,
  background 4 kHz / 4-bit conversion, and a restorable embedded original.
- Show sample mappings in F4, hide inapplicable SID controls, and add explicit
  unmapping. Keep PCM pitch/gate programs editable and SID settings saved.
- Validate actual PRG playback in VICE with CH1 kick/snare and mixed SID
  hi-hat arrangements plus CH2 bass; check channel/decoder equivalence and PCM isolation.


## v0.2.31

- WAV/MP3 output browser with format selection, 0–99 extra loops (default 0),
  background rendering, cancellation and atomic replacement with backup.
- Embedded PCM sample bank, instrument overrides, F3 waveform start/end
  markers and numeric edits, root note, gain, squeeze/restore and undo.
- Separate experimental C64 PCM-enhanced RSID/PRG routine: two SID voices plus
  channel 3 packed volume digis, verified memory and instruction budgets.
- Preserve ordinary SID player selection; add supplied synthwave PCM drum
  demo and format-8 persistence without upgrading ordinary SID-only projects.
- Correct the optional C64 render utility's default subsong selection for RSID.
- Regression, independent 6502 interruption, emulation and matched performance
  checks documented with raw results.

## v0.2.30

- Show all squeezer versions by default, save the display choice in config,
  retain optional Top 3 ranking, and add reusable overflow scrollbars.
- Supplied SP application icon and optional Linux desktop launcher.
- Actual F5 playback GIF/MP4 below the README logo.


- SQUEEZER v2.0.2: indexed immutable blocks and phrase calls, with complete
  player/dictionary RAM accounting and earlier encodings retained.
- Four-version export comparison adapts to narrow windows; preserves ties,
  immediate selection, cancellation and saved preferences.
- Documents GoatTracker 2.77 and Luxocrates' Hubbard-player reference study,
  independent implementation, rejected arithmetic prototype and measured limits.
- Repeats full regression, 6502, source-preservation and matched CPU/RAM checks.

## v0.2.29 - SQUEEZER v2.0.1 and measured export comparison

- Share identical packet sequences with non-recursive calls, counted repeats and
  common suffixes; include the new decoder/state cost in resident-size selection.
- Preserve both earlier optimizers, players and explicit saved selections.
- Compare v1.0/v2.0/v2.0.1 in three columns by default, highlight minima and select
  the smallest valid output. Each column has its own Use Squeezer button.
- Share source recording, candidate construction and verification inside one
  cancellable comparison; switching completed results does not recompile.
- Add a saved comparison toggle, current PRG version credits, independent 6502
  checks and matched export/native performance reports. No native format bump.

# v0.2.28 - distinct version for the revised automation and squeezer build

- Bump application, launcher and package metadata to 0.2.28. New native saves
  and squeezed PRG credits report the same version.
- Give full/overlay archives, checksums and current release documents unique
  v0.2.28 names; retain older documents and benchmark records as history.
- Include inline channel A/D/S/R/PW recording, direct Disarm, centered banks,
  SQUEEZER v2.0 with selectable v1.0, and measured UI caching improvements.
- Preserve musical format versions, dependencies and executable run.sh.

# v0.2.26 - clipboard feedback and Modern keyboard mapping

- Give clipboard and octave buttons a pressed state, release-inside activation,
  drag-away cancellation and a short visible response for quick clicks.
- Show clipboard success/empty/error notices above F8: SILENCE, including for
  keyboard actions and Paste Special. Preserve the selected field masks.
- Add a saved Modern/Classic keyboard profile in Settings Menu and F12. Default
  to Modern with Ctrl+Insert copy and Shift+Insert paste in F2. Retain Alt+C/O in
  both modes and the previous Ctrl+Insert roll action in Classic.
- Add Oct: current value [+1] [0] [-1] controls, including F3/F4. In Modern mode,
  + / - / 0 also change/reset octave there. Reset means octave 4; limits are 0..7.
- Keep pattern numeric input, text dialogs, song data and instrument definitions
  intact. Reset user settings restores Modern. No dependencies or format changes.
- Add instrument M/S beside activity dots, with press feedback and monitoring
  based on actual triggers across all voices. Combine with channel monitoring;
  leave song registers and exports unchanged. Sample M/S is visibly unavailable.
- Hide PW recording options and their keyboard focus while disarmed. Show
  Record to channel only when armed, with a configurable red REC_ARM color.
- Display ADSR resets as R. Add staged R/RA/RAL entry in PW to restore all five
  overrides atomically; R then Enter restores only PW. Add Reset all automation
  button/menu action for selected rows/channels, preserving notes and FX.
  Keep existing reset serialization, and defer VB because Hxy already exists.

# v0.2.25 - field clipboard, compact playback and reset settings

- Select F2 fields with mouse drag, Shift+click, Shift+arrows or a field-header
  click. Copy, cut, overwrite, insert, mix and roll respect selected fields.
  Keep legacy whole-channel block commands and one-step undo.
- Add optional clipboard buttons, Pattern Edit Menu and Paste Special choices
  for notes, automation or both. Notes means NOTE; automation means A/D/S/R/PW.
- Collapse/expand the shared control/filter pane in pattern and Info views;
  default to collapsed at narrow widths and save explicit visibility choices.
- Show red per-channel scopes at narrow widths. Add a saved visualizer switch
  which disables display-only scope processing as well as drawing.
- Add Reset all settings to defaults at the bottom of Settings Menu. Default
  confirmation to Cancel, retain song/preset/recovery data, and restore the old
  output if saving the reset preferences fails.
- Retain the existing music format, automation recording and export behavior.
  Update the application writer stamp to 0.2.25.
- Print a versioned, terminal-width startup banner from both launchers, warning
  against closing the console or using Ctrl-C with unsaved work.

# v0.2.24 - channel automation, PW recording and compatible loading

- Add per-channel A/D/S/R/PW fields after the existing NOTE/IN/EX/FX fields.
  Preserve full 12-bit PW, per-parameter resets, held-note control and the
  existing instrument programs. Use teal automation colors.
- Add audio-clocked, row-quantized PW touch recording with a visible channel
  target, one pattern pass per gesture, cancellation and one-step undo.
- Replace stale instrument edit text with per-cursor and live-gesture status.
- Keep the blue shared-filter lane in pattern and playback views; publish live
  filter/slide state and retain its display after stop or pause.
- Stamp native saves with the app version. Keep ordinary saves compatible with
  format 6; use format 7 for new row automation. Load structurally compatible
  future versions with warnings and retain unknown fields through native edits.
- Extend native load/save, real audio-process recording, 6502 export and UI tests.

# v0.2.23 - output devices and test arpeggio

- Add SDL playback-device selection and a saved `audio_output_device` machine
  preference; `null` uses the system default. Linux and Windows share the same
  SDL API and spawned-process implementation.
- Add a quiet, faded C-E-G-C test, Refresh outputs and staged Reset defaults to
  Alt+F12. The test uses the selected draft output/buffer without saving settings,
  changing SID state, advancing song time or discarding queued music.
- Confirm successful output changes before saving. Restore the previous output
  on open/save failure; use the default if a saved or restored device disappears.
- Preserve playback pause state and session diagnostic counters when reopening.
- Retain the 0.2.22 process isolation, native sound path, buffers, dependencies,
  song format 6 and exporter/player binaries.
- Replace a timing-sensitive restart-test assertion with an observable rewind
  assertion; 60 Hz telemetry can skip the original sub-5000-frame startup window.
- Add device/preference/UI and real spawned SDL integration coverage; record
  matched 0.2.22/0.2.23 measurements in docs/VALIDATION-v0.2.23.md.

# v0.2.22 - isolated audio and underrun diagnostics

- Run native synthesis and SDL output in a spawned audio process. Keep commands
  and display snapshots on IPC; never transfer PCM through the UI process.
- Optimize PCM FIFO copies and host conditioner loops while retaining sample
  ordering, DC filtering, transport ramps, rounding and SID register events.
- Add independent missing-frame and late-callback diagnostics. Detect callback
  delays even when the existing software PCM queue never becomes empty.
- Bind previously unused Alt+F12 to audio settings. Add a persistent, default-on
  `audio_underrun_detection` checkbox/config boolean for unobtrusive lower-left
  warnings. Preserve raw test counters when notifications are disabled.
- Retain 2048-sample defaults, saved buffer overrides, native format 6, runtime
  dependency pins, scopes, editor controls and export/player data.
- Include reproducible baseline/candidate benchmarks, identical-initial-state
  native PCM comparisons, failure injection and full regression results in
  docs/VALIDATION-v0.2.22.md. Hardware results are not inferred from dummy SDL.

# v0.2.21 — responsive export analysis

- Remove synchronous SID/PRG compilation from menu and dialog event handlers.
  Paint the first analysis frame before starting a background job; isolate the
  CPU-heavy compiler in a spawned Python process, with copying, IPC and cleanup
  managed outside the SDL thread.
- Add a pinned animated slider-colour activity bar without a knob, real compiler
  phase labels and elapsed time. Do not invent a percentage or time remaining.
- Keep resize, repaint, quit confirmation and Escape/Cancel responsive. Prevent
  duplicate submissions; discard cancelled/stale results and surface worker errors.
- Continue Save + export / Export only only after successful re-analysis of changed
  options. Keep preferences and all file writes in the original explicit UI flow.
- Preserve squeeze defaults, native songs, player binaries and export encodings.
  Extend worker lifecycle and SDL workflow tests without weakening replay assertions.

# v0.2.20 candidate — validation repairs

- Correct the development-only py65 1.2.0 DEC-absolute cycle-table typo using
  an instance-local test adapter (six cycles, not three). Preserve upstream
  instruction execution, installed packages, and the correct production verifier.
- Keep strict replay cycle/write comparisons; use the same reference adapter for
  SID, PRG, stream and channel tests. Add independent manual-based DEC/idle-path
  regression tests, adapter isolation checks and fail-closed metadata guards.
- Update the program-edit/save/export integration test to assert the actual
  File Squeezer dialog, prepared result and preserved source before exercising
  the existing complete native-save and SID-export workflow.
- No player binary, encoding, optimizer, sequencer, UI behavior, native song
  format, dependency pin or default export option changes. See
  `docs/VALIDATION-v0.2.20.md` for the exact validation scope and remaining gates.

# v0.2.19 candidate

- Add counted per-channel phrase/repeat reuse and shared register-order templates.
- Add independent register-value streams with an ordered global conductor.
- Add byte-cost dynamic-programming phrase-bank refinement, exact period search,
  unused-bank pruning, full resident-cost selection and bounded searches.
- Verify selected machine-code playback, timer/idle behavior, whole-loop traversal,
  stop/re-init, owned writes and a 20% instruction-cycle reserve with 128-cycle margin.
- Verify performed cleanup against the untouched original source trace.
- Correct compact PRG ZP accounting; preserve earlier explicit squeeze opt-outs.
- Keep exact legacy output on opt-out, no native format/editor/synth changes.
- Add independent CPU tests, reproducible benchmarks and canonical 64tass/CI checks.
- Provide checked, backed-up migration from the supplied original and known v0.2.18
  candidate trees, removing only hash-matched superseded candidate files.
- This source candidate still requires complete native GUI/audio/VICE/hardware validation.

# v0.2.18 candidate

- Add default-enabled, export-only **SIDpulse Tracker File Squeezer** to SID/PRG
  export, with individually controlled source cleanup and resident stream packing.
- Pack independently repeated voice/global/timing streams and compare a smaller
  single-stream encoding; read immutable shared literal phrases directly on C64.
  No full-song decrunch buffer, recursive references or lossy event simplification.
- Preserve source projects, preview, undo, implicit instrument memory and order
  positions; canonicalize only exact synthesis/program fields and pattern/control
  contents on an isolated export copy. Report that unused banks were already absent
  from legacy target images rather than attributing imaginary savings to cleanup.
- Use 406/474-byte player/state images and a 435-byte contiguous PRG wrapper;
  retain title/author, PAL/NTSC checks, CIA polling and RUN/STOP return. Preflight
  the complete target image and report code/data/wrapper/ZP/stack footprint.
- Verify decoded timed events before linking, enforce conservative per-tick CPU
  costs and retain exact legacy output when disabled or a smaller safe packed
  layout is unavailable. Logical equivalence does not imply cycle-identical writes.
- Persist machine-only export preferences with enabled migration defaults; add
  deterministic CLI opt-outs without importing GUI/audio backends for CLI export.
- Add squeezer/CPU/GUI regression tests and assembly rebuild checks; regenerate
  existing bundled SID/PRG examples with default squeezing. Add system monospace
  fallback when the optional supplied font is absent; existing font overrides stay.
- Native format remains 6; preview/sequencer, dependencies and audio settings are
  unchanged. See the validation report for checks performed and open release gates.

# v0.2.17

- Rename the startup splash's ambiguous `OK` action to **New song**.
- Make New song and Escape create a genuinely blank `Untitled` project instead
  of leaving the preloaded `Autumn at five` demo in the editor.
- Keep **Play demo song** loading/playing the bundled editable demo as before.
- Keep the startup opt-out preference, explicit `--play-welcome-song` path, audio
  startup handling, native song format and dependencies unchanged.
- Add regression coverage for replacing the loaded demo with a blank project and
  for the default New song keyboard action.

# v0.2.16

- Use one visible directory-list browser for Load, F10 Save, Save As and SID/PRG
  export destinations. Remove modal filename prompts from those paths.
- Add inline Unicode filename/directory carets, selection, insertion/deletion,
  Home/End, word movement, clipboard commands and horizontal scrolling. Keep
  directory traversal from erasing filename edits; prevent piano/AltGr routing
  from invoking unrelated project commands while a text field is active.
- Prefill the latest successful native project name and directory. Save starts
  before its extension without select-all, enabling small revision-name edits.
- F10/menu Save always browses; Ctrl+S/W remains quick-save outside the picker.
  Browser quick-save submits the visible draft. Keep the current page on a
  non-browser quick-save; update defaults after successful open/save/recovery.
- Preserve existing atomic writers and `.bak` files, Cancel-default overwrite
  checks, save-before-export continuation, unsaved state and native source paths.
  Retain drafts on I/O failures and check edited directory paths before writes.
- Correct effect-entry status; add configurable display-only beat/bar shading and
  exact oversized SID-export diagnostics with the clear instruction to shorten
  or simplify projects that exceed the compiled-player memory budget.
- Add direct octave-digit entry without changing pitch class/instrument/effects.
- Add actual-trigger/gate instrument activity dots; keep sample indicators idle
  until PCM/digi playback exists.
- Draw ADSR attack `00` vertically in the schematic envelope view without changing
  actual SID timing.
- Add F11 song-end loop control synchronized with F12 and fix final-row loop-state
  handling; F6 pattern looping remains separate.
- Replace stale v0.2.12 installation text with v0.2.16 full-release/checksum
  instructions and separate local maintenance patches from public release assets.
  Update release guidance and remove obsolete private-handoff wording.
- Native song format, dependency pins, saved audio settings and the compiled SID
  export memory budget remain unchanged. WAV/MP3 export and compact SID-player
  encoding are not included.
- Maintainer Linux validation before release: **693 tests passed** and both
  headless smoke tests completed successfully. See `docs/VALIDATION.md` for the
  stable release-validation procedure.
# v0.2.15

- Add F4 activity dots driven by actual instrument triggers and gated voice IDs,
  including delayed notes, retriggers and keyboard/cell/row audition. Keep them
  separate from selection, memory-only rows and PCM sample IDs. Mutes/pause/reset
  suppress indicators; a short UI fade makes fast notes visible.
- Reserve the sample-bank indicator area but explicitly keep it idle until PCM
  playback is implemented. Dots are activity, not measured envelope/volume meters.
- Remove the ADSR graph's artificial 4% minimum attack width: 00 is vertical and
  draggable to the left edge. Label the graph schematic and show approximate SID
  attack time; 00 still means the fastest hardware rate, not a changed zero time.
- Expose the shared song-end loop flag at the bottom of F11 with ON/OFF wording
  and L; rename its F12 alias. Preserve project defaults, undo/save and separate
  F6 pattern looping. Fix queued final-row loop edits being honored too late.
- Keep lookahead probes out of activity telemetry and cell/row audition IDs in
  the audio message. No dependency, native song-format or buffer setting changes.
- Cumulative checked parent-directory update over supplied 0.2.12/0.2.13/0.2.14;
  previous octave, grid and oversized-export message repairs are retained.
- 273 core tests passed, 4 pygame-dependent checks/modules skipped. Native desktop
  and audio untested; see docs/VALIDATION.md for exact scope and adapter checks.

# v0.2.14

- Fix F2 octave-digit routing: typed numbers reach the octave editor before
  physical piano-key decoding. At `D#5`, typing `4` on the last digit produces
  `D#4` without replacing the pitch class, instrument or effect.
- Accept octaves 0..7; reject 8/9 without moving the cursor or inventing a note.
  Blank, release and cut cells remain unchanged. Normal row Skip and undo/redo
  apply; repeat-last-note remembers the corrected octave.
- Preserve the full physical piano range in the note-name position, letter-note
  input in the octave position, Caps Lock audition, instrument/parameter input,
  Alt+digit Skip shortcuts, and keypad entry when it supplies a digit.
- Update the contextual helper, F1 guide and keyboard documentation accordingly.
- Keep "Shorten or simplify the project and try again" prominently in oversized
  SID-export errors. Retain exact byte diagnostics and the hard memory limit;
  remove the unhelpful suggestion to use a future, unimplemented player.
- Supply a cumulative checked updater for the supplied v0.2.12 snapshot and
  v0.2.13-cp001. It accepts only known source hashes, makes sibling backups,
  refuses conflicting edits, and retains direct parent-directory unzip support.
- No audio-engine, sequencer, song-format, buffer, dependency or song changes.
  Validation scope and limitations are in docs/VALIDATION.md.

# v0.2.13

- Replace the incorrect "sequencing is pending" effect-entry status with feedback
  from the same capability check used by playback/export. Unsupported commands
  remain stored and are labelled without promising playback support.
- Add project-local beat/bar shading controls in F12. Default 4/4, configurable
  rows per beat 1..256 and beats per bar 1..32. Pattern and filter rows share the
  display-only grid. Optional editor metadata preserves format-6 compatibility.
- Preflight complete PSID memory requirements and report player bytes, unique
  tick records, pointer sequence, total budget and excess. Keep the original
  player, memory map and all executable write semantics unchanged.
- Add a standard-library incremental updater with exact archive/file checks,
  CRLF-aware baseline matching, conflict refusal, sibling backups, write-failure
  rollback and idempotency. No automatic Git, downloads or dependency changes.
- Add focused regressions and a separate issue/fix-proposal report. Core checks:
  63 passed, 1 UI integration check skipped for missing pygame-ce. This is not a
  full GUI/native-audio validation. Native project format remains 6.

# v0.2.12

- Double the first-run/default audio buffer from 1024 to **2048 samples**
  (about 42.7 ms at 48 kHz) to provide more scheduling headroom by default.
- Keep existing explicitly saved per-machine audio-buffer preferences unchanged.
  The CLI override and all selectable buffer sizes remain unchanged.
- Update the preferences example, UI help, README and audio-settings regression
  checks for the new default. Project format remains 6.

# v0.2.11

- Show the startup splash by default until the user explicitly opts out. Add
  OK / Play demo song buttons and a small, initially unchecked lower-left
  "Don't show this on startup" checkbox. Keep the version beneath the logo.
- Save both checkbox states as hide_welcome_on_startup in preferences.json.
  Only boolean true hides the splash; missing or invalid values show it.
  Ignore legacy first-run markers. --welcome can reopen it and undo the opt-out.
- OK/Escape dismiss without playback. Play starts Autumn at five, waiting for
  audio or startup notices as before. Preserve unrelated preferences and report
  save failures. Keep explicit project/example/export/headless startup behavior.
- Keep the logo, version, buttons and checkbox within small windows at high zoom.
- Fix installation examples that used --example and bypassed the splash.
- Add regression checks for default/repeated startup, legacy state, opt-out and
  re-enabling, mouse/keyboard actions, preference preservation and save failures.

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

## v0.2.34

- Add W waveform automation with numeric/letter aliases and instrument/table reset.
- Add persistent sync and ring modulation FX in the previously unassigned SID macro range.
- Preserve envelope gate, waveform-table age, instrument settings and PCM isolation.
- Integrate column selection, edit masks, clipboard, undo, help, native format 10 and export.
- Preserve saved cursor fields across the layout change and fit the additional column.
- Include the supplied synthwave kick and snare reference WAVs unchanged.

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
