# Validation

This document describes how to validate SIDpulse Tracker before committing,
tagging, or publishing a release.

It intentionally does not contain permanent test-count snapshots. Test counts
change as the suite evolves. Release-specific results belong in release notes,
CI logs, or the release checkpoint.

## 1. Automated test suite

From the repository root, using the project virtual environment:

```bash
./.venv/bin/python -m pytest -q
```

The release must not proceed if any test fails.

## 2. Headless smoke tests

Verify that the application initializes and exercises its basic playback paths:

```bash
./.venv/bin/python -m sidpulse --headless-smoke --example
./.venv/bin/python -m sidpulse --headless-smoke --play-welcome-song
```

Both commands must exit successfully.

## 3. Generated references

Regenerate the tracked command/effect references and inspect any resulting diff:

```bash
./.venv/bin/python scripts/build_command_reference.py
./.venv/bin/python scripts/build_effect_reference.py
git diff --check
```

Unexpected generated changes must be reviewed before release.

## 4. Source-tree checks

Before committing:

```bash
git diff --check
git diff --cached --check
git status --short --branch
```

Before tagging, the release commit should be pushed and the working tree should
be clean.

## 5. Version consistency

The release version must agree in all declarations:

```bash
cat VERSION
grep -nE 'version|__version__' pyproject.toml sidpulse/__init__.py
```

For v0.2.17, each application-version declaration must resolve to `0.2.17`.

## 6. Interactive tracker checks

Automated tests do not replace a short desktop run. Before release, verify at
minimum:

- application starts normally;
- startup **New song** opens a blank Untitled project and does not leave the demo loaded;
- startup **Play demo song** keeps and plays the editable welcome project;
- example/welcome project loads and plays;
- pattern editor accepts normal note input;
- typing `0`..`7` on the octave digit edits only the octave;
- instrument editing and audition work;
- instrument activity dots react to actual playback/audition rather than mere
  selection;
- ADSR display shows attack `00` at the left edge as intended;
- F6 pattern looping remains independent;
- F11/F12 song-end looping can be enabled and disabled;
- F9 Load browser works;
- F10 Save browser works;
- Save As offers the current project filename and permits non-destructive caret
  editing;
- filename edits survive directory navigation;
- overwrite Cancel returns to the same editable draft;
- SID/PRG export uses the shared browser without renaming the native project;
- `.sidpulse` save/load round-trip works;
- audio playback has no obvious hangs, underruns or stuck notes.

## 7. Export validation

For SID and PRG export:

- verify a small known project exports successfully;
- verify exported files are non-empty;
- verify an oversized project is rejected cleanly;
- verify the error reports required and available memory;
- verify the error tells the user to **shorten or simplify the project**;
- verify a failed export does not modify the editable `.sidpulse` project.

The exporter must never silently discard musical material to make a project fit.

## 8. Platform validation

SIDpulse targets Linux and Windows. The GitHub Actions matrix should pass on the
exact release commit before tagging/publishing.

Current CI covers Ubuntu and Windows on Python 3.10 and 3.12. Local validation
on one platform does not substitute for the remote matrix.

If an expected platform or interactive behavior has not been tested for a
release, state that explicitly rather than implying otherwise.

## 9. Release gate

A typical final local gate is:

```bash
set -euo pipefail
./.venv/bin/python -m pytest -q
./.venv/bin/python -m sidpulse --headless-smoke --example
./.venv/bin/python -m sidpulse --headless-smoke --play-welcome-song
./.venv/bin/python scripts/build_command_reference.py
./.venv/bin/python scripts/build_effect_reference.py
git diff --check
git diff --cached --check
git status --short --branch
```

Then confirm:

- all automated tests pass;
- both smoke tests pass;
- intended interactive checks pass;
- version declarations match;
- documentation matches the current behavior;
- no private/local files are staged;
- the pushed release commit passes CI;
- the annotated release tag points at that exact verified commit.

## 10. Release-specific evidence

Exact test counts, CI URLs, operating systems manually tested, known limitations
and intentionally skipped checks belong in the release record or checkpoint.

Do not rewrite this document merely because the number of tests changed.
