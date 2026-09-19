# v0.2.30 validation evidence

- Final full regression log/JUnit: `final-ui-tests.txt/.xml` (1,468 passed).
- Final icon/control checks: `final-controls.txt/.xml` (61 passed); 1,470 unique
  cases pass across these two runs. Earlier logs retain development history.
- Independent assembly check for 22 compact players plus wrapper: `build.txt`.
- Earlier optimizer/player byte hashes: `unchanged-earlier-squeezers.json`.
- Final measured runtime: `runtime-sha256.json`; export trials used
  `export-benchmark-runtime-sha256.json`. Only UI code changed between snapshots.
- Serial fresh-process export CPU/RSS and C64 metrics: `squeezer-stress/` and
  `squeezer-examples/`, three trials for v2.0.1/v2.0.2 and one preservation trial for v1.0/v2.0.
- Matched native UI/audio/live checks with immutable v0.2.29: `native/`.
- Completed comparison off/Top 3/all drawing trials: `comparison-draw.json`.
- Shared scrollbar drawing ablation: `scrollbar-draw.json`.
- Earlier native batch: `native-before-scrollbars/`.
- Real F5 promo capture metadata: `promo-capture.json`.
- Screenshots: actual completed comparison, narrow windows, version dropdown;
  `joint-best-fixture.png` is an explicitly synthetic equal-result UI fixture.

The source song is unchanged and identified by hash in the results. It is not
bundled here. Reports describe dummy-driver, platform and analog timing limits.
Private notes and third-party reference archives are excluded.

Final display-preference revision: `show-all-tests.txt/.xml` has 61 passing cases;
`final-test-status.json` counts the unique cases across all release runs.
`show-all-final/` contains the serial matched follow-up against the initial
v0.2.30 build. `runtime-final-sha256.json` identifies the final runtime.

`promo-full-capture.json` records the complete 96-second Autumn at Five video
and audio. The earlier short preview remains documented separately.
