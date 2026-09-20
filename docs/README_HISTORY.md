# Earlier README release notes

Historical descriptions retained from the main README. For current installation
and usage, see the [main README](../README.md), [changelog](CHANGELOG.md) and
[current release notes](RELEASE_NOTES-v0.2.36.md). Versioned commands below refer
to their historical releases.

## v0.2.32: PCM remapping, import squeezing and export comparison

**File Menu → Export WAV / MP3** opens the output browser with format and loop
controls. **Loops 0 means play once**. **F3** imports samples, displays their
waveforms, edits start/end markers and squeezes to 4/8/16-bit PCM. Assign a
sample to an instrument; **F4** then shows its **Sample** view and an explicit
**Unmap sample from this instrument** button. SID settings remain saved;
working PCM pitch/gate controls stay available.

The supplied synthwave demo has a separate PCM kick/snare version in
`examples/autumn-at-five-synthwave-pcm-drums.sidpulse`. Its original remains
unchanged. Host PCM works on all three channels. C64 export has a separate,
experimental **CH1/2 SID + CH3 4-bit digi** routine. PCM on one tracker channel
is automatically remapped to C64 CH3 at export; the editable song keeps its
layout. A warning triangle marks PCM notes outside CH3. The usual squeezer
comparison, including Top 3, works for digi-enhanced exports. The routine is identified in the
export screen; its `.sid` output is RSID. It has different sound and hardware
limits from the host mix. Ordinary SID songs retain the existing player.

Auto-squeeze on import defaults to 4 kHz / 4-bit and keeps a restorable original.
Use its top-right F3 button to disable it. PCM WAV import needs no FFmpeg when
auto-squeeze is off; WAV export needs none. MP3, compressed sample import and sample
rate conversion use an optional FFmpeg installation. See the
[PCM/audio guide](PCM_AND_AUDIO.md), [release notes](RELEASE_NOTES-v0.2.32.md)
and [performance results](PERFORMANCE-v0.2.32.md).

## v0.2.30: smaller exports, version comparison and visible scrollbars

**SQUEEZER v2.0.2** uses short IDs for repeated literal blocks and phrase calls.
It saves another **1,245 bytes** on the native v8 stress arrangement, after
including the larger player and dictionary. All three earlier versions remain
available. **Show all versions** is on by default, with results ranked by file
size, resident RAM and measured cycles. Uncheck it for **Top 3**; the checkbox
saves `export_show_all_versions` immediately, including when you cancel export.
The dropdown keeps every version selectable. Ties stay highlighted.

Shared draggable scrollbars now expose overflow in the export panel, pattern
grid, banks, help, settings, menus, file browser and long text. Keyboard and
wheel navigation remain available; scrolling does not edit the song. See the
[scrollbar behavior and implementation](SCROLLBARS.md). The supplied SP
[application icon](DESKTOP_ICON.md) loads once at startup; Linux users can
optionally install a matching application-menu launcher.

Read the [design and reference findings](SQUEEZER-v2.0.2.md),
[performance report](PERFORMANCE-v0.2.30.md),
[validation](VALIDATION-v0.2.30.md), and
[overlay instructions](APPLY-v0.2.30.md).

## v0.2.29: shared playback phrases and three-version export comparison

**SQUEEZER v2.0.1** stores identical playback packet sequences once and calls them
with bounded repeats. v1.0 and v2.0 remain available. The export comparison is on
by default: three columns show output size, resident RAM and measured maximum
C64 cycles, with a **Use Squeezer** button beneath each. The smallest valid result
is selected initially; choose another version immediately or turn comparison off.
Shared analysis runs in the cancellable background worker.

Read the [design and measurements](SQUEEZER-v2.0.1.md),
[release notes](RELEASE_NOTES-v0.2.29.md),
[performance report](PERFORMANCE-v0.2.29.md),
[validation](VALIDATION-v0.2.29.md), and
[overlay instructions](APPLY-v0.2.29.md).

## v0.2.28: lower UI cost and safer pattern editing

The UI reuses rendered cells, M/S buttons and mouse geometry, and avoids scanning
an unchanged song on every frame. M/S and channel visualizers remain on by
default. See the [measured performance comparison](PERFORMANCE-v0.2.28.md).

