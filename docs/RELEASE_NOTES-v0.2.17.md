# SIDpulse Tracker v0.2.17

## Startup splash correction

The startup splash now presents the two actual choices:

- **New song** creates a blank `Untitled` project.
- **Play demo song** keeps the bundled editable **Autumn at five** project and
  starts playback as before.

Escape follows **New song**. This fixes v0.2.16 behavior where dismissing the
splash without playing still left the demo song loaded in the editor.

The **Don't show this on startup** preference is unchanged. Explicit
`--play-welcome-song` playback is unchanged, as are audio startup behavior,
project format 6, dependency pins and export semantics.

## Compatibility and limits

This is a focused UI/startup bug-fix release over v0.2.16. No song-format,
sequencer, SID-player, audio-buffer or dependency changes are introduced.

Download `sidpulse-tracker-v0.2.17-full.zip` and
`sidpulse-tracker-v0.2.17-SHA256SUMS.txt`. Verify the checksum, then follow the
README. The release-validation procedure is recorded in `docs/VALIDATION.md`.
