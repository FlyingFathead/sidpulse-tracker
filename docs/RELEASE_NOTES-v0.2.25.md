# SIDpulse Tracker v0.2.25

This release builds on v0.2.24's A/D/S/R/PW automation. Its main change is field
selection: copy a pulse-width curve or just notes without replacing the rest of
the destination channel. Mouse drag, Shift+click and Shift+arrows make selections;
header clicks select a whole field lane. Alt+C copies and Alt+O pastes. Paste
Special offers Notes / Automation / Both; optional buttons and Pattern Edit Menu
make these operations available without memorizing shortcuts.

The blue CTRL CH / FILTER panel now has a collapse/expand triangle in both F2 and
Info. At narrow widths the default is collapsed so all three voices fit. An
explicit choice persists across views and restarts. Playback through F5/F6/F7,
pause and F8 stop do not change this preference. Ctrl+Shift+F2 reveals the panel
when moving keyboard focus into control editing.

Per-channel red waveforms remain visible in narrow Info panels, stacked below
their labels. Settings > Channel visualizers turns them off and stops the
display-only SID scope emulation. The master scope and music output remain active.

## Reset user preferences

At the bottom of Esc > Settings Menu, choose **Reset all settings to defaults**.
Cancel is selected in the confirmation; Enter therefore cancels until the user
deliberately chooses Reset settings. Escape also cancels.

The reset clears saved user configuration and immediately restores appearance,
font, file timestamps, F5 restart behavior, clipboard buttons, responsive filter
pane visibility, channel scopes and autosave defaults. It restores the helper
strip, 100% zoom and windowed mode. Audio returns to System default, a 2048-sample
buffer and underrun detection enabled. Startup welcome and export-squeezer
preferences return to defaults for their next use.

Song tempo, SID model/clock/filter, notes, instruments, automation, orders,
project export metadata and undo history are preserved. User presets and existing
autosave/recovery files are never deleted. The default autosave destination
becomes the installation's autosave folder again; older copies stay where they are.

With active audio, the reset waits for confirmation of the output change before
atomically replacing preferences. Cancel during that wait restores the old output.
Output failure leaves preferences intact; a preference-write failure also restores
the old output. If audio has already failed, preferences can still be reset, with
a notice that restarting is needed to try the default output.

## Compatibility and scope

The Linux and Windows launchers print the version from VERSION between rules
matching the terminal width (80 columns if unavailable). The banner warns to
keep the console open and that Ctrl-C in the console quits without the normal
save prompt. Windows run.cmd continues to delegate setup and launch to run.ps1;
both platforms use the same standard-library banner helper.

No new musical fields or format revisions are introduced. The application writer
stamp becomes 0.2.25; formats 6/7 and compatible-future-file handling remain as in
v0.2.24. Whole-cell copies retain unknown extension data. Partial edits preserve
unselected destination data. The synthesis, export player and PW recording rules
are unchanged; SC/RM/waveform columns remain deferred. No dependency changes.

See [pattern editing](PATTERN_EDITING.md), [appearance](APPEARANCE.md),
[validation](VALIDATION-v0.2.25.md) and [overlay instructions](APPLY-v0.2.25.md).
