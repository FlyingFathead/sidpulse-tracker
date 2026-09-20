# Pattern arpeggio automation

In F2, use the **Arp** button above a channel or enter commands directly in
its **AR** column. This uses the previously reserved EX space. No existing
effect letter or parameter has been reassigned, and the FX column is free
for slides, vibrato, tempo changes or other commands on the same row.

| Key | Display | Action |
|---|---|---|
| `0` | `OF` | Switch arpeggio off on this channel. |
| `1` | `ON` | Switch the instrument's arpeggio on, including an F4-bypassed table. |
| `R` | `IN` | Return to the currently sounding instrument's arpeggio switch. |
| `.` | `..` | Clear this row command; keep the running channel state. |

OFF/ON persist across blank rows, new notes, instrument changes and pattern
boundaries until another command or a transport/whole-song loop restart.
Starting playback at the cursor starts with instrument defaults; earlier
pattern commands are not replayed. Put the intended command at the start of
a section when it needs to audition independently.

OFF suppresses both the instrument table and `Jxy`. With ON or IN, `Jxy`
retains its existing three-tick row arpeggio, and `J00` recalls its previous
value. Pitch sequences, pitch slides and vibrato remain active. Arpeggio
phase follows the note's age; turning ON does not retrigger its gate or
erase the table. F4 settings remain untouched.

The Arp button shows the command at the selected row, not a prediction of
the running state. Its dialog names the exact row and channel. Hold clears
that command; Cancel leaves it untouched. Commands are copied, cut, rolled,
pasted and undone as one field. Paste Special's Automation option includes
AR; the existing Reset all automation/RAL command still resets A/D/S/R/PW.

Playback, PCM instruments, WAV/MP3, SID and PCM-enhanced PRG/RSID use the same
row semantics. Projects containing an AR command save as native format 9;
projects without one retain the applicable earlier format. Older releases
cannot execute this new field and may show a compatibility warning.
