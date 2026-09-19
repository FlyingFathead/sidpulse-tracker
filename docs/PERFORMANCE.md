# Performance release check

Every code release needs a matched comparison with its previous release before
packaging. Keep the baseline immutable and use the same input song, runtime,
buffer sizes, scope settings, window dimensions and CPU affinity. Run timed
trials serially without concurrent tests, profiling, exports or other CPU work.

Use `scripts/benchmark_releases.py` with the same virtual environment that runs
the tracker:

```sh
python scripts/benchmark_releases.py \
  --baseline ../baseline-release \
  --candidate . \
  --input path/to/representative-song.sidpulse \
  --out ../performance-results --repetitions 5
```

The harness uses SDL dummy video/audio and native reSIDfp. It compares a temporary
copy of the song without row automation, then measures the unmodified original
on the candidate. It checks that the supplied file's SHA-256 stays unchanged.
The benchmark copies use fixed output names beginning with `v5` for continuity
with the initial study; hashes identify the actual input. Use a fresh output
folder for each run because raw results are appended.

Default phases are audio, GUI and live. The script measures offline CPU time and
block-stage timings, unthrottled drawing cost, and a 60-Hz UI with the actual
spawned audio worker. Live measurements include separate process CPU, actual
frame rate, gaps, missing frames, late callbacks and over-budget audio blocks.
Use `--phases recording` for the recording view plus a live automated PW drag,
or `--phases scrolling` for instrument/sample browsing. Use `--phases live512`
with repeated trials to investigate small-buffer callback scheduling.
Use `--phases audio`, `--phases gui` or `--phases live` to investigate a specific
regression. Linux `/proc` and CPU-affinity support are required for live results;
use the full Linux test environment for the release gate.

To isolate the instrument/sample M/S bank controls:

```sh
python scripts/benchmark_releases.py \
  --baseline ../baseline-release --candidate . \
  --input path/to/representative-song.sidpulse \
  --out ../button-performance-results --repetitions 5 --phases buttons
```

This runs both bank pages with buttons enabled and disabled. For old versions
without a preference, it suppresses the bank button drawing method only. This is
an experimental ablation, not a setting claimed to exist in those releases.

Report medians and ranges across repeats, absolute cost as well as percentages,
and changes smaller than trial variation as inconclusive. Keep features enabled
in the main comparison. Profile a demonstrated regression in a separate run;
profiler overhead is not a timing result. Measure a fix before calling it faster.
Save raw JSONL, environment details, input hashes and a concise interpretation
with the release. Keep hardware-output and OS limitations explicit.

After renderer changes, validate displayed values, selections, mouse targets,
font/theme changes, button states and narrow layouts. After audio changes, verify
register behavior, native held-note monitoring and real worker playback. Confirm
that save/quit protection, undo and the original input song remain intact.