F2 now has **Cut / Copy / Paste / Paste Special / Reset all automation**.
Cut and Reset confirmations start on **Cancel**. Cut includes a saved
**Don't show this again** checkbox; selected fields remain in the clipboard and
can be restored with Undo. Reset always asks before replacing automation.

**Settings Menu > UI Settings** groups display controls and includes an enabled-
by-default **Instrument/sample M/S** toggle. Turning it off hides those buttons
and bypasses instrument monitoring; channel M/S remains available. Parent-menu
buttons stay pressed while their submenu is open.

**Record automation** opens inline in F4, with **Automate what** (A/D/S/R/PW),
**On channel** (1/2/3), and a blue slider. Drag or hold its arrow keys to record.
Only one channel is armed, red with **(A)**, and the bank has a direct Disarm
button. Instrument selection cannot redirect a take. UI Settings retains the
old window as method 1; inline method 2 is the default.

Instrument/sample banks start at 001 on new/load, center through the middle and
clamp at their ends. Their selection survives view changes, independently of
F2's **Center pattern row** preference.

**SQUEEZER v2.0** adds overlap packing. The export panel's **Squeezer version**
dropdown retains **v1.0** for A/B comparison. v2.0 includes v1.0 fallbacks and
uses the same C64 decoder. Squeezed PRGs display the tracker and squeezer versions
before playback. See [squeezer details](SQUEEZER.md).

See [release notes](RELEASE_NOTES-v0.2.28.md),
[validation](VALIDATION-v0.2.28.md), and
[applying the update](APPLY-v0.2.28.md).

## v0.2.26: responsive clipboard buttons and Modern keyboard mode

F2 clipboard buttons now depress while held, activate on release inside, and
show a brief **Copied to clipboard** / **Pasted from clipboard** notice above
**F8: SILENCE**. An empty clipboard gets an explicit notice. Dragging away and
releasing cancels the click; quick clicks still show a short pressed state.

**Settings Menu > Keyboard mapping** selects **Modern** (the new default) or
**Classic**. Modern uses **Ctrl+Insert** to copy and **Shift+Insert** to paste in
F2. Classic preserves the previous shortcuts, including Ctrl+Insert to roll.
Alt+C / Alt+O continue working in either mode. The setting is saved per user.

The header now shows **Oct: 4 [+1] [0] [-1]** controls in pattern, instrument and
sample views. The current value updates immediately; **0 resets to octave 4**.
In Modern mode, **+ / - / 0** also perform these actions in F3/F4. These controls
change the audition/note-entry octave; they do not transpose existing music.

Instrument rows now have **M/S** buttons beside their activity indicators. Mute
and solo follow that instrument across all three voices during playback and
audition. They are session monitoring controls; songs and exports stay intact.
Sample rows use the assigned instrument mute/solo controls; F3 shows the PCM waveform.

**REC PW: OFF** shows only its arm button. Arming reveals **Record to channel**
and the recording instructions. The arm color defaults to red and supports the
`REC_ARM` color override in user preferences.

Automation resets are now explicit: **R** in an ADSR field restores that
parameter; **RAL** typed in PW restores all five parameters at that row/channel.
The **Reset all automation** button applies all five resets to the current cell
or selected rows/channels. Notes, instruments and FX remain, with one-step undo.
**R then Enter** in PW restores only pulse width. Incomplete R/RA input is
temporary and cancellable. See [automation](AUTOMATION.md).

See [keyboard profiles](KEYBOARD_MAPPING.md),
[release notes](RELEASE_NOTES-v0.2.26.md),
[validation](VALIDATION-v0.2.26.md) and
[applying the update](APPLY-v0.2.26.md).

## v0.2.25: field selection, compact playback and preference reset

Drag across the F2 fields you want, or use **Shift+arrows**, then **Alt+C** to
copy and **Alt+O** to paste at another row/channel. Selecting PW copies only PW;
notes, instruments and effects at the destination remain intact. Click a field
header to select that field for the whole pattern. **Ctrl+Shift+V** opens Paste
Special with Notes / Automation / Both choices. The Copy / Paste / Paste Special
buttons can be hidden in Settings.

