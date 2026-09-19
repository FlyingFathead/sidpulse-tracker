# v0.2.29 release evidence

- `full-tests.txt` / `.xml`: 1,423 passing regressions; XML hostname removed.
- `final-ui.txt`: five final comparison focus/caption checks.
- `build.txt`: independent 64tass rebuild of 16 players and compact PRG loader.
- `unchanged-earlier-squeezers.json`: byte-identical older optimizer/player hashes.
- `squeezer-stress/`: isolated serial v8 compiler measurements and hashes.
- `squeezer-examples/`: isolated serial measurements for all four native examples.
- `native/`: matched UI/audio/live checks against v0.2.28 and unchanged native hashes.
- `comparison-draw.json`: completed comparison panel on/off drawing cost.
- PNGs: comparison at three sizes, dropdown and labeled equal-result fixture.

Input stress song and third-party reference source are not bundled. Environment
and raw task fields are retained without private paths or hostnames. See
`docs/PERFORMANCE-v0.2.29.md`, `docs/VALIDATION-v0.2.29.md` and
`docs/SQUEEZER-v2.0.1.md` for interpretation, source preservation and limits.
