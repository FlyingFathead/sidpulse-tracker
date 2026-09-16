# Pattern beat/bar display grid

F12 contains **Grid: rows per beat** and **Grid: beats per bar** near the bottom.
Use the mouse or scroll/arrow down to those entries; Enter accepts a decimal
integer, while Left/Right decrement/increment. Bounds: 1..256 rows per beat and
1..32 beats per bar. Defaults are 4 and 4, preserving the prior 4/16 appearance.

The darker beat and brighter bar rows are shared by the three voice lanes and
the filter-control lane. Bar spacing is rows_per_beat * beats_per_bar. The
phase restarts at each pattern's row zero; the grid does not infer a musical
meter, maintain phase through arbitrary pattern lengths or insert any notes.
Use whole-bar pattern lengths, or a separate pickup pattern, for aligned bars.

For the separately delivered Broken Machine v21 arrangement: speed 02, tempo
118, rows per beat 12, beats per bar 4, ordinary pattern length 48. Pattern 00
contains its eight-row source-origin pickup. Do not change speed to 06 just to
make the shading familiar. SD1 cells encode attacks on the second tick of a row.

The grid is stored with Ctrl+S in optional `editor.pattern_grid` metadata:

```json
{"pattern_grid": {"rows_per_beat": 12, "beats_per_bar": 4}}
```

It is a display setting, like zoom, and does not dirty or modify musical song
data. Explicitly save to retain a changed grid. Invalid optional values revert
to their default individually; unknown nested metadata remains preserved.
Older format-6 builds still open the project and keep this metadata, but they
continue to draw their hard-coded grid. There is no project-format bump, global
machine preference change, tempo change or MIDI time quantization in this patch.
