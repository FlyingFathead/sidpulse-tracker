# SIDpulse Tracker v0.2.21 release checkpoint

Application 0.2.21; native format 6, unchanged.

## Local release validation — 2026-09-17

The maintainer's Linux run of `./.venv/bin/python -m pytest -q -ra`
completed with **1023 passed, zero failures and zero skips** in 264.79 seconds.
The export UI was also exercised manually and reported working well.

These results supersede the earlier dependency-limited local checks for this
version. They do not establish VICE/real-hardware or Windows validation;
consult the release commit's CI runs for cross-platform and assembler results.

See docs/RELEASE_NOTES-v0.2.21.md and docs/VALIDATION-v0.2.21.md.
Historical candidate checks are retained in the validation document.
