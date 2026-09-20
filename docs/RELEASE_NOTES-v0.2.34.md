# SIDpulse Tracker v0.2.34

**Current priority: sample-to-SID wavetable synthesis.** The preferred C64
workflow creates ordinary SID instruments from short audio references;
improving the fits is the priority. PCM remains available as a separate option.

PCM-enhanced export now shows **Continue as DIGI / Synthesize all samples /
Cancel**, with synthesis recommended and selected first. It explains the
display/sprite and hardware-channel/timer tradeoff. Batch fitting offers
source/result audition before applying all replacements in one undoable edit.
Instrument numbers, names and embedded source samples are preserved. It then
reanalyzes ordinary SID export for review. Cancel, a failed fit or a changed
source applies nothing. Unmapped bank samples do not trigger the warning.

This update adds waveform automation in the pattern editor and puts sync/ring
modulation in the existing FX slot. W is the only new column.

- W: 1/T triangle, 2/S saw, 3/P pulse, 4/N noise, 0/R instrument/table, dot hold.
- FX Z10/Z11/Z1F: sync off/on/instrument default.
- FX Z20/Z21/Z2F: ring modulation off/on/instrument default.

Settings persist on their tracker channel. Changing a held note's waveform
keeps its gate state; restoring a waveform sequence resumes its current age.
Instrument settings and frozen state remain intact. PCM samples stay isolated
from oscillator controls, with overrides retained for the next SID note.
Existing effects and the ADSR/PW reset command keep their meanings.

W supports direct entry, field selection, edit masks, repeat, clipboard,
Paste Special and undo. The pattern and Info layouts fit the added field.
At the smallest window sizes the pattern viewport follows the selected channel.
Older cursor metadata is translated to the same logical field. Format 10 is
used only when W or the new FX commands are saved.

The author's supplied 48 kHz, 16-bit mono reference WAV files are included
unchanged as:

- `examples/samples/sidpulse_sample_synthwave_kick.wav`
- `examples/samples/sidpulse_sample_synthwave_snare.wav`

`PATTERN_ARPEGGIO.md` and `CHECKPOINT.md` move into `docs/`, their links are
updated, and obsolete root notes are removed completely. Development guidance lives in
the existing `docs/ROADMAP.md`. Incremental upgrades include an explicit cleanup
step to remove the old root documents; see the installation instructions below.

## Validation

The broad regression run completed 1,618 cases: 1,616 passed and two exposed
an 800-pixel layout fit and an old PW-column test index. Both were corrected;
the final 150 affected checks pass, including four additional PRG cases.
The 30 waveform-specific checks cover input, native persistence, undo,
held-note gate preservation, waveform-table age, independent persistent FX,
PCM isolation/handoff, PAL/NTSC SID writes, and squeezed/unsqueezed PRG startup.

A further 81 batch/media/export checks and seven remapping checks pass after
the export warning was added. These cover default selection, audition, worker
cancellation, failed/stale results, shared-sample fitting, atomic apply/undo,
save/reload, independent SID export and compact-window rendering.

Seven existing songs match the v0.2.33 baseline exactly for native PCM,
conditioned PCM, SID write/cycle traces and final playback state. This includes
a 200-second mixed PCM/SID arrangement and variable audio block sizes.
Repeated serial performance results and limits are in
[the performance report](PERFORMANCE-v0.2.34.md).

See [waveform usage](PATTERN_WAVEFORM.md) and
[installation/overlay instructions](APPLY-v0.2.34.md). No dependency changed.
