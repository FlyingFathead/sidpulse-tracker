# SIDpulse Tracker v0.2.27

This release reduces repeated UI work and adds safeguards to pattern editing.
M/S and channel visualizers remain enabled by default. The musical file formats,
SID synthesis and dependencies are unchanged. The revised recorder adds ADSR
capture, and SQUEEZER v2.0 adds export packing with the same replay decoder.

## Performance

- Cache the displayed unsaved-change indicator by editor revision instead of
  comparing the complete song every frame. Direct model changes refresh within
  one second. Save, quit and autosave still perform the exact comparison.
- Reuse rendered note/automation cells, including their colors, and invalidate
  them on value, font, zoom and appearance changes. Bounded caches keep memory
  use finite. Scrolling and editing still update immediately.
- Reuse pattern mouse geometry while its layout is unchanged.
- Reuse M/S and regular button images while preserving held, muted, solo and
  disabled states. Pixel comparisons include button edges, colors and hit targets.
- Keep the responsive font fit between frames instead of rebuilding it twice
  per frame at zoom levels that need fitting.
- Avoid recalculating the instrument mute mask on each note when no instrument
  is muted or soloed. Ownership is still tracked for toggling held notes.

See [matched performance measurements](PERFORMANCE-v0.2.27.md), including the
v0.2.23 starter, v0.2.26 before optimization, and this version. Future releases
must include matched measurements; this is recorded in `AGENTS.md`.

## Cut and reset safeguards

F2 buttons are **Cut / Copy / Paste / Paste Special / Reset all automation**.
Small windows abbreviate the last two labels. Cut uses the same field selection
as Copy. Selecting PW cuts only PW; no selection cuts the complete current cell.
The clipboard retains the cut values, and one Undo restores them.

Cut confirmation defaults to Cancel. Its unchecked **Don't show this again**
option is saved only after confirming Cut. Cancelling does not change the song,
clipboard or preference. **UI Settings > Confirm before Cut** re-enables it.
The same confirmation applies to Alt+Z and the Pattern Edit Menu.

Reset all automation always asks first and defaults to Cancel. It states the
pattern, rows and channels affected, and writes all five A/D/S/R/PW reset commands
to that area. Notes, instrument numbers and FX are preserved. Undo restores the
old automation. Typed R/RAL entry remains an explicit tracker command.

## UI Settings and instrument monitoring

**Settings Menu > UI Settings** groups themes, fonts, helper strip, clipboard
buttons, Cut confirmation, instrument/sample M/S, the control/filter pane,
channel visualizers, zoom and fullscreen. Visible parent-menu buttons stay
pressed while their submenu is open, including navigation by mouse.

**Instrument/sample M/S** is a saved on/off setting, enabled by default. Off
hides these bank controls and bypasses instrument mutes/solo. Channel M/S keeps
working. Re-enabling restores the session's instrument monitor choices. These
choices never alter the song or exports. Sample M/S is still disabled until PCM
playback is implemented. Reset all user settings restores the enabled default.

See [validation](VALIDATION-v0.2.27.md) and [apply instructions](APPLY-v0.2.27.md).

## Channel recording and centered scrolling

Record automation opens inline inside F4, with the bank still visible. Method 2
is the default; method 1 retains the earlier popup module in UI Settings. Choose
**Automate what** (A/D/S/R/PW) and **On channel** (1/2/3) using triangles or
clickable choices. The blue slider accepts mouse dragging and focused arrow
keys. Only one channel is armed, red with (A), independent of instrument changes.
The instrument bank has a direct Disarm button on every tab, including empty
slots. Disarming keeps the recorded rows and Undo. Normal F4 sliders still edit
instrument definitions. See [recording instructions](AUTOMATION.md).

New/load starts instrument and sample banks at 001. Their highlighted row stays
centered in the middle, with top/bottom clamping, and survives view changes.
Bank centering is independent of **Center pattern row**, the saved F2 preference.
Mouse selection, wheel and keyboard navigation share the same rule.

## SQUEEZER v2.0 and PRG credits

The enabled export panel now has a **Squeezer version** dropdown. **v2.0** is the
default; **v1.0** remains selectable for A/B comparisons. v2.0 joins overlapping
phrase fragments and retains all original candidate encodings as fallbacks.
Every selected compact export still undergoes exact write, timing, memory and
instruction-cycle checks. No source song or instrument is simplified.

With squeezing enabled, the PRG startup text includes the actual tracker version
and selected squeezer version. It fits the existing loader allocation and does
not add work to the playback loop. See [squeezer details](SQUEEZER.md).

The overlay and full ZIP both preserve executable permissions on `run.sh`.
