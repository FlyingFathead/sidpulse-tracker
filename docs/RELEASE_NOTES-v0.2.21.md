# SIDpulse Tracker v0.2.21 — song squeezing and responsive exports

- Default-enabled, optional song squeezing for SID and PRG exports only.
  Reuse repeated channel phrases and compact timing/register data, with
  byte-cost selection and playback verification. Native projects stay intact.
- Keep export analysis outside the UI event loop. Show an animated,
  slider-colour activity bar, processing-stage labels and elapsed time.
- Keep Cancel and window events responsive; reject stale results and show
  worker errors without unexpectedly saving files.
- Retain strict replay-cycle checks, including the test-only py65 timing
  correction and updated native export-workflow regression tests.

No new runtime dependency or native song-format conversion is required.
Packed playback reads compressed data directly without expanding the entire song.
Ordered tick/write verification does not guarantee cycle-identical spacing
within a tick or identical analog behaviour on every SID chip.

## Local release validation — 2026-09-17

The maintainer's Linux run of `./.venv/bin/python -m pytest -q -ra`
completed with **1023 passed, zero failures and zero skips** in 264.79 seconds.
The export UI was also exercised manually and reported working well.

These results supersede the earlier dependency-limited local checks for this
version. They do not establish VICE/real-hardware or Windows validation;
consult the release commit's CI runs for cross-platform and assembler results.