A triangle collapses or expands the blue **CTRL CH / FILTER** pane in F2 and
playback Info. Narrow windows start collapsed to fit all three tracks; an explicit
choice is saved across views and restarts. Red per-channel scopes also fit narrow
Info panels. **Channel visualizers** in Settings disables both their drawing and
the display-only SID scope processing when off.

The bottom of **Esc > Settings Menu** now has **Reset all settings to defaults**.
Its confirmation starts on **Cancel**. Reset restores user preferences including
audio, appearance, autosave and display options. Songs, instruments, patterns,
presets and existing recovery files are preserved.

See [pattern selection and clipboard](PATTERN_EDITING.md),
[release notes](RELEASE_NOTES-v0.2.25.md),
[validation](VALIDATION-v0.2.25.md) and
[applying the update](APPLY-v0.2.25.md).

Both launchers print the current version and a terminal-width warning banner.
Keep that console open while the tracker runs. Ctrl-C in the console interrupts
the program without the normal save prompt; use the application's Quit command
to exit normally.

## v0.2.24: channel automation and PW recording

F2 now shows **NOTE IN EX FX A D S R PW** on every voice. The teal automation
fields control the sounding voice: ADSR accepts one hex digit each and PW uses
three hex digits. Blank holds; **R** restores an ADSR setting, **R then Enter**
restores PW, and **RAL** in PW restores all five channel overrides. Existing
notes, instruments and FX keep their established positions and meanings.

**F4 > General > REC PW** records Pulse width slider movements into the chosen
channel's PW rows while playing. **Ctrl+Shift+R** arms recording, **Record to channel**
chooses the voice, releasing keeps the take and **Ctrl+Backspace** undoes it.
Recording uses row steps and ends at the current pattern pass boundary. The
instrument preset stays intact. ADSR can be entered directly in F2.

The main status line follows the cursor or active gesture. The blue shared-filter
lane now also appears in the playback Info page with live values, including
paused/stopped views. Native saves record the app version; newer compatible files
open with a warning and unfamiliar fields are preserved. Ordinary projects stay
format 6; projects using new row automation use format 7.

See [automation and recording](AUTOMATION.md),
[compatibility details](SIDPULSE_FORMAT.md),
[release notes](RELEASE_NOTES-v0.2.24.md) and
[validation](VALIDATION-v0.2.24.md).

## v0.2.23: output selection and test arpeggio

**Alt+F12** now includes an output-device list, **Test arpeggio**, **Refresh
outputs** and **Reset defaults**. Choose System default or an output exposed by
SDL on Linux/Windows. The short C-E-G-C test previews the selected output and
buffer without changing the song or saving preferences. Playback waits during
the test and resumes afterwards, retaining its queued PCM and pause state.

**OK** saves the confirmed output name as `audio_output_device` in the machine
config (`null` means System default). Failed selections restore the previous
output and do not save. An unavailable saved output falls back to System default
at startup; its saved name remains available for reconnection. Reset defaults
stages System default, 2048 samples and underrun detection ON; OK saves it.

Device discovery is on demand. Ordinary playback retains the isolated audio
process, two-block reserve and existing SID/conditioner path. See
[validation and performance](VALIDATION-v0.2.23.md) and
[release notes](RELEASE_NOTES-v0.2.23.md). Native Windows hardware validation
remains separate from Linux SDL dummy tests.

## v0.2.22: isolated audio and underrun diagnostics

Audio now runs in its own spawned process, keeping UI Python stalls away from
the SID renderer and SDL callback. PCM block handling and output conditioning
are faster without changing the 48 kHz rate, audio quality, 2048-sample default,
two-block reserve or song/export semantics.

**Alt+F12** opens audio settings. A saved **Detect audio underruns / warn**
checkbox defaults to ON (`audio_underrun_detection: true` in the machine config).
An underrun produces a small reddish lower-left status message for 12 seconds;
it never opens a popup or steals focus. Late callbacks have a separate message.
Raw diagnostic counters remain available when notifications are disabled.

See [performance and regression evidence](VALIDATION-v0.2.22.md),
[release notes](RELEASE_NOTES-v0.2.22.md) and
[audio architecture](PLAYBACK.md). The recorded tests use Linux SDL dummy
output; Windows hardware playback remains a separate validation step.

