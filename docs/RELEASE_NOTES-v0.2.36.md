# v0.2.36 — drum fitting and explicit project saving

The old sample fitter could favor slow, weak drum attacks and mistake the
emulator's startup decay for the source sound. This update settles each chip
before measuring it, separates transient and bass analysis, and fits a falling
pitch mathematically. Drum fitting now scores native attack energy and the
snare's noise/body balance. ADSR is revisited after waveform stages change.

Stopped audio now suspends SID rendering, conditioning and scope measurements
once the transport fade or audition release has finished. Active note commands
wake it immediately. Quiet windows redraw at 5 Hz while input/services keep
polling at 60 Hz; playback, active jobs and interaction retain full-rate drawing.
Meter calculations use the existing NumPy dependency instead of per-sample
Python loops. The 2048-sample default remains unchanged; 512 is the stress case.
Spawned export compilers use lower POSIX priority so playback gets preference
under CPU contention. Export may still use a full core. The README now explains
the application before its feature list and offers Git and release-ZIP installs.
The 2048 export follow-up had no missing frames; 512 export stress still
underran in one trial. See the matched [performance checks](PERFORMANCE-v0.2.36.md).

The File menu and native save browser now say **Save as .sidpulse...**.
The save behavior and keyboard shortcuts are unchanged.

Generated instruments remain frozen by default and self-contained. Both DIGI
methods and SQUEEZER v1.0, v2.0, v2.0.1 and v2.0.2 are retained, with v2.0.2
still the default. Sequencing, player images and export encoders are unchanged. Host scheduling
and metering now avoid redundant idle work.
Previously saved fitted instruments retain their sound; run synthesis again
to obtain a new proposal and audition it before replacing an instrument.

The example `examples/synthesized-reference-drums.sidpulse` contains the exact
kick/snare recipes used for the supplied MP3 renders, at C-4, tempo 125,
PAL/8580. Each MP3 is one native SID hit, with its release tail and no added
gain, normalization, compression or effects. The original source WAVs remain
unchanged in `examples/samples/`. These are source-driven one-voice SID
reconstructions, not exact copies of layered samples.

See [the synthesis method and limitations](SAMPLE_SYNTHESIS.md),
[validation and performance](VALIDATION-v0.2.36.md), and
[installation instructions](APPLY-v0.2.36.md).
