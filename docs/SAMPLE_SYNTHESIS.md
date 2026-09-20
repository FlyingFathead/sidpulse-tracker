# Sample-to-SID wavetable synthesis: findings and considerations

## Current priority and preferred workflow

**Sample-to-SID wavetable synthesis is the preferred C64 workflow and the
current development priority.** Import a short sample in F3, mark the useful
range, run Synthesize audio, compare the source and fitted instrument, and
choose an instrument slot. Use the normal SID export once the arrangement
uses synthesized instruments in place of PCM overrides.

The C64 export warning also offers **Synthesize all samples**, selected first,
alongside **Continue as DIGI** and **Cancel**. It fits every PCM-mapped instrument,
including unused mappings that would otherwise select the DIGI routine. Unmapped
bank samples do not trigger the warning or get converted. Each distinct mapped
sample slot is fitted once; instruments sharing it receive independent copies.
Audition each source/result pair, then **Apply all + review export** replaces
all listed slots in one undo step and reanalyzes the ordinary SID export.
Names, instrument numbers, patterns and source samples stay intact. Cancel,
failed fitting and stale results apply nothing. Fitted instruments start frozen.

Batch conversion replaces the complete instrument sound, including existing
PCM gain, pitch/arpeggio, gate and retrigger programs. The fit uses the source's
marked range and root note. Audition the whole arrangement after applying it;
the fitter does not promise matching loudness or reproduce every PCM program.

The term follows C64 tracker usage: timed changes to SID waveform and pitch,
with pulse width and envelope shaping. It is not a claim that a SID voice can
faithfully reconstruct every sampled sound. Fit quality, especially drum
transients and noise texture, remains the main area to improve.

The frozen reference fits are also built-in F4 presets under
**[Wavetable] Drums & Percussion** (sidebar: **Wavetable drums**). They are the
exact recipes from `examples/synthesized-reference-drums.sidpulse`, requiring
no sample bank or new fitting pass. Audition C-4 at tempo 125, PAL/8580 for the
reference sound; Unfreeze makes their normal instrument controls editable.

Use the unchanged [reference kick and snare](../examples/samples/README.md)
for comparisons. Keep source audio, fitted audio and the settings together;
judge the sound in the complete arrangement as well as solo. A low fitting
score alone is not evidence of a good result.

## The intended sound model

**Synthesize audio (create wavetable)** analyses a marked PCM sample and proposes
an instrument made from SID waveform choices, relative pitches, pulse width and
an ADSR envelope. Waveform and pitch can change every tracker tick. At tempo 125,
that is 20 ms. This is the traditional C64 meaning of a wavetable: a sequence of
parameter changes that creates a composite sound. It does not replay the source
PCM through a different name.

The source remains in the sample bank. Accepting a proposal creates or replaces
one instrument, with an occupied-slot confirmation and one undo step. The result
window offers both source and SID audition before committing. Source provenance
is displayed between solid lines in F4 and saved in the project. Instruments
start frozen against accidental editing; Unfreeze exposes normal controls.
Freeze is an editor safeguard available to any instrument. Pattern automation
can still shape playback, and unfreezing does not detach or corrupt a hidden
sample engine. The generated instrument is self-contained.

## How the fitter works (v0.2.36)

The worker fits the selected range, up to two seconds, at 12 kHz. It measures
an attack envelope in 5 ms windows every 2.5 ms and spectra at three resolutions.
Long windows resolve the bass body; short windows locate the transient. Local
pitch measurements seed a falling-pitch model `f(t) = b + a * exp(-t / tau)`.
For each candidate decay time, weighted least squares solves the floor and sweep.
Measured local pitches and autocorrelation supply alternative trajectories.

Percussive ranges may have up to 30 ms of quiet lead-in removed for fitting;
the original markers and samples are untouched, and the amount is recorded.
Fast-attack candidates combine tonal bodies and independently pitched noise.
The loss compares spectrum, envelope, attack slope and high-frequency energy
fraction, so a strong bass body cannot hide a missing snare noise burst. Drum
attacks also compete against an absolute output-energy target calibrated with
an ordinary fast SID pulse on the selected chip model. This is a synthesis
constraint, not output normalization, compression or an added audio layer.

Up to 320 candidates are rendered through reSIDfp with the project's model,
clock and tempo. Each fresh chip settles for one second before note-on. The
old 50 ms warm-up left a substantial external-filter startup decay in the
measurement; the fitter could mistake that decay for the source's drum body.
Subsonic bias is excluded from analysis only, with the same response applied
to source and candidates. Actual playback and exported audio are not filtered
by this analysis operation.