## Retained from v0.2.21: responsive SID/PRG export analysis

Opening Export now shows the squeezer immediately, with an animated activity bar
using the current slider-fill colour (no slider handle), real compiler phase
labels and elapsed time. Song copying and compilation run outside the display
thread, in a coordinator thread and a separate Python worker process respectively.
The window continues rendering and processing resize, close and Cancel events.

This also covers **Analyze** and the re-analysis needed after changing options
before **Save + export** or **Export only**. Busy controls prevent duplicate jobs;
Escape/Cancel stops the worker without saving preferences, the song, or an export.
Successful analysis is reused for export. Errors are displayed in the dialog and
late results cannot replace a cancelled/newer dialog. No new dependency, player
binary, encoding, audio setting or native song format is introduced.

The moving bar is an **activity indicator**, not a fabricated completion percentage
or an estimated time remaining. The optimizer can still take several seconds.
See [release notes](RELEASE_NOTES-v0.2.21.md),
[validation](VALIDATION-v0.2.21.md) and [export controls](SQUEEZER.md).

## Retained from v0.2.20: strict replay test-reference repairs

The development-only py65 timing adapter remains intact, along with exact cycle
and SID-write assertions. The preceding v0.2.20 full suite passed on the user's
Linux environment (979 tests, as reported by the user); that is a baseline result,
not a substitute for validating this new asynchronous GUI path.

## Retained from v0.2.19: automatic channel-phrase squeezing

**Squeeze song** remains enabled by default for SID/PRG exports only. The exporter
now compares counted per-channel phrases, shared register-order templates,
independent register-value streams, and cost-optimized static phrase banks.
Repeated bass/drum parts share storage underneath a changing lead, without
changing the IT-style editor. The player reads the packed representation directly;
there is no whole-song expansion buffer. Native songs, preview and undo are unchanged.

Complete PAL exports: **First light SID 22,552 → 6,496 bytes, PRG 24,477 → 6,809**;
**Autumn at five SID 11,174 → 3,600 bytes, PRG 13,099 → 3,913**. These compare the
legacy opt-out with the new default. The latest v0.2.18 candidate's SID figures
were 8,638 and 4,717 bytes respectively; this is an additional improvement.

The compiler compares full resident footprints, verifies reconstructed events,
and executes the selected machine-code player through full pass/loop/re-init
checks. It rejects a compact candidate that exceeds its instruction-cycle reserve.
`--no-squeeze-song` retains exact legacy output. No new runtime dependency is added.

This is a **source candidate**, not a published or fully hardware-validated release.
Native GUI/audio, py65, 64tass and VICE/real-target release gates remain open in the
build environment. Ordered tick/write equivalence is not cycle-identical spacing
inside a tick. See [design/options](SQUEEZER.md),
[measurements and actual validation](VALIDATION-v0.2.19.md), and
[release notes](RELEASE_NOTES-v0.2.19.md).

## Retained from v0.2.17: startup splash now makes the choice explicit

The startup splash now offers **New song / Play demo song**. **New song** (and
Escape) creates a genuinely blank `Untitled` project instead of leaving the
bundled **Autumn at five** demo in the editor. **Play demo song** keeps the demo
loaded and starts it as before. The saved **Don't show this on startup** preference
and explicit `--play-welcome-song` behavior are unchanged.

## Retained from v0.2.16: one file browser and editable filenames

**F9 Load, F10 Save, Save As, SID export and PRG export share the same directory
browser.** Filename and Directory are inline fields, not popups hiding the list.
Left/Right and Home/End move a real caret; Shift selects, Backspace/Delete edits,
and Ctrl+A/C/X/V selects/copies/cuts/pastes. Click to position the caret.

The current project's latest successfully opened/saved name is prefilled.
Save starts just before the extension without selecting the whole name:
`work_v21.sidpulse` can become `work_v22.sidpulse` by editing only that digit.
Folder navigation keeps the draft; a successful Save As becomes the next F9/F10
default. F10 now always opens the browser. **Ctrl+S/W remains quick-save** outside
it; inside Save it submits the visible name. Overwrites ask first (Cancel default),
and errors/cancelled confirmations retain the editable draft. Export keeps the
native project's path and saved/dirty state unchanged.

