# v0.2.27 validation evidence

- `full-tests.txt` / `full-tests.xml`: full regression run, 1235 passed.
- `final-navigation.txt` / `final-navigation.xml`: 14 passing navigation and
  renderer tests after the final sample-wheel handler, including two new bank
  mouse/wheel/keyboard integration cases.
- `smoke-example.txt` / `smoke-welcome.txt`: successful headless startup commands;
  empty logs are expected on success.
- Screenshots cover Cut/Reset confirmations, the new UI submenu, bank controls,
  one armed channel, the dedicated PW recorder, and centered-list boundaries.
- `performance/`: matched measurements, raw counters and source fingerprints.

The input-navigation test was corrected to render the initial view before
sending mouse input, as the application does, and then passed. The full suite
predates only the isolated two-line sample-wheel branch; the 14 focused tests
cover that final addition. Linux SDL dummy audio/video, native SID and spawned
worker playback were tested. Physical devices, Windows and C64 hardware were not.
