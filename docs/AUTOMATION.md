# Channel automation and recording

The F2 voice layout is `NOTE IN EX FX A D S R PW`. All three SID voices remain
available. Automation headers and entered values use teal by default; empty
values are dimmer. The blue lane is the one shared SID filter.

| Field | Entry | Meaning |
|---|---|---|
| A | 0..F | Attack rate |
| D | 0..F | Decay rate |
| S | 0..F | Sustain level |
| R | 0..F | Release rate |
| PW | 000..FFF | Full 12-bit base pulse width |

These are hexadecimal values. A dot means no command on this row: retain the
running value. **R** in an A/D/S/R field restores that parameter's instrument
setting and displays `R`. Zero is an explicit value, never an empty cell.

In PW, type **R, A, L** to reset all five A/D/S/R/PW overrides on the current
row/channel. The unfinished `R..` and `RA.` input is temporary: it changes no
music or saved data until L completes the command. Escape cancels; Backspace
removes a prefix letter. Navigation also cancels unfinished entry. To restore
only pulse width, type **R then Enter**; this displays `R..`. A completed reset
of all five displays `R R R R RAL`. Press period to clear a field's command.

The **Reset all automation** button and Pattern Edit Menu action write all five
resets at the current cell, or across every selected row/channel if a block is
selected. This explicitly includes all five automation fields even when the
selection covers only PW. Notes, instrument numbers, FX, other voices and
instrument definitions are preserved. One Undo restores the entire operation.
Typed RAL always applies only to the current row/channel, then advances normally.
The reset button stays visible when the clipboard buttons are hidden.
The button/menu action always opens a confirmation with Cancel selected by
default; the dialog identifies the exact pattern, rows and channels affected.

These are existing per-field reset values in the file, so no new format is
needed. Older reset entries load with the clearer R/RAL display. A reset restores
the playing instrument's defaults from that row onward; it does not erase earlier
automation or disable the instrument's own motion programs.

Vibrato already uses **Hxy** in FX (x: speed, y: depth). A separate VB column is
deferred. Reset all automation affects A/D/S/R/PW and leaves FX intact.

Each override belongs to its channel. It affects the sounding instrument even
when the row has no note, and persists through subsequent notes and instrument
changes until another value or reset. Playback initialization clears overrides.
The instrument bank itself is not edited. Copy, paste, insert/delete, block
operations and undo/redo include these values. EX remains reserved; existing FX
letters retain their existing meanings.

PW only affects a pulse waveform. Instrument Motion PWM depth/rate remains
additive around the row's base PW, with the result clamped to 000..FFF. Set Motion
PWM depth to zero or bypass Pulse motion when an exact manually drawn sweep is
wanted. Extreme widths can silence the pulse. Changing PW consumes no extra
oscillator and leaves the shared filter available.

ADSR writes program the actual SID envelope registers. They do not trigger a
new note or restart an attack. Sustain is the SID's sustain level, not a general
PCM gain control. A new note or supported retrigger command starts a fresh
attack. Row overrides also apply to delayed notes and retriggers.

## Record channel automation

Open **Record automation** from the F2 toolbar, F4 General, the Pattern Edit or
Instrument menu, or **Ctrl+Shift+R**. Display **2 (inline)** is the default: the
highlighted field opens the controls inside F4 while the instrument bank remains
available. **UI Settings > Automation display** also retains the legacy window
as method **1**, in its own module.

1. Choose **Automate what**: A, D, S, R or PW. PW is the default. Use the triangles,
   or click the field to reveal the five choices in place.
2. Choose **On channel**: CH 1, 2 or 3 using the triangles, clickable choices or
   keys 1/2/3. This destination is independent of the instrument bank selection.
3. Click **Arm recording**, or press Space with recording controls focused.
   Only one channel can be armed; its marker is red with **(A)**.
4. Start playback with F5 or F6. The inline controls stay visible.
5. Drag the blue slider, or focus it with Tab and hold Left/Right. PW steps by
   010 hex, Shift by 100, Ctrl by 001; ADSR steps by 1, Shift by 4. Values clamp
   to the displayed hexadecimal range. Release keeps one undoable take.

Escape during a gesture cancels it. Ctrl+Backspace undoes a completed take.
**Disarm CH N (A)** is also directly available in the instrument bank while
armed, including other tabs and empty slots. Disarming keeps recorded rows and
their undo history. F8 stops playback. Tab cycles controls and returns to the
bank; Right from the bank enters the inline controls.

The destination and parameter stay fixed during a take. Bank browsing, pattern
cursor movement, and closing/reopening the panel cannot retarget it. New/load
clears the arm. Each parameter remembers its session knob value: PW starts at
800 and ADSR at 8. The bank's ordinary sliders still edit instrument definitions.

Recorded values go into the chosen channel and parameter column and affect
whichever instrument plays there. Original instrument definitions are preserved.
The audio sequencer captures rows it actually visits, so missed UI repaints do
not lose intermediate rows. Recording is **row-quantized touch recording**:
multiple changes in a row keep the last value. Playback applies values at row
start, with ADSR in place before a new note triggers. There is normal audio-buffer
latency; this is not a sub-tick lane.

A take ends at release, pause/stop, or the end of the current pattern pass. It
never silently overwrites the next pass or order. Release and adjust again for
another take. Reused patterns share their edits; duplicate a pattern first when
only one occurrence should change. Save waits for acknowledged take rows.

When stopped or unarmed, dragging or using the recording slider's arrow keys
adjusts only its value, without writing the song. `REC_ARM` defaults to red and
`REC_SLIDER` to blue; both support color overrides. Multi-pattern takes and
interpolation remain future additions.

SID and PRG export compile the same PW/ADSR register events as host playback.
More automation can increase export data size and register-write work; export
continues to enforce its existing memory and replay-cycle limits.

## Display and file compatibility

The main F2 status line follows the exact cursor position, including the octave
digit and each hex nibble. A separate, temporary **Last action** message describes
completed edits. A live drag says what it is adjusting or recording.

The blue control lane is available in F2 and the playback Info page, including
when stopped or paused. Its triangle expands/collapses the pane; explicit choices
persist across views and restarts. Narrow windows default to collapsed to fit all
three tracks. Collapsing never disables filter commands. The Info page shows live
cutoff, resonance, routing, filter mode, master volume and cutoff-slide values
above upcoming rows. F8 stops playback; it does not change pane visibility.

Mouse drag or Shift+arrows can select only PW or ADSR fields. Alt+C copies the
selection; Alt+O pastes it at another row/channel without replacing notes or
unselected automation. See [pattern selection and clipboard](PATTERN_EDITING.md).

Native saves record the application version. Ordinary projects remain format 6;
projects using row automation require format 7. The new loader also opens
structurally compatible newer formats, warns about newer writers and unfamiliar
fields, and preserves unfamiliar data with the owning cell, instrument, pattern,
filter or song. See [native format details](SIDPULSE_FORMAT.md).

SC, RM and waveform columns are deferred so this first automation update stays
focused on ADSR and PW. Sync, ring modulation and waveform remain available in
the instrument editor as before.
