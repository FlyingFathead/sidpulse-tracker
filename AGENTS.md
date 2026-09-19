# SIDpulse Tracker development

- Run matched performance checks for every code release. Keep the previous
  release as an immutable baseline, use identical input/settings, and report
  CPU time for UI and audio separately. Repeat timing trials serially; do not
  run tests, profilers or other heavy work alongside measured trials.
- Profile regressions before optimizing. Keep requested features enabled in
  the default comparison. If a toggle is added, measure its enabled/disabled
  cost separately. Do not call disabling a feature an optimization of it.
- Record environment, workloads, raw measurements, limits and before/after
  results. Check real-time playback for gaps and late callbacks as well as
  offline rendering cost. Preserve the input song.
- Verify user-visible rendering, input, undo, save and playback behavior after
  changes. Performance changes must preserve sound and editing semantics.
- Deliver full and incremental ZIPs with SHA-256 checksums. Both extract under
  `sidpulse-tracker/`; verify the overlay matches the full archive exactly.
- Keep private project notes and developer-machine paths out of tracked files
  and release archives. Do not push, tag or publish a release without a request.
