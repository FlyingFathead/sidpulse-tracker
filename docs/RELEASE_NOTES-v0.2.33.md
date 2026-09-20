# SIDpulse Tracker v0.2.33

This update repairs a concrete source of C64 PCM switching artifacts and adds
sample shaping, sample-to-SID wavetable fitting, and instrument protection.
The existing WAV/MP3 browser, extra-loop count (default 0), embedded PCM bank,
channel remapping and best-of-version export comparison remain available.

## C64 PCM playback

The previous routine changed SID master volume for each PCM sample and restored
full volume while leaving the bias voice active. That produced discontinuities
and also modulated the other SID parts. Correct sample bytes and note triggers
were insufficient evidence of clean playback; the earlier v0.2.32 register and
sample-neutralization checks overstated what they proved about sound quality.

The new routine uses timed waveform-DAC captures. It holds a neutral DAC state
between hits, primes the mixer before musical time, and explicitly returns CH3
to normal SID synthesis when a waveform instrument plays. Other voices keep
their programmed master volume. Export still rotates a single tracker PCM
channel to hardware CH3 and preserves the source project's channel layout.

The tradeoffs are visible in the export menu: **display and sprites are blanked
while playing**, and exported PCM uses one frequency byte per 4-bit frame
instead of two samples per byte. The editable project still uses packed samples.
The selected SID model and PAL/NTSC clock must match the playback machine.
RUN/STOP restores the display and returns to BASIC.

The isolated drum test's 8580 neutral-trigger recording now has a peak of 50
signed-16-bit units after BASIC autostart, including the music startup. Repeated
silent hits remain close to the emulator noise floor. The full HERMO.ROM test
retains all 32 kick/snare hits while
both other SID channels play: measured isolated hit windows are approximately
188–192 RMS for kicks and 95 RMS for snares. PAL and NTSC builds run through the
whole arrangement and into the loop in VICE with both 6581 and 8580 models.
These levels are measured at the original project gain, without boosting the
project or normalizing the evidence recordings.

This addresses switching behavior, not the inherent fidelity or balance gap
between four-bit C64 playback and host PCM. Chip-specific amplitude, distortion
and physical-hardware playback remain experimental. The new F3 warning states
this directly. The C64 display/timer ownership model is unsuitable for dropping
into another game/demo unchanged.

## Sample shaping and wavetable instruments

F3 adds **Normalize**, with an OK/Cancel confirmation, and **Adjust volume**,
with a linked 0–200% slider and numeric field. The volume dialog opens at 100%,
which makes no change. Both act on the marked range, preserve bit depth and
markers, retain the original and support undo. Normalization before squeezing
defaults on; after squeezing defaults off. Both preferences are saved and used
by F3 and F4 imports. Opening a project does not convert its samples.

**Synthesize audio (create wavetable)** fits 12 ms–2 seconds of marked audio to
an ordinary SID instrument. It searches waveform/pitch sequences, pulse width,
ADSR and gate settings using actual SID renders. Work runs in a cancellable
background process. The proposal browser lets you audition source/result and
choose one of 99 instrument slots. Empty slots accept directly; any occupied
slot requires confirmation. The source sample remains available.

F4 displays **Synthesized from sample NN: "filename"** between solid lines.
Generated instruments start frozen against accidental edits. **Unfreeze / Freeze**
is available to all instruments and saved in projects; toggling it supports undo.
Unfreeze to experiment with normal controls. Pattern automation and playback
continue while frozen, because protection applies to stored instrument edits.

The fitter is a prototype and may produce a related timbre rather than a close
reconstruction, especially for layered sounds, voices or reverb. It introduces
no new effect command, real-time synthesis engine or mandatory dependency.
See [findings and credited references](SAMPLE_SYNTHESIS.md), including the
MIDIbox wavetable tutorial, MSSIAH and zBlex. Reference PDFs are not bundled.

## Validation and installation

Native audio, conditioned audio, SID writes/cycles and sequencing state match
v0.2.32 exactly across seven songs, including 200 seconds of the three-channel
PCM tester. Source projects remain unchanged. Regression checks cover sample
edits, synthesis, audition, occupied/empty slots, cancellation, save/load, freeze
and undo. UI checks cover 640×480, 960×1080 and 1280×900.

Final regression counts and matched performance measurements are recorded in
[PERFORMANCE-v0.2.33.md](PERFORMANCE-v0.2.33.md) and `validation/v0.2.33/`.
Measurements distinguish UI CPU, audio CPU, callback delays and gaps. Emulation
uses VICE 3.7.1 classic reSID; physical audio-device and physical-C64 testing
remain outside this environment.

Use the full ZIP, or apply the incremental ZIP to v0.2.32 following
[APPLY-v0.2.33.md](APPLY-v0.2.33.md). Both archives extract under the same
`sidpulse-tracker/` root and their overlay is checked for exact equivalence.