**Tab / Shift+Tab** changes focus; **Ctrl+L** edits the directory inside the
browser; **Alt+Up** goes to its parent; Enter submits; Escape cancels. Directories
and optional modified dates stay visible. See [browser guide](FILE_BROWSER.md).

All features below are included in the **v0.2.23 source candidate**; earlier
incremental patches are not required. After publication, obtain the full ZIP and
its checksum from [GitHub Releases](https://github.com/FlyingFathead/sidpulse-tracker/releases).
The intended public release assets are `sidpulse-tracker-v0.2.23-full.zip` and
`sidpulse-tracker-v0.2.23-SHA256SUMS.txt`. Incremental/checkpoint update packages
are a separate local-maintenance workflow, not required release downloads.
Song files, existing audio-buffer defaults and dependencies are unchanged
by the file-browser update. See [issue/fix report](ISSUES-v0.2.16.md) and
[validation](VALIDATION.md).

## Retained from v0.2.15: playing-instrument dots, clearer ADSR and song looping

**F4 instrument bank:** dots at the right flash on actual note triggers and stay
lit while a voice is gated. Song/pattern playback and keyboard/cell/row audition
are supported. Selection alone does not light them. Short visual persistence
keeps drum hits visible; these are activity indicators, not volume meters.
**F3 sample dots stay idle**; use the waveform and assigned instrument controls for PCM.

**General / ADSR:** attack `00` now draws vertically and the handle reaches the
left edge. This is a schematic fastest-setting marker: SID attack 00 is nominally
about 2 ms, not zero time. The graph now states that and shows the approximate
clock-scaled attack time. Sound-engine/register behavior is unchanged.

**F11:** the bottom **Loop song when the playlist ends** control is ON/OFF;
press **L** or click it. ON restarts at order 000; OFF stops at the end. Ctrl+S
saves it with the project. **F12 > Loop song at end** is the same setting;
F6's pattern loop stays separate. Final-row loop changes are now honored at the
next end boundary. Previously saved OFF remains OFF.

## Retained from v0.2.14: type the octave directly in the note field

In F2, move the cursor onto the final digit of a note and type **0..7**:
`D#5` + `4` becomes **`D#4`**, retaining the pitch class, instrument and effects.
The cursor then follows the existing **Skip** setting (Skip 0 stays put).
**Ctrl+Backspace** undoes the edit; **Ctrl+Shift+Backspace** redoes it.

The complete physical piano range is unchanged in the note-name slot. Numeric
entry takes priority only in the octave slot. Letter piano keys still work
there, and **Caps Lock keeps audition non-destructive**. Numeric keypad input
works when Num Lock produces a digit. Octaves 8/9 are outside the current 0..7
range and are rejected; digits never turn blank, release or cut cells into notes.

Oversized SID exports still refuse to run and now lead with **"Shorten or
simplify the project and try again"**, followed by exact byte counts. There is
no automatic musical simplification or change to the export budget.
See [octave-input issue and fix report](ISSUES-v0.2.14.md) and
[validation](VALIDATION.md).

## Features retained from v0.2.13: editable beat grid and export diagnostics

**F12 > Grid: rows per beat / Grid: beats per bar** now controls pattern and
filter-lane shading. Defaults remain 4/4 (4-row beats, 16-row bars). For a
12-row-per-quarter shuffle, set 12/4 for 48-row bars. Enter values in decimal;
Ctrl+S stores the display grid in the project. This never retimes notes or
changes tempo/speed. Highlight phase restarts at each pattern's row zero.

Entering an implemented effect no longer incorrectly says that sequencing is
pending. Unsupported commands remain editable and are explicitly labelled.
An oversized PSID export now reports the exact player, unique-record and
pointer-table sizes, including the excess over the existing memory budget.
The compact-player limitation is **not** fixed by this diagnostic change.

See [issue report and proposals](ISSUES-v0.2.13.md),
[grid details](PATTERN_GRID.md) and [validation](VALIDATION.md).

## Features retained from v0.2.12: 2048-sample default audio buffer

Fresh installs and machines without an explicit saved audio-buffer preference now
start at **2048 samples / 42.7 ms per buffer**, twice the previous 1024-sample
default. Existing explicitly saved buffer preferences are retained unchanged.

## Features retained from v0.2.11: Startup splash

The splash appears on every normal startup by default, with the version number
beneath the logo and **New song / Play demo song** buttons. New song creates a
blank **Untitled** project; Play starts **Autumn at five** and keeps the arrangement editable.

A small **[ ] Don't show this on startup** checkbox sits in the lower-left corner.
It starts unchecked when there is no saved choice. Either button saves its state
as `hide_welcome_on_startup` in the per-user `preferences.json`: `true` hides the
splash; `false`, a missing flag or an invalid value shows it. Old `first-run.json`
markers no longer suppress the splash. Escape works like New song.

Use `bash run.sh --welcome` or `.\run.cmd --welcome` to reopen it, even when
hidden. Uncheck the box and choose New song to restore the splash on future startups.
The preference survives replacing the checkout and subsequent application updates.
Launch without arguments for the normal flow; `--example` explicitly opens
First light and bypasses the splash, as does opening a saved project.

![Startup splash](preview-welcome-0211.png)

## Features retained from v0.2.10: Autumn at five and PRG export

The new welcome track is **Autumn at five**: 96 seconds of quiet, early-morning
woodland music at 80 BPM, with soft triangle swells, gentle arpeggios and delayed
vibrato. The triangles pass through the SID low-pass filter for a rounded,
sine-like tone. All three voices, patterns and instruments remain editable.

Start the tracker and play the welcome song directly:

```bash
bash run.sh --play-welcome-song
```

On Windows: `.\run.cmd --play-welcome-song`. **F8** stops; **F2** opens the patterns.
`--welcome` shows the startup splash again. `--silent --play-welcome-song`
opens the arrangement without an audio device. The bundled source is
`sidpulse/assets/autumn-at-five.sidpulse`; opening it through the welcome flow
creates a fresh editor document, so saving asks for your own filename.

**First light remains included**, with its original editable and PAL/NTSC SID
files in `examples/`. Use `--example` to open it.

**File > Export PRG** now saves a C64 program you can load and `RUN`. Choose the
matching PAL/NTSC setting before exporting; RUN/STOP returns to BASIC. The PRG
uses the same music player as SID export, including the welcome track's arps,
envelopes, filter and vibrato. No assembler or c1541 is needed for export.

```bash
bash run.sh --play-welcome-song --export-prg autumn-at-five.prg
bash run.sh path/to/song.sidpulse --export-prg song.prg
```

CLI export also saves an editable `.sidpulse` beside the program. PAL and NTSC
welcome examples are included in `examples/`. See [PRG export](PRG_EXPORT.md)
for loading instructions and limits.

## Previous checkpoint v0.2.9: README and docs update

v0.2.9 is a documentation/packaging-metadata cleanup over v0.2.8. Public
installation examples and tracked project notes use repository-relative or generic
paths rather than developer-machine checkout locations. There are no functional
runtime, audio, dependency or project-format changes in this patch.

### Pattern-length controls retained from v0.2.8

**Ctrl+F2** opens a linked **1–256 row slider** with a yellow **three-digit
value field centered underneath**. Drag the slider, or click the value itself
and enter up to three decimal digits. The field and slider update together.
Typing starts only after clicking the value field. **OK** applies the length;
**Cancel / Escape** leaves the pattern unchanged. Shortening can be undone,
including removed notes and filter rows.

![Pattern length dialog](preview-pattern-length-028.png)

### Configurable F5 restart retained from v0.2.7

**Restart on repeated F5** is a saved setting, **OFF by default**. Find it in
F12, or **Settings Menu > F5 restart option**. With it off, F5 starts a stopped
song and opens Info during playback without restarting. With it on, every F5
press starts the song from the beginning. **Ctrl+F5 always restarts**.

The preference is stored as `restart_on_f5` (true/false) in `preferences.json`,
separate from songs. Existing installations default to OFF when the key is absent.

### Playback stability and recovery retained from v0.2.6

- Fix a reproduced SDL/Python deadlock when starting, restarting, pausing or
  closing audio. F5 restart behavior follows the setting described above.
- The complete QWERTY piano range works in the note-name part of F2 NOTE.
  At the octave digit, type 0..7 to change only the existing note's octave;
  letter piano keys still enter notes. Caps Lock previews notes from any voice
  field without writing pattern data.
- **F11** shows the order list and complete pattern bank, with names and row
  counts. Click the black order-number column and type three decimal digits:
  each completed number applies and advances to the next row. Delete removes
  an order and shifts later entries up. Tab switches panels; Enter in the bank
  opens the selected pattern in F2. Unused patterns remain in the bank.
- **Autosave is On by default, every five minutes.** Settings > Autosave settings
  changes the interval (1–60 minutes), folder or On/Off state. Recovery copies
  go into `autosave/` beside the launchers. The folder is created and checked;
  an OK warning explains if it is unavailable. Settings can create/retry it.
- An unclean exit offers the previous session’s latest recovery copy on startup.
  Autosave never overwrites the working project or clears its unsaved status.
- Persistent crash reports include Python/native tracebacks, recent input and
  playback state. A 15-second watchdog records thread stacks if the UI hangs.
  The Windows launcher keeps its console open after a failure. See
  [recovery and crash reports](RECOVERY.md) for locations and limitations.

### Editing controls retained from v0.2.5

- QWERTY note keys remain available while adjusting instrument parameters.
  **Only clicking a yellow value field opens manual entry.** Sliders, graph
  handles, field labels and Enter on a parameter never open a typing prompt.
- New project, Clear all pattern data and Clear all instruments each ask for
  **OK / Cancel**, starting on Cancel. Both clear operations can be undone.
- Every quit request asks for confirmation, including a clean project and the
  window close button. Choices include **Discard & Quit**, with Cancel selected.
- Help uses aligned shortcut/description columns with ruled category headings.
  Instrument labels have inner padding, and Save user preset has a solid dock
  below the list, separated from the status bar.
- The file browser shows green modified dates on the right. **File timestamps**
  in F12, or `file_browser_show_modified` in preferences.json, toggles them.

### Playback and controls retained from v0.2.4

- Continuous SDL audio stream replaces the chain of short mixer sounds. The
  sample-clocked sequencer feeds a bounded reserve; UI redraws never set tempo.
- Separate native waveform monitors in the SID VOICE 1/2/3 panels. These show
  each voice before the shared filter; mute/solo is reflected in the displays.
- General now shows a mouse-editable ADSR envelope beside its linked sliders.
  The larger ADSR tab remains available. Menus use outlined, bevelled buttons;
  horizontal rules separate the bottom status/help groups.
- Audio buffer: a mouse/keyboard slider, current samples/ms, **OK / Cancel**.
  Default **2048 samples**; existing chosen buffer preferences are retained.
- Prepare scheduled SID attacks before retriggering, avoiding the reproduced
  ADSR counter delay in First light. Preview and PSID use the same register writes.
- The SVG-logo welcome now uses the startup splash controls described above.
  Use `--welcome` to see it again. Opening a project bypasses the splash.
- Header field values are vertically centered. Order/Pattern/Row values are also
  horizontally centered; Song Name/File Name/Instrument have extra inner padding.

### Windows launcher (retained from 0.2.3)

Windows now starts with `run.cmd`, a thin wrapper that calls `run.ps1` and
forwards arguments and its exit code. The PowerShell launcher still owns Python
virtual-environment setup, dependency installation and starting the tracker.
Its first-run dependency probe now handles missing packages without a traceback.

The following instrument improvements were introduced in v0.2.2:

The previous patch fixed the empty-slot hover crash, including mouse clicks and window
resizing that put an empty slot under the pointer. All button labels are centered
horizontally and vertically inside a one-pixel outline and raised/pressed bevel.

Motion / tables has On/Off buttons for arpeggio, wave/pitch sequences, pulse
motion, vibrato, automatic gate-off and retrigger. Off preserves parameters and
drawings. The switches work in audition, playback and PSID export, and survive
project saves and user presets. Tab to buttons, arrows to select, Enter to toggle.

Run `bash run.sh --example` on Linux or `.\run.cmd --example` on Windows. **F5** plays First light on loop; **F8** stops.
**F4** opens the instrument bank with real raised buttons, sliders and typed values.

- Browse slots **01–99**, including grey empty slots. Enter on an empty slot opens
  **Choose preset / No preset / Manual**. Add/Delete buttons are above the list.
- **39 built-in presets**, including all nine First light instruments, grouped by
  Melodic, Percussive, Bass, Leads, Major arps, Minor arps, Fifths, Noise and FX.
  Built-in and User lists are separate. Save user preset stores your own sounds.
- General, Motion / tables, Arp / pitch and ADSR are mouse and keyboard buttons.
  Every numeric instrument parameter has a slider and an editable numeric field.
  Arps/pitch have a drawable piano grid. **ADSR sliders and draggable envelope
  handles stay synchronized**, including native saves and keyboard audition.
- **PAL / NTSC** changes the SID clock, pitch calculation, and PSID CIA timing.
  The selected musical tempo stays the same. F12 controls song/export looping.
- Clear separators between every voice in both editing and playback views.
  Three sound voices, with a separate shared CTRL CH / FILTER lane in F2.
- Readable dark text on beige, a heavier font, crimson sliders and scope,
  three editable colour themes, and persistent font settings.
  **Ctrl+F12** opens theme settings; **Shift+F12** opens font settings.
- Visible mouse/keyboard Save / Discard / Cancel buttons and a framed, centred
  About window. Cancel remains the default for instrument deletion.
- The existing Schism-style editing, effects, native reSIDfp sound, buffer
  settings, lossless native saving, song notes, PSID export and M/S buttons remain.

[Controls and preset guide](INSTRUMENTS.md) ·
[Theme/font configuration](APPEARANCE.md) ·
[Remaining placeholders](PLACEHOLDERS.md) ·
[Validation](VALIDATION.md)

![Instrument editor](preview-instruments-025.png)

PSID export targets one PAL or NTSC 6581/8580 at $1000. Native projects save as
**.sidpulse format 6 or 7**, with backward-compatible loading of older formats.
It preserves empty instrument banks and pattern references to empty slots.
Format 7 carries row automation; see the compatibility notes below.
SID import, MIDI and remaining legacy effects are future work. PCM playback and experimental C64 digi export are available.

### Linux: install or update

Download `sidpulse-tracker-v0.2.30-final-full.zip` and
`SHA256SUMS-v0.2.30-final.txt` from the same release into one
directory. The full ZIP extracts under `sidpulse-tracker/`.

```bash
sha256sum --check --ignore-missing SHA256SUMS-v0.2.30-final.txt &&
unzip sidpulse-tracker-v0.2.30-final-full.zip &&
cd sidpulse-tracker &&
bash run.sh
```

For an existing ZIP installation, close the tracker and back up the folder
before extracting the full release over it. The release does not contain
`.git`, `.venv`, `user_songs`, `autosave` or machine preferences. Keep your own
projects outside the bundled `examples/` and `sidpulse/assets/` directories,
which are release-owned. An overlay replaces shipped source files; it is not
a merge of local source edits. A fresh adjacent folder is also suitable.

For a Git checkout, review and preserve local edits before using
`git pull --ff-only` on `main`, then run `bash run.sh`. Do not extract a release
ZIP over source changes that you intend to keep.

The launcher creates `.venv` and installs the pinned `pygame-ce` and `pyresidfp` dependencies if needed. Python 3.10+ is required; Linux Python 3.12 has been tested. Ubuntu systems may require `python3-venv` if virtual-environment creation is unavailable. `pyresidfp` wheels support common Linux and Windows configurations; building from source requires a C++20 compiler and Python development headers.

To open saved work, use F9 or:

```bash
bash run.sh path/to/song.sidpulse
```

Older song formats load with defaults for newer fields. Saves use format 6, or
format 7 when row automation is present. Newer-version and unsupported-feature
warnings explain partial compatibility; keep an original copy before resaving
such a project. See [native format compatibility](SIDPULSE_FORMAT.md).
Keep songs in `user_songs/` or another location of your choice; checkpoint ZIPs
never include that folder.

