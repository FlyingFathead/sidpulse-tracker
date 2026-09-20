# Validation: v0.2.37

**124 focused tests passed:** 110 in the final integrated run (11.58 seconds),
plus the 13 previously failing FFmpeg-dependent cases and one MP3 decoding
check (14 passed in 2.94 seconds). This is a targeted regression run, not a
rerun of the entire historical suite. Logs are in `validation/v0.2.37/`.
The headless example smoke launch also completed successfully.

## Playback and performance

The checks cover order navigation at an exact fractional tick boundary,
retained voice state and instrument memory, repeated/queued skips, start/end
clamping, inactive modes, Modern/Classic key mappings, and real audio-worker
commands at both 2048 and 512 samples. Mouse buttons use the same worker command.
The ordinary buffer-partition timing, full-song events, native sustained audio,
idle release preservation, meter/output behavior and rendering caches still pass.

Six deterministic register/state traces match v0.2.36 exactly: SID arrangement,
PCM arrangement and the fitted drum example, each with PAL and NTSC timing.
These use the same mixed render partitions and compare ordered writes and
transport state. The probe script and hashes are retained with the results.
This verifies the measured windows, not every possible project or driver.

The performance audit contains 184 serial measurements: 174 matched matrix
trials, six longer PCM rechecks and four rapid-navigation trials. The candidate
has zero gaps/missing frames in all 58 live trials; all scopes remain enabled.
A candidate CPU outlier did not recur in the longer PCM recheck. A baseline
recording stall is also retained, including its missing frames. See the complete
[performance report](PERFORMANCE-v0.2.37.md) for raw results, absolute costs and
limits. 2048 remains the default; 512 is still a stress setting. These are
Linux SDL-dummy measurements; they do not certify physical audio or Windows.

## File browser and presets

Manual browser checks traverse 116-entry listings in Open, Save and WAV modes
at 640x480 and 1280x900. They cover arrows, paging, Home/End, mouse wheel,
centered selection with clamped ends, short directories and stable double-click
targets. The existing 34 browser GUI tests also pass in the integrated run.

Playback button availability and all ten preset categories were checked at
480x360, 640x480, 960x540 and 1280x900. Evidence screenshots show the navigation
buttons, small-window category layout and centered browser positions.

Both factory drum instruments compare exactly with their counterparts in
`examples/synthesized-reference-drums.sidpulse`. Tests verify independent copies,
frozen state, adding through the chooser, undo/redo, save/load and ordinary PSID
compilation with an empty sample bank. Their recipes, source WAVs and the
reference example are unchanged from v0.2.36, as are the supplied MP3 sounds.

## Windows media dependency

The prior Windows failures required FFmpeg but the workflow installed it only
on Linux. Windows now installs FFmpeg with Chocolatey and exports its executable
through SIDPULSE_FFMPEG. Both operating systems run the application's FFmpeg
lookup and `ffmpeg -version` before pytest. YAML and preflight Python were parsed;
the preflight succeeded locally, and a deliberately missing configured executable
failed immediately with the expected message. The reported 13 cases and the
additional MP3 check pass locally with FFmpeg. An actual Windows Actions run is
still required; no Windows success is claimed and no media tests were disabled.

## Release contents

Full and incremental ZIPs share the `sidpulse-tracker/` root. The incremental
base is the delivered v0.2.36 release. Extraction plus the idempotent cleanup is
verified against every full-release file. The full archive retains executable
`run.sh`. SHA-256 checksums accompany the downloads.

Source comparison verifies that export implementations/player binaries, SID
backend, voice programs, audio conditioning, sample fitter and example files
are unchanged. Both DIGI methods and all four SQUEEZER versions are retained.
Navigation adds a command and one pending destination; existing sample/tick
rendering and order-transition functions remain unchanged.
