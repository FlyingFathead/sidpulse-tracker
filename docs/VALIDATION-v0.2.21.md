# SIDpulse Tracker v0.2.21 — export-analysis responsiveness

Date: 2026-09-17. Local source candidate based on the supplied v0.2.20 full ZIP.
No remote commit, push, tag, GitHub Actions run or published release is implied.

## Baseline and diagnosis

The user's preceding v0.2.20 environment reported **979 passed, no failures or
skips**. That is a user-supplied baseline result, not a run of this new candidate.

In v0.2.20, `export_squeezer.open_dialog()` called `analyze()` directly.
`analyze()` copied the song and ran `compile_prg()` / `compile_song()` before the
menu/key handler returned. `activate()` also recompiled synchronously when options
were changed. The pygame loop therefore could not draw or service events during
that work. A progress drawing call inside the same blocked handler would not fix it.

## Implemented change

The modal now schedules a job and paints an animated bar before starting it.
The bar uses the theme's existing SLIDER fill colour, a recessed track and no
handle; a solid band moves back and forth. It is an **indeterminate activity bar**,
not a calculated completion percentage. Elapsed time and actual compiler phase
labels are shown. The bar is pinned outside the scrolling body.

The analysis coordinator runs in a thread; it owns song copying, subprocess
startup, private-pipe IPC and cleanup. CPU-heavy compilation runs in a separate
Python process using an explicit spawn context on both supported platforms.
Only immutable status snapshots and a complete compiled result reach the UI.
No worker uses pygame, touches an audio device, writes an export/project or saves
preferences. CLI compilation does not start a worker.

Cancel is nonblocking to the UI and terminates/discards the private worker job.
Only Cancel is actionable during analysis; other controls are disabled to prevent
duplicate submissions and changing settings underneath a pending computation.
Worker errors become visible, retryable dialog errors. Cancelled/superseded results
cannot deliver into a new dialog. Jobs abandoned by another modal are cancelled;
a notice with a return-dialog link can temporarily retain the analysis safely.
Application shutdown cancels/reaps all outstanding jobs.

Save + export and Export only continue on the UI thread after a successful result
and source-snapshot check, including when changed options require re-analysis.
Native-save/browser failures restore the dialog and clear the pending continuation.
Existing file browsers, overwrite/backup logic and machine-preference saving remain.

## Checks executed in this container

Python 3.13.5, dependency-light focus:

```bash
python -m pytest -q -ra tests/test_export_analysis_job.py tests/test_export_progress_gui.py tests/test_squeeze_gui.py tests/test_channel_squeeze.py tests/test_phrase_optimizer.py tests/test_squeeze.py tests/test_incremental_update.py tests/test_replay_cycles.py tests/test_player_build_metadata.py tests/test_project.py tests/test_editor.py
```

**262 passed, 2 skipped in 59.67 seconds.** The two skips are whole native pygame
GUI modules, not successful UI tests. The focus includes **16 new worker/progress
checks**, also run separately (16 passed in 5.53 seconds).

The new dependency-light tests actually start fresh Python compiler processes.
They compare both SID and PRG results with direct compilation with squeeze on/off;
exercise cancellation during a deliberately stalled worker and before startup;
check child-process reaping, snapshot copying off the caller thread, no pygame
import in the child, source/file preservation, worker crash and compiler error
reporting, process-startup failure and real phase-callback byte equivalence.

Full-suite attempt with `--continue-on-collection-errors`:
**572 passed, 10 skipped, 21 failed, 17 collection errors in 64.13 seconds.**
Failures/collection errors report unavailable pygame, pyresidfp or py65, including
the audio-worker assertion containing the missing-pyresidfp error. This is **not a
full-suite pass**. Neither the user's baseline count nor skipped GUI modules are
being counted as validation of the new GUI.

Python syntax compilation passed. New/changed files passed whitespace and archive
path checks. The checked updater was exercised on a fresh v0.2.20 extraction,
including check-only preservation, backed-up application, repeated application,
CRLF inputs, refusal of unexpected edits and unrelated-file preservation.

## Export invariance

All four bundled PAL/NTSC native projects were recompiled to SID and PRG, with
squeezing disabled and enabled: **all 16 output hashes match v0.2.20 exactly**.
All eight deterministic benchmark/report entries also match, excluding wall time.
No source song changed. Measurements are supplied alongside this release.

The C64 assembly sources and all bundled player/loader binaries are unchanged.
There is no new replay layout, native song format, compression algorithm, audio
setting or dependency pin in this update. The optional progress callback only
reports compiler phases and processed-tick counts.

## Native checks still required

pygame-ce 2.5.7, pyresidfp 0.17.0 and py65 1.2.0 were unavailable here. Installation
in an isolated environment was attempted, but package-index access failed;
a direct connectivity check could not resolve pypi.org. No substitute/mock pygame
implementation was used to pretend to execute native tests.

Run the complete suite in the existing project environment:

```bash
./.venv/bin/python -m pytest -q -ra
```

The new native GUI module includes deterministic UI-state tests and a real spawned
slow-worker/frame-loop test. It checks first-paint-before-start, moving slider-colour
pixels, theme overrides, small/high-zoom layouts, duplicate suppression, responsive
resize/Cancel, late results, errors, notices, changed snapshots, native-save failure
and post-analysis save/export continuations. Existing GUI integration tests now
pump frames and await the real analysis job instead of assuming synchronous results.
These native tests have **not** run in this container.

Manually check the actual animation, responsiveness and Cancel on Linux and Windows;
listen while analyzing to assess audio scheduling on those hosts. No desktop
screenshot, native audio, Windows, 64tass, VICE or real-hardware run was completed here.
The existing replay/hardware release gates remain distinct from this UI fix.

## Local release validation — 2026-09-17

The maintainer's Linux run of `./.venv/bin/python -m pytest -q -ra`
completed with **1023 passed, zero failures and zero skips** in 264.79 seconds.
The export UI was also exercised manually and reported working well.

These results supersede the earlier dependency-limited local checks for this
version. They do not establish VICE/real-hardware or Windows validation;
consult the release commit's CI runs for cross-platform and assembler results.
