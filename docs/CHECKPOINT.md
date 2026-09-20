# SIDpulse Tracker v0.2.38 checkpoint

UI scale hotfix for F2/F5. Extra channels no longer force the whole page into a
smaller font. The existing horizontal channel-follow behavior handles overflow.
Minimum fitting remains only for essential editing space. See
[release notes](RELEASE_NOTES-v0.2.38.md) and [validation](VALIDATION-v0.2.38.md).

# SIDpulse Tracker v0.2.37 checkpoint

Playback order navigation, centered file browsing and exact frozen drum presets
are implemented. Windows FFmpeg installation/preflight is included; the actual
Windows runner still requires a new Actions run. Sequencer navigation preserves
the sample clock and existing voice programs. See [release notes](RELEASE_NOTES-v0.2.37.md),
[validation](VALIDATION-v0.2.37.md) and [performance](PERFORMANCE-v0.2.37.md).

# SIDpulse Tracker v0.2.36 checkpoint

Source-driven drum fitting now distinguishes short attacks, bass pitch decay
and noise content, using settled reSIDfp candidate renders. The reference kick
and snare and native save-label change are validated. Host idle scheduling,
redraws and metering are optimized; the sequencer and export algorithms, all
SQUEEZER versions and both DIGI methods remain intact. Spawned compilers request
lower POSIX priority. Runtime checks cover 2048 default / 512 stress buffers;
512-sample export stress still has measured underruns and is not certified
gap-free. See the raw results and limits in the performance report.
See [release notes](RELEASE_NOTES-v0.2.36.md),
[validation and performance](VALIDATION-v0.2.36.md), and
[synthesis details](SAMPLE_SYNTHESIS.md).

# SIDpulse Tracker v0.2.35 checkpoint

Restored packed volume DIGI as method #1 and the export default. The display
stays enabled; waveform-DAC DIGI is retained as method #2 with explicit blanking.
The UI/CLI selector, preference migration and method-specific confirmation are
implemented. Current triggers, remapping, music packers and source projects are
preserved. Sample-to-SID synthesis remains the development priority.
See [release notes](RELEASE_NOTES-v0.2.35.md),
[validation](VALIDATION-v0.2.35.md), and [performance](PERFORMANCE-v0.2.35.md).

# SIDpulse Tracker v0.2.34 checkpoint

Sample-to-SID wavetable synthesis is the preferred C64 workflow and current
priority. W waveform automation and sync/ring modulation FX are implemented
to support instrument shaping in patterns. The original
reference kick and snare are included in examples/samples. PCM export now offers
Continue as DIGI / Synthesize all samples / Cancel, with synthesis recommended.
Batch fitting reuses shared samples, offers audition before replacement, and
applies all replacements in one undo step before reanalyzing ordinary SID export. See
[waveform behavior](PATTERN_WAVEFORM.md),
[release notes](RELEASE_NOTES-v0.2.34.md) and
[performance checks](PERFORMANCE-v0.2.34.md).

# SIDpulse Tracker v0.2.33 checkpoint

PCM repair, sample normalization and volume tools, wavetable synthesis,
source provenance, and general instrument Freeze/Unfreeze are implemented.
See docs/RELEASE_NOTES-v0.2.33.md, docs/PCM_AND_AUDIO.md,
docs/SAMPLE_SYNTHESIS.md and docs/PERFORMANCE-v0.2.33.md for behavior,
validation and remaining hardware limitations.

# SIDpulse Tracker v0.2.31 checkpoint

- WAV/MP3 export through the shared file browser, explicit format and extra
  loops (default 0), background jobs, cancellation and atomic backed-up saves.
- Embedded PCM bank, F3 cached waveform and start/end markers, numeric frame/ms
  edits, root note, squeeze/restore and instrument sample overrides. Undo and
  format-8 native saves include the sample data; SID-only files remain 6/7.
- Separate experimental C64 PCM-enhanced RSID/PRG player, with CH1/2 SID and
  CH3 packed four-bit digis. Original SID player/squeezer remain the default
  for songs without overrides. Every PCM export checks bytes, writes, loops,
  samples, memory and instruction budgets. Physical C64 testing is pending.
- Supplied synthwave demo is preserved, with a separate PCM drum version.
  Full mixed C64 demo fits 35,327 loaded bytes and passes emulator playback.
- 1,502 full regression tests, 205 focused follow-up checks, eight identical
  SID-only PCM/register fixtures from shared native initialization, and serial
  matched audio/UI/live measurements. Default 2048 buffer is clean; 512 stress
  outliers are included in the report. No feature was disabled for that result.
- Full/incremental ZIPs share the sidpulse-tracker root and are checked for
  exact overlay equivalence. No remote push, tag or publication.

See docs/PCM_AND_AUDIO.md, docs/PERFORMANCE-v0.2.31.md,
docs/RELEASE_NOTES-v0.2.31.md and docs/APPLY-v0.2.31.md.

## Previous v0.2.30 checkpoint

- Tracker 0.2.30 / SQUEEZER v2.0.2; native formats remain 6/7. Existing saves,
  native synthesis, recording and editing semantics remain unchanged.
- v2.0.2 adds one-byte dictionary IDs for frequent immutable blocks and
  single-execution phrase calls. Repeated calls and shared suffixes remain.
  The 336-byte dictionary and decoder are included in full resident costs.
- v8 gains another 1,245 bytes beyond v2.0.1; register packet data shrinks
  1,665 bytes and player grows 420 bytes. SID maximum cycles rise 8,172 to
  8,287. All earlier candidate families remain selectable and eligible.
- Four-version analysis shows all versions by default; saved Top 3 remains optional.
  `export_show_all_versions` defaults true and saves immediately on checkbox changes.
  Shared overflow scrollbars are integrated across the UI. Minima, complete ties,
  current-choice preservation, measured CPU, immediate selection, config and
  cancellation remain supported. No compilation occurs during drawing.
- v1.0/v2.0/v2.0.1 optimizer sources and player binaries are unchanged. Six new
  players use existing mutable state with no new per-stream fields or buffer.
- Independent 6502 tests cover every call's cycles, ordered SID/CIA writes,
  loop/stop/reinit, decimal flag, workspace and dictionary immutability.
- Serial export and native performance evidence is under validation/v0.2.30.
  All four bundled examples and unchanged native v8 are used. Native baseline
  is immutable v0.2.29 (e4e38c1); M/S and scopes stay enabled.
- GoatTracker 2.77 source and the supplied Luxocrates explanation of Hubbard's
  player were studied for concepts. Acknowledgments and findings are in docs.
  No third-party code, transcript or song data was incorporated.
- Exact arithmetic-packet prototype was rejected: one-byte saving on the best
  stress layout did not pay for the decoder. It is not in the shipped runtime.
- Supplied SP window icon loads once before window creation; optional Linux
  desktop integration is documented. README GIF/MP4 captures actual F5 playback
  of bundled Autumn at Five, with all three scopes and no source mutation.
  The full MP4 covers one complete 96-second pass with audio; the GIF stays short.
  README official-source notice is immediately below the logo.
- Full and incremental archives retain executable run.sh and common root;
  final-named cumulative overlay supports v0.2.26 through the earlier v0.2.30.
  No remote push, tag or publication.

See docs/SQUEEZER-v2.0.2.md, docs/PERFORMANCE-v0.2.30.md,
docs/VALIDATION-v0.2.30.md and docs/APPLY-v0.2.30.md for results and limits.
Potential later work: note/effect bytecode, duration/transposition and deeper
song-specific code generation, only with complete state/timing equivalence.
