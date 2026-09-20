# Validation and performance: v0.2.36

## Focused regressions

**216 focused checks passed in one integrated run:** synthesis, batch conversion,
file-browser, SQUEEZER selection, audio/transport, output devices, scopes,
conditioning, metering, sample streams and spawned export workers.
This is a targeted run, not a rerun of the whole historical suite. The complete
pytest result is retained in `validation/v0.2.36/integration-tests.txt`.

The checks cover selected-range isolation, unchanged source samples, frozen
instrument editing, save/load provenance, independent SID export, worker
completion/cancellation, native startup settling on 6581/8580, and fast drum
onsets with retained snare noise stages. The file menu was rendered and visually
checked at 640x480 and 1280x900; evidence images are in `validation/v0.2.36/`.

The exact delivered drum project reloads with its instrument data intact and
compiles as ordinary PSID and PRG with versions 1, 2, 201 and 202. The saved
source bank has no mapped PCM overrides. Default v2.0.2 exports and the complete
size/hash report are included in the evidence directory.

## Matched audio measurements

The before instruments were fitted by the unmodified supplied v0.2.35 snapshot;
the after instruments were fitted by v0.2.36. Both sets were rendered using
the same settled PAL/8580, C-4, tempo-125 audition path at 48 kHz. Each render
is one second including the release tail. Analysis downsamples to 12 kHz and
excludes subsonic bias; the delivered MP3 audio is not processed this way.
Energy values are signed-16-bit PCM units, not perceptual quality percentages.

| Instrument | First 20 ms RMS | Peak of 5 ms RMS envelope |
|---|---:|---:|
| Kick before | 321 | 57.5 ms |
| Kick after | 3056 | 7.5 ms |
| Snare before | 2392 | 17.5 ms |
| Snare after | 2906 | 5 ms |

These measurements show earlier energy delivery, especially for the kick;
they do not establish that a one-voice SID reconstruction matches every layer
of the original recording. Listen to the delivered MP3s and audition the saved
project in an arrangement. The snare recipe contains both pulse and noise
stages, with their pitches independently chosen.

MP3 files are mono, 48 kHz, 192 kbit/s, encoded from the native SID renders with
no added gain, normalization, compression or effects. The source references
are the unchanged original 48 kHz WAVs, not their optional auto-squeezed copies.
Both fits compensate 10 ms of detected quiet lead-in without changing markers
or sample data. MP3 encoder framing adds container padding around the one-second
render; the encoded stream includes gapless timing information.

## Cost and unchanged runtime

The final serial fit took 12.78 seconds / 247 candidates for the kick and
16.42 seconds / 274 candidates for the snare
inside this environment. Candidate rendering now includes a one-second chip
settle and broader analysis, so this is more offline work than the old fitter.
The search is capped at 320 candidates and remains in the cancellable worker.
No additional work is inserted into the playback/audio callback. No new
runtime dependency was introduced.

The sequencer, SID backend, song model, project format, export encoders and
player images match the supplied snapshot byte for byte. Host audio idle
scheduling, meter calculations and UI redraw scheduling were optimized after
a stopped-state CPU report; see [runtime performance](PERFORMANCE-v0.2.36.md). Spawned POSIX compilers also request lower scheduling priority without
changing results or the main process priority. The 198 serial performance trials
include a 24-trial export follow-up. The default 2048 export follow-up had no
missing frames; 512 export stress still underrran in one candidate trial.
Both DIGI methods and every SQUEEZER implementation are retained. There is no claim of a new
hardware benchmark; physical C64 listening remains untested for these recipes.
The full ZIP and the incremental overlay are checked for byte-identical results.
