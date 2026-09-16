# SIDpulse Tracker v0.2.16

## Shared file browser and editable filenames

F9 Load, F10 Save, Save As, Export SID and Export PRG now share one visible
directory browser. Filename and directory fields have movable carets, selection,
non-destructive editing and clipboard shortcuts. Save As starts before the
extension without selecting the entire filename. The latest successful open or
save supplies the next default, and folder navigation preserves filename edits.

F10 opens the Save browser; Ctrl+S/W still quick-saves outside it. Overwrite
confirmation, cancelled operations and I/O errors keep the editable draft.
Export does not rename the native project or falsely mark it saved.

## Other improvements since v0.2.12

- Type 0..7 at a note's octave digit without changing its pitch class,
  instrument or effects. Existing Skip and undo/redo behavior is preserved.
- Configure display-only beat/bar shading in F12, including a 12/48-row
  shuffle layout. This does not alter musical timing.
- F4 instrument activity dots follow actual triggers and gated voices during
  playback and audition. Selection alone does not light them.
- ADSR attack 00 draws vertically in the schematic envelope view; the actual
  SID attack rate and audio behavior are unchanged.
- F11 exposes "Loop song when the playlist ends"; click or press L. F12 shares
  that setting. Final-row changes are honored at the end boundary; F6 pattern
  looping remains separate.
- Implemented effects no longer incorrectly report sequencing as pending.
  Oversized SID exports clearly say "Shorten or simplify the project and try
  again", with exact byte counts and the existing hard limit.

## Compatibility and limits

The existing 2048-sample default and explicitly saved audio settings are retained.
Native song format stays 6. This is the complete v0.2.16 release; no incremental patch chain is required.

PCM/digi playback is not implemented, so sample activity dots remain idle.
WAV/MP3 export and more compact SID-player encoding are not included. The memory
limit for compiled SID exports is unchanged; a valid editable `.sidpulse` can
still be too large to export.

Download `sidpulse-tracker-v0.2.16-full.zip` and
`sidpulse-tracker-v0.2.16-SHA256SUMS.txt`. Verify the checksum, then follow the
README. User songs, environments, recovery files and private working notes are
not release assets. Local incremental ZIPs are not needed for installation.

The release-validation procedure is recorded in `docs/VALIDATION.md`. This is
work-in-progress software; keep backups of editable projects.