The search refines ADSR, pulse width, pitch, gate and waveform stages, resolving
the first eight ticks individually. It refits the envelope after stage changes.
The frozen result uses existing waveform/pitch tables, each at most 64 steps,
and normal gate/release handling. At tempo 125 a step lasts 20 ms. No new
playback engine, register macros, audio effects or runtime dependencies are used.
All analysis stays in the cancellable worker. The source sample remains intact.

For the reference comparison, use the original 48 kHz WAVs with auto-squeeze
on import disabled, or restore the retained original before fitting. The saved
4 kHz / 4-bit auto-squeeze default remains available; fitting a squeezed source
necessarily starts with its reduced bandwidth and quantization noise.

## Limits and observations

A single SID voice cannot reproduce an arbitrary recording. A layered snare,
room response, speech or chord may only yield a related timbre. Most comparison features are normalized; the separate attack-energy constraint
penalizes weak drum onsets, but does not promise source-matched loudness. There is no perceptual
"percent identical" claim. Always audition the result in the arrangement.

Low, decaying kicks need care: a short analysis window weakens autocorrelation,
so an overly high confidence threshold incorrectly removes tonal candidates.
The current search retains those candidates and lets actual SID renders compete
with noise models. Tests cover low decays, noise, selected-range isolation and
an independently generated multi-waveform SID sound. More elaborate per-step
ADSR/pulse/filter tables and faster instrument update rates are future work,
with playback/export timing gates required before introducing them.

SID envelope history and retriggering also matter. The fitter uses the same
note-on path as playback; existing hard-restart handling remains in place.
Changing song tempo changes table timing, and changing root note or SID model
changes the result. Global filter or pattern automation already in the song can
alter an otherwise good solo audition. Saved provenance metadata records the
analysis settings for future reference; it does not lock the arrangement.

## PCM is a separate, retained option

MSSIAH's Wave-Player demonstrates 4-bit, 6 kHz sampling with three virtual
channels, sample memory and MIDI transfer. Its Drummer instead builds sounds
with changing SID waveforms and frequencies. These are two useful approaches;
the published specifications do not reveal the exact playback routine or
establish the same CPU budget as SIDpulse's mixed SID/PCM export.
[Official MSSIAH application descriptions](https://mssiah.com/mssiah.php).

SIDpulse keeps host PCM, WAV/MP3 export and experimental C64 PCM. The v0.2.33
C64 repair addresses its own switching and register ownership issues with a
stabilized waveform DAC (now DIGI method #2). v0.2.35 restores the original
display-preserving volume digis as method #1 and the default. Screen blanking
is specific to method #2. Emulation checks cannot certify every physical chip.
Wavetable synthesis is the preferred C64 path. PCM remains a separate choice,
and its playback defects still need to be fixed on their own merits. See [PCM usage and C64 constraints](PCM_AND_AUDIO.md).

## Design references and acknowledgements

Thorsten Klose's [MIDIbox SID Wavetable Sounds Tutorial #1](https://www.ucapps.de/howto_sid_wavetables_1.html)
explains reconstructing SID drums by analysing short waveform/pitch sections,
matching the table rate and considering envelope timing. It also distinguishes
waveform inspection from directly tracing SID register writes. The latter is
more exact when the original sound is already a SID program. Audio fitting has
to infer those parameters, so it is inherently less certain. The tutorial is
about MIDIbox SID V1; its commands and values are not copied into SIDpulse.

Gavin Graham's [zBlex V6 project](https://github.com/gavindi/zblex-v6) describes
independent macro tables for SID register groups and a programmable music
language. It is a useful reference for possible richer instrument tables.
SIDpulse's implementation here uses its existing program fields and does not
include zBlex source, bytecode, binaries or instrument data. Thanks to Gavin
and Thorsten for making these design explanations available. These references
are acknowledgements, not claims of affiliation or endorsement.

Pex "Mahoney" Tufvesson's
[Cubase64 white paper](https://livet.se/mahoney/c64-files/Cubase64_White_Paper_by_Pex_Mahoney_Tufvesson.pdf)
describes timed waveform-DAC playback and the importance of interrupt/raster
timing. [audio-bitsqueezer](https://github.com/FlyingFathead/audio-bitsqueezer)
provided useful sample conversion and C64 playback context. No third-party
reference PDFs are distributed with this release.
