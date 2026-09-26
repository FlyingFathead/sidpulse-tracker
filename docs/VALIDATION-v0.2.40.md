# v0.2.40 local validation

## Results in the release-prep tree

- Linux / Python 3.12.14, pygame-ce 2.5.7, SDL dummy video and audio devices:
  **1,733 passed in 663.91 s** (`python -m pytest -q`).
- `python -m sidpulse --headless-smoke --example` and
  `python -m sidpulse --headless-smoke --play-welcome-song` both passed.
- Command and effect reference builders completed with **282** command records
  and **64** effect entries. Their generated files matched the prepared tree.
- `VERSION`, `pyproject.toml` and `sidpulse/__init__.py` all say **0.2.40**.

The preceding [checkpoint-002 checks](VALIDATION-v0.2.39-pattern-bank-drop-checkpoint-002.md)
cover F11 gestures and protected rows, octave order, compatibility notices,
screenshots, and short dummy-device audio/UI comparisons. The
[checkpoint-001 checks](VALIDATION-v0.2.39-pattern-bank-drop-checkpoint-001.md)
cover the F4 backup/clear and dropped-project paths. This version bump does not
change their underlying implementations.

Release publication requires the exact pushed commit and the annotated tag to
pass all four Ubuntu/Windows CI matrix jobs. The release helper verifies both
runs before building the ZIP from the tag. Those remote results are not part of
this local validation record. Desktop audio and GUI checks on the release
machine remain appropriate because SDL dummy devices cannot establish hardware
behavior.
