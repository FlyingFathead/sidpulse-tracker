# v0.2.39 validation

Base: the v0.2.38 CI checkpoint-001 source that passed the supplied GitHub
Ubuntu/Windows matrix at commit `591f6fd`. The results below cover the local
checkpoint before publication; interactive F2 review was subsequently accepted.
The release procedure requires a successful four-job Ubuntu/Windows matrix for
the exact commit used for the release tag and ZIP. The GitHub release notes link
to that run.

## Automated checks

Full-suite result: **1722 passed in 556.66s (0:09:16)** on Linux/Python 3.12.14.
Source hashes were unchanged during the run.

Both startup smoke commands passed: `--headless-smoke --example` and
`--headless-smoke --play-welcome-song`.

Focused display/editing checks: **101 passed**, plus **34 waveform tests passed**
with fitting both on and off. Coverage includes:

- All three voices and all 17 editable fields, with the control column both
  expanded and collapsed, at 800×600, 960×540, 960×1080, 1280×900 at 200% zoom,
  and 1920×1080 at 150% zoom.
- Mouse field mapping after resize/scroll; fitted PW drag/copy/paste and undo;
  independent control-column visibility; tiny-window selected-field access.
- Menu toggle, restart persistence, missing/invalid preference defaults, and
  Reset all settings restoring the default.
- Stable page fonts and toolbar geometry; font/glyph/hit-rectangle cache reuse;
  theme/zoom updates; existing pattern-length dialog and scrollbar checks.

Eighteen baseline/candidate screenshots were pixel-identical with fitting off
across F2, F5 and Orders at six size/zoom/control combinations, normalizing only
the version title. F5 pixels also match between the new toggle's on/off states.
[Comparison hashes](../validation/v0.2.39/unchanged-views.json).

## Visual review

Rendered with pygame-ce 2.5.7 on Linux/Python 3.12.14 using SDL dummy video.
Reviewed 800×600 (control hidden and shown), 960×1080, and 1280×900 at 200% zoom.
Grid text is deliberately smaller where needed. Toolbar/header sizes remain
stable, and the control column aligns with the voice rows.

- [960×1080, three voices](../validation/v0.2.39/f2-960x1080-control-0-zoom-1.png)
- [800×600, three voices plus control](../validation/v0.2.39/f2-800x600-control-1-zoom-1.png)

At 480×360 with control expanded, the 8-pixel font floor permits two complete
voices. Selection follows the active voice; every field remains reachable.

See the [matched performance report](PERFORMANCE-v0.2.39.md). Windows validation is covered by the required GitHub matrix. Rendering timings
use SDL dummy drivers and do not measure a physical audio output device or
desktop compositor.
