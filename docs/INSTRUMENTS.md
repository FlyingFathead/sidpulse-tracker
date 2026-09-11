# Instruments in 0.2.5

F4 keeps a bank of 99 numbered SID instrument slots. Empty slots are grey and
scrollable with Up/Down or the wheel over the bank. Enter on an empty slot opens
three real buttons: **Choose preset**, **No preset**, **Manual**. Left/Right and
Enter work on these buttons; Choose preset is initially selected. No preset
creates a plain pulse instrument in that slot. Manual opens an editable draft.
Cancelling a chooser does not alter the song. Insert directly creates a blank
instrument. Add instrument opens the chooser for an empty slot.

Enter on an occupied slot, or Choose from presets, opens the catalog. Adding a
preset creates an independent instrument in the selected empty slot or the first
free slot; it never silently replaces an existing sound. The built-in list has
39 sounds, separated into Melodic, Percussive, Bass, Leads, Major arps, Minor arps,
Fifths, Noise and FX. Category buttons jump within one continuous list. Up/Down/Page keys
browse sounds; F8 stops song playback so note keys can audition the selection.

Presets and Manual parameters are raised tabs. Left/Right switches them when
browsing; Tab cycles fields, source/category choices, and Add/Cancel buttons.
Arrows move focus within choices/buttons; Enter activates the focused button.
In Manual, only a mouse click on a yellow value field opens numeric/text entry. The draft
begins from the selected preset, and Blank instrument resets it. Add instrument
commits the entire draft as one undoable edit. Esc leaves the song untouched.

Save user preset stores the selected sound as a new independent JSON preset under
`presets/` beside preferences.json. The User presets button lists these files.
The directory can be backed up or populated with compatible user preset files;
there is no PCM/sample importer. Duplicate names are allowed and saves never
overwrite another preset. Invalid/oversized preset files are skipped with a status
message. Presets preserve all Instrument fields, including future macro data.

## Editing and audition

Tab cycles the bank, the raised action/tab buttons, and parameter fields. Arrows
move button focus; Enter/Space activates it. General, Motion / tables, Arp / pitch
and ADSR select editor pages. The oscillator retains its illustrated buttons.
Only a deliberate mouse click on the yellow value field opens numeric/text entry.
Typing digits or A–F, highlighting a parameter, clicking its label, dragging a
slider or envelope, or pressing Enter on the parameter does not open entry.
QWERTY note keys audition across the bank and parameter pages. Once the yellow
field has opened a typing dialog, Enter applies that value and Escape cancels.
General/ADSR values are hex; Motion values are decimal. Arrows adjust selected
values. Wheel over the parameter area scrolls fields on smaller windows.

Every numeric instrument field has a draggable slider plus its value. Waveforms
and switches use buttons; sequences use their own table/grid editors. Dragging
commits one undo step, not hundreds. Esc during a drag cancels it. Ctrl+Backspace
undoes; Ctrl+Shift+Backspace redoes. Note-on/off and held-note edits use native
reSIDfp. Audition restores initial master volume/filter after a song fade, and
held-note parameter updates reach the native instrument program. It uses the
song's tempo and selected PAL/NTSC clock.

## ADSR and piano grid

General and ADSR show linked sliders, yellow values and the envelope together. Drag A
horizontally to change attack; drag D horizontally/vertically for decay/sustain;
drag S vertically for sustain; drag R horizontally for release. Each updates the
same four saved 0..15 SID register values. The curve is illustrative: stage width
shows the rate index, not a measured time scale or a custom software envelope.
Sustain holds until note-off; it is a level, not a duration.

Arp/pitch uses 16 steps per page, up to 64, with pitch range buttons and a piano
reference. Drag to draw; skipped mouse events interpolate intervening steps.
Arrows move/change steps; Ins/Del inserts/deletes a step; click the yellow Length
value to resize;
Clear disables the sequence. Values are relative semitone offsets -48..48, not
free-running Hz. Arpeggio repeats at its ticks/step rate; pitch sequence advances
once per tick and holds the final value. Wave sequences remain editable tables.

Delete instrument / Del asks for OK or Cancel, with Cancel selected. Deleting a
referenced instrument explicitly tells you which remaining instrument receives
its pattern references. Notes remain; the bank and references undo together.
Individual deletion retains at least one populated instrument. File Menu >
Clear all instruments removes the entire bank after a Cancel-default confirmation.
It preserves patterns and instrument numbers; empty slots play silently. The
whole operation is undoable, and format 6 saves empty banks losslessly. Save user
preset sits on a solid dock below the instrument list and requires a populated slot.

## Timing and playback

F12's C64 timing selects PAL or NTSC; changing it stops playback for a safe native
chip reset. F5 restarts with the new clock. Pitch and musical BPM are compensated;
NTSC does not automatically make the tune 20% faster. Host preview and exported
PSID both use the selected clock. F12's Song / PSID loop controls natural endings
in both paths. First light and new songs default to loop on. An old project with
an explicit loop=false keeps that choice; turn it on in F12 if desired. F6 still
loops the current pattern. Host loops restart instrument programs, initial
filter/volume, speed and tempo while elapsed time continues.

## Program On/Off buttons

Motion / tables has seven independent raised buttons: Arpeggio, Wave sequence,
Pitch sequence, Pulse motion, Vibrato, Auto gate-off and Retrigger. Pressed means
On; raised means Off. Off bypasses the program without clearing its table or
resetting its numeric values. Editing while Off keeps the program bypassed until
you turn it back on. An empty table or zero depth/timing remains inactive even
when its switch is On. Older instruments load with switches On to preserve sound.

Click a switch, or Tab to buttons, use arrows to focus it, and press Enter.
The Arp / pitch drawing page also exposes the selected program's switch; both
views share one state. Off draws the retained steps in grey. Undo/redo restores
the switch as a single edit. New project and user-preset saves include all states.

These are instrument-program switches. Explicit pattern J/H/Q/S effects still
work independently. Sync and ring already have their own switches. Hardware
ADSR stays active; its four controls edit the chip's envelope. Switching off
automatic gate-off does not disable keyboard key release or pattern note-off.
