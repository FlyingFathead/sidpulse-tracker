# SIDpulse Tracker

![SIDpulse Tracker logo](sidpulse/assets/sidpulse-tracker-logo.svg)

> **ATTENTION:** [FlyingFathead/sidpulse-tracker](https://github.com/FlyingFathead/sidpulse-tracker/) is the one and only official, original source for **SIDpulse Tracker**. Steer clear of other sources or repositories claiming to be the official project.

**SIDpulse Tracker is a desktop music tracker for composing with the Commodore
64's SID sound chip, inspired by Impulse Tracker.** Arrange notes across three
voices, build instruments with waveform and pitch tables, shape their envelopes
and filters, and hear the result through native 6581/8580 emulation as you work.

Save editable songs as `.sidpulse` projects, export `.sid` music files or
runnable C64 `.prg` programs, and render your tracks to WAV or MP3. PCM sample
import and sample-to-SID synthesis are also available alongside the tracker.

![F5 playback: Autumn at Five with all three SID voice scopes](docs/media/sidpulse-f5-playback.gif)

[Watch Autumn at Five with audio (full song, 1:36)](docs/media/sidpulse-f5-playback-full.mp4)

## Features at a glance

- **Three SID voices:** compose for 6581 or 8580, PAL or NTSC, with native reSIDfp playback.
- **Sample-to-SID wavetable synthesis:** fit a self-contained SID instrument from a sample, compare source/result, then freeze or edit its tables. Preferred C64 workflow.
- **Tracker workflow:** patterns, orders and instrument editing, with Modern and Classic keyboard layouts.
- **Channel automation:** W waveform and AR arpeggio controls, sync/ring FX, plus editable/recordable A/D/S/R and pulse width; preserve the instrument settings.
- **Flexible editing:** select individual columns, copy notes or automation, paste special and undo changes.
- **Live feedback:** three voice scopes, channel and instrument mute/solo, and audio performance counters.
- **C64 exports:** SID and runnable PRG files, with four SQUEEZER versions, all-version comparison (optional Top 3) and measured size, RAM and playback cycles.
- **PCM samples:** F3 import, waveform trim markers, squeezing, and instrument sample overrides.
- **WAV/MP3 export:** output browser, format choice, and extra loop count (default 0).
- **Editable projects:** `.sidpulse` saves include version information and compatibility warnings when applicable.

Click the song name in the header to open F12 with **Song title** highlighted.
Click the active instrument to open it in F4. **Copy instrument / Paste
instrument** copy the complete instrument and assigned sample; occupied slots
ask before overwriting, and paste is undoable.

F2 now has **Select all** for the whole current pattern and an **Arp** button
on each channel. The previously unused EX column is now **AR**: type **0** for
OFF, **1** for ON, **R** for the instrument setting, or **.** to hold. Commands
persist on that channel; existing FX commands keep their meanings. See
[pattern arpeggio automation](docs/PATTERN_ARPEGGIO.md).

**Current priority: sample-to-SID wavetable synthesis.** Our preferred C64
workflow is to import a short sound in F3, fit a SID instrument with
**Synthesize audio (create wavetable)**, audition it, then use that instrument
in the song. The result uses ordinary SID waveform/pitch tables. Improving
these fits, with the included kick and snare as reference sounds, is the
priority. [How it works and current limits](docs/SAMPLE_SYNTHESIS.md).

## v0.2.37: playback navigation and drum presets

Use **− / +** on the F5 Info page, or the **previous/next triangle buttons**
beside the playback position, to skip through song orders. The file browser
now follows the highlighted row through the center of the list.
F4 presets include the frozen reference kick and snare under
**[Wavetable] Drums & Percussion**. Windows CI installs and checks FFmpeg before
the media tests. [Release notes and checks](docs/RELEASE_NOTES-v0.2.37.md).

## Drum attacks and sample fitting

The fitter now measures short transients separately from the bass body, solves
a falling-pitch model, and checks native attack energy and snare noise content.
Each candidate chip is settled before measurement. Results remain ordinary,
frozen SID instruments with existing waveform, pitch and envelope programs.
Open `examples/synthesized-reference-drums.sidpulse` to audition the fitted
reference kick and snare. [Method and limits](docs/SAMPLE_SYNTHESIS.md) ·
[release notes and validation](docs/RELEASE_NOTES-v0.2.36.md).

Stopped-state CPU is reduced by suspending silent emulation and redundant
redraws. Input stays responsive; 2048 remains the default audio buffer and 512
is the stress setting. [Performance checks](docs/PERFORMANCE-v0.2.36.md).

The File menu now says **Save as .sidpulse...**. All four SQUEEZER versions,
including v2.0.1 and default v2.0.2, and both DIGI methods remain available.
[DIGI methods and limits](docs/PCM_AND_AUDIO.md#experimental-c64-pcm-enhanced-routine).

## Quick install

Choose either Git or a release ZIP. Both use the same launchers and need
Python 3.10+; Python 3.12 is tested. On first launch, the launcher creates a
local `.venv` and installs the pinned dependencies, which needs internet access.

### Option 1: clone with Git

```bash
git clone https://github.com/FlyingFathead/sidpulse-tracker.git
cd sidpulse-tracker
```

- **Linux:** run `./run.sh`.
- **Windows:** run `run.cmd`, or double-click it in the cloned folder.

### Option 2: install a release ZIP

Download the **full ZIP** and matching **SHA256SUMS** file for the release.
For this version, they are `sidpulse-tracker-v0.2.37-full.zip` and
`SHA256SUMS-v0.2.37.txt`.

**Linux**, from the download directory:

```bash
sha256sum --check --ignore-missing SHA256SUMS-v0.2.37.txt &&
unzip sidpulse-tracker-v0.2.37-full.zip &&
cd sidpulse-tracker &&
./run.sh
```

**Windows:** [verify and extract the full ZIP](#windows), then double-click
`run.cmd` inside `sidpulse-tracker`. Accept the first-run setup when prompted.
For an existing ZIP installation, use the
[v0.2.37 incremental update instructions](docs/APPLY-v0.2.37.md).

Press **F5** to play, **F2** to edit patterns, **F4** for instruments and **F8**
to stop. Keep the launcher terminal open while the tracker runs.

**The official site of SIDpulse Tracker, a homage to Impulse Tracker, reimagined as a modern SID-native tracker.**

Created by [FlyingFathead](https://github.com/FlyingFathead). Runs on native Python + pygame-ce desktop application, with Impulse Tracker and Schism Tracker as the main keyboard keymap and visual reference.

> NOTE: This project is more or less a WIP (work-in-progress) at this stage, although the program is fully functional. Still, don't expect too much at this point, because the software hasn't been through years of extensive testing. I needed a SID tracker for my Commodore 64 projects, none of them had the classic Impulse Tracker interface, so I made this. *This is a hobby project, and that's it.*

Earlier changes: [v0.2.35 DIGI method selection](docs/RELEASE_NOTES-v0.2.35.md),
[v0.2.34 waveform automation and batch synthesis](docs/RELEASE_NOTES-v0.2.34.md),
[v0.2.33 sample tools and wavetable synthesis](docs/RELEASE_NOTES-v0.2.33.md),
and the [changelog](docs/CHANGELOG.md).

[Detailed earlier release descriptions](docs/README_HISTORY.md) are kept in
`docs/` so this page stays focused on installation and current usage.

## Keyboard transport

| Key | Action |
|---|---|
| F5 | Start song; show Info if already playing. Restart on repeated F5 is optional, default OFF. |
| Ctrl+F5 | Restart the complete song. |
| − / + on Info | Previous / next song order during playback; keypad also works. |
| F6 | Loop current pattern from row zero. |
| Shift+F6 | Play song from current order. |
| Ctrl+F6 | Loop current pattern from the current row. |
| Ctrl+F7 | Set/clear the separate playback mark in F2. |
| F7 | Play from that mark, otherwise the current pattern/row. |
| F8 | Stop song and audition. |
| Shift+F8 | Pause/resume. |
| Scroll Lock / Ctrl+F | Toggle tracing in the pattern editor. Default off keeps editing cursor independent. |

F2 returns to the pattern editor while the song keeps playing. The green row
and left `>` mark indicate playback; the outlined cell remains your edit cursor.
A `*` in the row gutter marks the F7 playback position. F5 uses the song loop
setting: **F11 > Loop song when the playlist ends** or **F12 > Loop song at end**
(on for new songs and First light).
An explicit loop=false in older projects stays off. F6 keeps looping until F8.
An unsequenced pattern selected with F7 plays as a pattern loop.

F4 selects SID instruments. Tab cycles bank/buttons/properties. Enter in the bank
opens the instrument chooser; click a yellow parameter field to type its value.
Keyboard jazz works while stopped: Caps Lock in F2, or
normal note keys in F4. F2 audition uses the selected physical SID voice; F4
allocates three voices. During song playback, note entry edits the source without
stealing its voices for separate audition. Use F8 before auditioning instruments.

F10 opens Save; Shift+F10 opens Save As. Ctrl+S/W quick-saves a named project
outside the browser. Ctrl+Alt +/- zooms; Ctrl+Enter toggles
fullscreen. Schism block keys are Alt+C/Alt+P/Alt+O. Ctrl+C centers the cursor;
Ctrl+Backspace undoes and Ctrl+Shift+Backspace redoes.

## Instruments, filter rows, song notes and export

In F4, switch to properties with Tab, then use PgUp/PgDn or click the General /
Motion tabs. Click a yellow field to type; sliders and envelope handles change
values directly while note keys remain available. Arpeggio and pitch sequences use signed decimal
semitone offsets, e.g. `0 3 7 12`; waveform sequences use `10 20 40 80` hex.
An empty sequence disables it. Arps loop at the chosen ticks/step; wave and pitch
sequences advance each tick and hold their last step. Motion parameters use
decimal values; General SID registers use hexadecimal values.

Press **Ctrl+Shift+F2** for filter focus, move to a row and press Enter. A row has
six values: cutoff, resonance, routing, mode, volume (hex), then signed cutoff
slide (decimal). A dot keeps the previous value; a zero explicitly sets zero.
Example: `380 A 2 10 F -3` routes voice 2 through a resonant low-pass filter and
lowers cutoff by three units each tick. Tab returns to voice editing. Ctrl+F2
continues to edit pattern length. Alt+Insert/Delete moves all voices and filter
rows together; voice/block editing operates on its selected voice lanes.

**Shift+F9** opens song notes. Shift+Enter inserts a line; Enter commits. Notes
remain in `.sidpulse`, including Unicode and line breaks.

**Ctrl+Shift+E**, or Escape > File > Export PSID, compiles the current document.
The export-only squeezer starts enabled. Choose S to save `.sidpulse` and export,
E to export only, or Escape to cancel. A analyzes changed checkbox settings.
An export alone never marks unsaved edits as saved. F12 offers PSID released text
and whole-song loop. Existing export files get an overwrite prompt and backup.

For a command-line export that also saves a native source:

```bash
bash run.sh --example --export-sid user_songs/first-light.sid
# Or export an existing project; a sibling .sidpulse is always saved:
python -m sidpulse user_songs/song.sidpulse --export-sid exports/song.sid
```

`--save-project PATH` changes the native-save destination for a CLI export.
The bundled 6510 player requires no assembler, emulator executable or extra
runtime package on your machine.

## Clear commands and file dates

Escape > File starts with New project, Clear all pattern data, and Clear all
instruments. Each asks for OK / Cancel and defaults to Cancel. Clearing patterns
empties their voice cells and filter rows while keeping pattern numbers, names,
lengths, the order list, instruments and song notes. Clearing instruments removes
the whole bank while retaining patterns and their instrument numbers. Both are
single undoable edits. Empty slots play silently until repopulated. PSID export
reports an empty bank or a used empty slot instead of silently omitting its notes;
native .sidpulse saving remains available.

The file browser's Modified column uses local time, `YYYY-MM-DD HH:MM`, for files
and folders. Its default is on. Toggle **File timestamps** in F12, or set
`"file_browser_show_modified": false` in preferences.json. Narrow views hide the
date column to keep filenames readable. Selected dates stay green on black.

## Audio buffers and diagnostics

Press **Alt+F12**, open Escape > Settings > Audio settings, or choose Audio buffer in F12.
Select an output, use Test arpeggio to preview it, or Refresh outputs after
connecting hardware. Reset defaults stages the three audio defaults without
changing appearance or other preferences.
Drag the slider from Less delay to More stability, or use Left/Right. The current
sample count and milliseconds update as you move. OK applies and saves; Cancel
or Escape keeps the original setting. Tab reaches every control; Enter activates
the focused control. There is no numeric-entry prompt. Available steps are 256,
512, 1024, 2048, 4096 and 8192 samples. Default: **2048 samples / 42.7 ms per buffer**.
Existing explicitly saved values are retained; use the slider to change them.
Larger values help tolerate busy or slower PCs but add latency. This displayed
buffer duration is not total output latency:
up to two PCM blocks are queued and the device adds its own buffering.

Applying a buffer setting briefly reopens SDL and resumes from the next generated
position; already queued audio is discarded. The setting persists per machine,
not in your song. `--audio-buffer 4096` overrides it for one launch. Linux config
is `$XDG_CONFIG_HOME/sidpulse-tracker/preferences.json` (normally under `~/.config`);
Windows uses `%LOCALAPPDATA%/SIDpulse/preferences.json`.

The saved **Detect audio underruns / warn** checkbox defaults to ON. Its config
key is `audio_underrun_detection` (true/false). Live warnings appear as a small
reddish lower-left footer message for 12 seconds, with Alt+F12 as the shortcut;
they never open a popup or steal focus. A late callback is labeled separately
from a confirmed PCM underrun. Raw counters remain available when warnings are
disabled. Audio settings also show missing frames and callback timing.

The Info page shows **Audio gaps**: continuous episodes where the SDL callback
requests PCM during playback/audition and none is ready. Each episode counts once,
including a long starvation; normal startup, pauses and idle silence do not count.
The old `gaps` counter polled short-Sound queue state, so its numbers are not directly
comparable. Counters accumulate until Reset audio counters (Settings); reopening
the device preserves these session counters. Late worker wakes, current/peak render
budget and over-budget blocks help distinguish scheduling and rendering pressure.
These are application measurements, not whole-PC CPU usage or definitive proof
of every driver/hardware underrun. A quiet native emulator startup is explicitly
muted; a 5 Hz DC blocker and 5 ms transport ramps condition host PCM only.

## Windows

Download the **v0.2.37 full ZIP and SHA-256 checksum file** from the same release.
In PowerShell, verify the ZIP before extracting:

```powershell
$zip = ".\sidpulse-tracker-v0.2.37-full.zip"
$checksums = ".\SHA256SUMS-v0.2.37.txt"
$lines = @(Get-Content -LiteralPath $checksums -ErrorAction Stop | Where-Object {
    $_ -match '^[0-9a-fA-F]{64} [ *]sidpulse-tracker-v0\.2\.36-full\.zip$'
})
if ($lines.Count -ne 1) { throw "Missing or ambiguous full-ZIP checksum." }
$expected = ($lines[0] -split '\s+')[0]
$actual = (Get-FileHash -LiteralPath $zip -Algorithm SHA256 -ErrorAction Stop).Hash
if ($actual -ne $expected) { throw "ZIP checksum mismatch. Do not extract." }
Expand-Archive -LiteralPath $zip -DestinationPath . -ErrorAction Stop
```

Open PowerShell or Command Prompt in the extracted `sidpulse-tracker` folder
(the one containing `run.cmd` and `run.ps1`), then run:

```powershell
.\run.cmd
```

To start with First light or open your own project:

```powershell
.\run.cmd --example
.\run.cmd "C:\Music\My song.sidpulse"
```

`run.cmd` calls the adjacent `run.ps1`, forwards arguments, and returns its exit
code. If setup is needed, `run.ps1` lists Python, the local environment and the
contents of `requirements.txt` under "The following Python dependencies are
required and need to be downloaded", then asks **Continue? [Y/n]** before making
changes. Enter or Y accepts; N cancels installation. Missing 64-bit Python is installed as Python
3.12 through WinGet for the current user; if WinGet is unavailable, the launcher
prints the official Python download address. Packages are installed into `.venv`.
An internet connection is needed for installation. Later runs reuse the ready
environment and skip the setup prompt. The WinGet options follow Microsoft's
[install command documentation](https://learn.microsoft.com/en-us/windows/package-manager/winget/install).

If calling `.\run.ps1` directly reports "running scripts is disabled", use
`.\run.cmd`. The wrapper starts Windows PowerShell with
`-NoProfile -ExecutionPolicy Bypass -File`; that override applies only to the
launched process. It does not persistently change your execution policy or need
an administrator terminal. Microsoft documents the process-specific option in
[about_PowerShell_exe](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_powershell_exe?view=powershell-5.1#-executionpolicy-executionpolicy).

For an existing ZIP installation, close the tracker, back up the folder, verify
the full ZIP as above, then extract it over the installation (use `-Force` with
`Expand-Archive` to allow replacement). User songs, autosaves and `.venv` are not
release contents. Preserve local source edits separately; extraction replaces
files rather than merging them. Git checkouts can update with `git pull --ff-only`
on `main` after reviewing and preserving local changes.

If you prefer manual setup:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m sidpulse
```

Direct `run.ps1` remains available where script execution is already enabled.
The CI matrix includes Windows/Linux tests and the Windows CMD-to-PowerShell
first-run path. Check the Actions result for the exact release commit; local
validation does not substitute for the remote matrix. The validation procedure
is recorded in [VALIDATION.md](docs/VALIDATION.md).

## Development, Git and checkpoint delivery

```bash
python -m pip install -e '.[dev]'
python -m pytest -q
python -m sidpulse --headless-smoke --example
python -m sidpulse --log-keys keys.log
```

Public release assets are the **full source ZIP and its SHA-256 checksum file**.
Build them from the checked release tag, not by zipping a working directory.
Local cumulative patches are not public release assets. Do not include Git
history bundles, private project notes, environments, backups or user projects.
Clone the repository for Git history. See [RELEASING.md](docs/RELEASING.md) for
the commit, CI, tag, archive and release-review sequence, and
[release notes](docs/RELEASE_NOTES-v0.2.22.md) for the user-facing change summary.

Repository: [FlyingFathead/sidpulse-tracker](https://github.com/FlyingFathead/sidpulse-tracker).

See [PLACEHOLDERS.md](docs/PLACEHOLDERS.md), [CHECKPOINT.md](docs/CHECKPOINT.md), [VALIDATION.md](docs/VALIDATION.md),
[IT_KEY_COMPAT.md](docs/IT_KEY_COMPAT.md), [COMMANDS.md](docs/COMMANDS.md),
[EFFECTS.md](docs/EFFECTS.md), [PSID_EXPORT.md](docs/PSID_EXPORT.md), [PLAYBACK.md](docs/PLAYBACK.md), [SIDPULSE_FORMAT.md](docs/SIDPULSE_FORMAT.md),
[DECISIONS.md](docs/DECISIONS.md), and the unchanged [v4 roadmap](docs/ROADMAP.md).

---

## Acknowledgment

Thanks to **Lasse Öörni and the GoatTracker contributors** for the extensive
documentation on storing song data more compactly and optimizing playback
routines. The GoatTracker documentation served as a useful reference for
SIDpulse Tracker's squeezer. The implementation is independent; no GoatTracker
code was incorporated. See the
[optimization study](docs/SQUEEZER-v2.0.1.md#goattracker-reference-compressing-the-instruction-not-just-its-results).

## My other Commodore 64-related projects

- [audio-bitsqueezer](https://github.com/FlyingFathead/audio-bitsqueezer) — Convert audio into compact 4-bit SID samples and playable C64 programs or EasyFlash cartridges, with a command-line interface and local browser UI.
- [c64-3d-toolkit](https://github.com/FlyingFathead/c64-3d-toolkit) — Compile low-poly wireframe models and Blender scenes, animations and physics into C64 demos, with OBJ/MTL and SVG import support.

---

## Credits

SIDpulse Tracker has been made by [FlyingFathead](https://github.com/FlyingFathead/). Special thanks to: ChaosWhisperer
