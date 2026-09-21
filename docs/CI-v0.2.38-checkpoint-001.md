# v0.2.38 CI repair: checkpoint-001

This checkpoint applies to the supplied v0.2.38 snapshot. It keeps the application
version at 0.2.38 and does not publish or replace an existing release.

## Causes

The failure occurs in the `python -m pytest -q` validation step shown in the
supplied job log.

| Failing check | Cause | Correction |
| --- | --- | --- |
| Narrow pattern view at 960x1080 | The old test requires three simultaneous channels, contradicting v0.2.38's requested-font-size behavior. | Expect two visible channels and verify that all three remain accessible by horizontal following without shrinking the font. |
| Narrow pattern view at 800x600 | The same obsolete three-channel expectation. | Check the actual two-channel layout, all 17 fields of each selected channel, and the control-panel toggle. |
| Empty instrument slot / preset persistence | The test assumes 39 factory presets, omitting the two reference wavetable drums added in v0.2.37. | Check the 39 existing presets plus the named reference kick and snare. Keep category, schema and user-preset persistence checks. |
| Pattern-length dialog at 480x360 / 300% | Dialog fitting measures an already-fitted page, then incorrectly multiplies the original requested zoom. This enlarges the dialog and overlaps the number field with OK/Cancel. | Multiply the effective rendered zoom by the fit ratio. Check stable repeated rendering and clicking the bottom of the number field. |

The runtime change is one expression in `Renderer.dialog`: use
`self.signature[2] * fit` in place of `app.zoom * fit`. The saved zoom is preserved.
Audio, sequencing, sample processing and all C64 export files match the input
snapshot byte for byte. No tests are skipped, removed or marked as expected failures.

## Validation

The unmodified snapshot reproduces all four failures: **4 failed, 1693 passed**
in 554.72 seconds. The initial v0.2.38 validation covered 111 selected tests and
did not cover these failures.

The corrected focused run passes **56 tests**, including the narrow-window,
factory-preset, pattern-length, page-zoom, sample-normalization and audio-settings
checks. Both CI startup commands pass:

```bash
python -m sidpulse --headless-smoke --example
python -m sidpulse --headless-smoke --play-welcome-song
```

The 480x360 / 300% pattern-length dialog was also rendered and visually inspected:
the value, slider, labels and buttons are visible and do not overlap.

Complete suite: **1,697 tests collected; the full pytest process completed
successfully with exit code 0**. The retained progress log contains 1,693 passing
cases and omits the final output segment. The remaining four startup tests were
also rerun explicitly: **4 passed** in 0.37 seconds. No failed cases appeared in
the corrected full run.

Environment: Linux, Python 3.12.14, pygame-ce 2.5.7, pyresidfp 0.17.0,
NumPy 2.5.3, pytest 9.1.1 and py65 1.2.0. SDL dummy video/audio drivers were used.
The Python 3.10 and Windows CI combinations require confirmation on GitHub.
This work does not claim physical audio-device testing or rerunning the
unchanged C64 assembly rebuild checks.

## Apply

Download the incremental ZIP, the matching `apply-sidpulse-tracker-v0.2.38-checkpoint-001.py`
launcher and `SHA256SUMS-v0.2.38-checkpoint-001.txt` into the parent of the existing
`sidpulse-tracker/` checkout. Close the tracker first.

```bash
sha256sum --check --ignore-missing SHA256SUMS-v0.2.38-checkpoint-001.txt
python3 apply-sidpulse-tracker-v0.2.38-checkpoint-001.py --check
python3 apply-sidpulse-tracker-v0.2.38-checkpoint-001.py --apply
```

The launcher checks the archive and every replacement against the supplied
snapshot, refuses conflicting local edits, and backs up changed files before
applying. It accepts Git's LF/CRLF text conversion. An already-applied checkpoint
is a no-op. It does not commit, push or alter tags. Use `--repo PATH` if the
checkout has another name or location. On Windows, use `python` for the launcher.

The full ZIP is an alternative for a fresh directory; both ZIPs contain the
`sidpulse-tracker/` prefix. Review `git diff` after applying and commit the CI fix
normally. Keep the existing published v0.2.38 release artifacts unchanged.
