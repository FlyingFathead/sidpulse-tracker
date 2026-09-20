# Apply v0.2.35

Both ZIPs contain the common `sidpulse-tracker/` directory. Use the full ZIP for
a fresh install or the incremental ZIP over a completed v0.2.34 installation.
Close the tracker before extracting; keep any uncommitted local edits safe.

From the directory containing the ZIP and the existing tracker folder:

```bash
sha256sum --check --ignore-missing SHA256SUMS-v0.2.35.txt
unzip -o sidpulse-tracker-v0.2.35-incremental.zip
cd sidpulse-tracker
python scripts/finish_update.py
```

The cleanup removes the old root changelog; its content is now under `docs/`.
The cleanup is repeatable and only touches its listed obsolete document paths.
Projects, preferences and autosaves are not traversed. Windows users can extract
with their archive tool and run the same Python command inside the tracker.

Missing DIGI preferences use method #1. Choose method #2 in SID/PRG export if
you want the previous waveform-DAC routine. Source projects need no conversion.
Sample-to-SID synthesis remains the recommended route in the confirmation popup.
