# SIDpulse Tracker v0.2.16 release checkpoint

This tree is the intended **final v0.2.16 release**. The application version is
**0.2.16** and the public Git tag/release name is **v0.2.16**.

## Included work

v0.2.16 contains the shared Load/Save/Save As/Export file browser with
non-destructive filename editing, plus the fixes accumulated since v0.2.12:

- effect-entry status correction;
- configurable display-only beat/bar shading;
- exact oversized-SID-export diagnostics and the clear “Shorten or simplify”
  recovery instruction;
- direct octave-digit entry;
- instrument activity indicators;
- corrected schematic ADSR attack-00 display;
- F11/F12 song-end loop control and final-row loop-state fix.

Native project format remains 6. No WAV/MP3 exporter or compact SID-player
encoding is claimed in this release.

## Maintainer validation completed locally

On the maintainer's Linux checkout, the complete test suite reported:

```text
693 passed
```

Both headless smoke tests also completed successfully:

```bash
./.venv/bin/python -m sidpulse --headless-smoke --example
./.venv/bin/python -m sidpulse --headless-smoke --play-welcome-song
```

`git diff --check` also completed without errors after the current changes.
See `docs/VALIDATION.md` for the stable validation procedure.

## Remaining release gates

Before publishing:

1. review and commit the intended v0.2.16 tree;
2. push `main` without force;
3. verify the exact pushed commit passes the GitHub Actions matrix;
4. create and push annotated tag `v0.2.16` on that verified commit;
5. build the full source ZIP from the tag;
6. create and verify the SHA-256 checksum file;
7. publish only the reviewed tag-built release assets.

No remote CI result, release tag or GitHub release is implied by this checkpoint
until those steps have actually completed.

## Licensing note

The tree currently has no project-wide `LICENSE` for the original SIDpulse code.
No license is selected by the v0.2.16 documentation work; third-party notices
remain in `docs/THIRD_PARTY.md`.
