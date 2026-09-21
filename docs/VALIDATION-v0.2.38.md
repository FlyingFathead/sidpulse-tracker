# v0.2.38 validation

The original focused checks below missed four full-suite failures. The
[CI repair checkpoint](CI-v0.2.38-checkpoint-001.md) records their causes,
corrections and complete-suite results.

## Original hotfix checks

111 focused tests passed in 6.52 seconds (six unrelated tests deselected).

```sh
python -m pytest -q tests/test_page_zoom.py tests/test_app.py \
  tests/test_render_performance_contract.py tests/test_button_cache.py \
  tests/test_centered_lists.py tests/test_order_skip.py \
  tests/test_pattern_waveform.py -k 'not prg and not pcm and not trace and not timer'
```

The added regression checks enter F2 with the actual key handler, compare font
metrics with the requested UI size, keep font objects cached across pages and
steady frames, preserve song/zoom, and follow all three channels and all 17
editable columns. Existing resize/zoom, cursor visibility, waveform field,
mouse target, clipboard, centered list, rendering-cache and playback navigation
checks pass. An old layout test now expects the channel count available at the
requested font size, instead of requiring the smaller fitted font.

Screenshots were inspected at 1280×900 / 100% and 480×360 / 300%. Headers,
pattern values and footers remain readable; the minimum-fit fallback keeps the
small-window selection above the footer. All version sources report 0.2.38.

The renderer's page-fitting block is the only changed runtime logic. Audio,
playback, SID backend and export files are byte-identical to the v0.2.37 archive.
Matched rendering and 2048/512 playback measurements, including the modest F2
rendering cost and late callbacks, are recorded in PERFORMANCE-v0.2.38.md.

Packaging checks validate ZIP integrity, executable run.sh, checksums and exact
incremental-overlay equivalence to the full archive. The finish_update.py cleanup
runs twice successfully on the overlay. Release shell syntax passes bash -n.
Windows GitHub Actions and real audio output still require external confirmation.
