# SIDpulse Tracker v0.2.24 validation

## Results

- Full regression suite: **1115 passed**, no failures or skips (179.36 seconds).
- Final automation/compatibility checks: **32 passed** (1.12 seconds), including
  the additional current-instrument reset case and the final status timestamp
  adjustment. The final tree contains 1116 tests; these targeted checks cover
  the changes made after the full run.
- Both headless smoke commands passed: `--example` and `--play-welcome-song`.
- Python 3.12.14, pygame-ce 2.5.7, pyresidfp 0.17.0; Linux x86_64, SDL dummy
  audio/video. Native Windows, physical audio output and real C64 hardware were
  not exercised.

## Automation and UI

The checks cover full-range PW, zero, hold/reset, blank-note rows, later notes,
changes of instrument, three independent voices, ADSR registers without extra
note triggers, delayed notes, retriggers, and restart prediction isolation.
Instrument presets remain unchanged. PAL and NTSC 6502 execution matches the
host sequencer's ordered register events with both export compression settings.

PW capture follows the audio sequencer across every visited row without needing
UI polling. Tests cover pattern wrap, start before the first tick, cancellation,
stop, one undoable commit, and a real spawned audio process with SDL dummy output.
The real-process test moves the F4 slider and immediately saves with Ctrl+S;
the save waits for the final recorded rows and contains the complete take.

F2 cursor hints cover every field and nibble, including the note octave. The old
instrument action text cannot replace them. The blue control lane appears in
pattern and Info views during playing, paused and stopped states. Live filter
slide values survive stop. Rendered screens were inspected at 800x600,
1280x900 and 1920x1080; narrow windows scroll voice columns while retaining the
control lane. SC, RM and waveform automation are deferred; the added columns
are only A D S R PW.

## Compatibility and unchanged playback

The actual supplied v0.2.23 loader successfully opened an ordinary project saved
by v0.2.24 and produced the same song. Such saves retain the legacy cell shape
and format 6; projects using automation use format 7. Tests open a simulated
format-8 project saved with 0.9.1, display warnings and retain unknown data at
seven locations through editing, copy/paste, save/load and undo. The current
writer version is stamped on save, and a higher source format is retained.

The unchanged synthwave v3 project has identical full-song export register data
in both versions: 6912 ticks, 189.8901098901 seconds. SHA-256 of the recorded
stream is `064a8ab4c63818ff0a8728945944b0b5182bfaf2c84d07c02b4b20fcf920edf6`.

A 12-second comparison from common native emulator state matched all **576000
raw and conditioned PCM frames**, ordered register writes/cycle calls and the
existing transport state. Independent cold runs initially had different PCM
hashes; repeated runs of the unchanged baseline did too, while their native
register/cycle traces matched. The existing `scripts/compare_pcm.py` documents
this emulator analog-dither issue. The comparison used that script's method:
warm native tables once, then fork isolated offline renders from the same state.
Production audio continues to use spawn. No emulator or output-conditioning code
was changed to force a match.

## Synthwave PW demonstration

The separate v4 sweep copy changes only 65 channel-1 PW entries: 64 steps across
patterns 000/001 and an instrument reset at pattern 002, row 000. The curve goes
from 680 hex down to 281 and back to 680 over about 10.55 seconds. Notes,
instruments, other channels, control data and the complete order list remain
identical to the supplied v3 project.

Full-song compressed exports passed their existing memory and replay checks:

| Output | Bytes | Ticks | Duration | Maximum cycle bound | Warnings |
|---|---:|---:|---:|---:|---|
| SID | 19858 | 6912 | 189.8901 s | 7560 | None |
| PRG | 20171 | 6912 | 189.8901 s | 7560 | None |

The accompanying 12-second MP3 is a native reSIDfp preview of the edited intro,
with the normal output conditioner and a short ending fade. The native project
and SID/PRG contain the full arrangement. Export validation is software evidence;
physical hardware listening remains for user testing.
