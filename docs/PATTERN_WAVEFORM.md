# Waveform and SID modulation automation

F2 has one new **W** column between AR and FX. It changes the waveform of the
playing voice without editing its instrument or retriggering its envelope.
W is a simple four-waveform selector; it does not edit a waveform sequence.

| W input | Waveform |
|---|---|
| `1` or `T` | Triangle |
| `2` or `S` | Sawtooth |
| `3` or `P` | Pulse |
| `4` or `N` | Noise |
| `0` or `R` | Restore the instrument waveform or waveform sequence |
| `.` | Empty command: keep the running waveform setting |

The cell displays T, S, P, N or R. An override persists across blank rows,
notes and instrument changes on that tracker channel until reset. R resumes
an instrument's waveform sequence at the playing note's current age, without
restarting the sequence. Starting playback or restarting the whole song resets
the channel overrides. Other instrument programs, including pitch, arpeggio,
pulse-width motion and ADSR, keep running.

Click W in the header to select that field. Keyboard entry, edit masks,
copy/paste, Paste Special automation, clear, repeat and undo work as for the
other fields. The existing RAL command and Reset all automation button still
reset the five ADSR/PW fields; use R in W or AR to reset those separately.
Frozen instruments still respond to pattern automation.

## Sync and ring modulation in FX

These commands occupy the previously unassigned SID macro range. Existing
IT-style effect assignments, including FX Wxx and Rxy, retain their meanings.

| FX command | Action |
|---|---|
| `Z10` | Sync off |
| `Z11` | Sync on |
| `Z1F` | Sync follows the instrument |
| `Z20` | Ring modulation off |
| `Z21` | Ring modulation on |
| `Z2F` | Ring modulation follows the instrument |

Each command changes only its own setting. Both settings persist on the
channel, and both can be active after setting them on separate rows. No
parameter memory is used: Z00 is still reserved, not a repeat command.
Unassigned Z values remain stored but unsupported. F1 and the FX helper show
which individual commands execute.

SID sync and ring modulation depend on the neighbouring oscillator: CH3
feeds CH1, CH1 feeds CH2, and CH2 feeds CH3. Ring modulation needs triangle
and a running source oscillator to produce the expected modulation. Switching
waveforms can itself cause an audible discontinuity; W does not add smoothing.

W and these FX commands are SID controls. They do not turn on a second SID
oscillator underneath a PCM sample or alter the PCM audio. Their settings are
retained for the next ordinary SID note. The experimental C64 PCM routine
reserves hardware CH3; it is not an independent fourth oscillator for sync
or ring modulation. Consider an ordinary synthesized instrument when all
three SID oscillators need to interact.

## Projects and exports

Host playback and WAV/MP3 export share this playback path. SID and PRG export
compile its ordered register writes and verify the generated 6510 player.
No additional high-rate interrupt or sample analysis is added to playback.

Native projects use format 10 when W or one of these six FX commands is present.
Projects without them keep the previous applicable format. Older builds can
preserve newer fields but cannot play the new commands correctly. Cursor
metadata records the new layout; loading an earlier project keeps the cursor
on its original logical field.

The unchanged reference kick and snare WAV files are in
[examples/samples](../examples/samples/README.md).
