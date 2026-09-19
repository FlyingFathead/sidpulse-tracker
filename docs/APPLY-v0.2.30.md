# Apply the v0.2.30 update

Close the tracker and review any local source edits before replacing files.
Download `sidpulse-tracker-v0.2.30-final-incremental.zip` and `SHA256SUMS-v0.2.30-final.txt`
into the parent of the existing `sidpulse-tracker/` directory, then run:

```bash
sha256sum --check --ignore-missing SHA256SUMS-v0.2.30-final.txt &&
unzip -o sidpulse-tracker-v0.2.30-final-incremental.zip &&
cd sidpulse-tracker &&
./run.sh
```

The incremental supports v0.2.26, all delivered v0.2.27 candidates, v0.2.28, v0.2.29 and the earlier v0.2.30 ZIP. For older
installations or a new checkout use `sidpulse-tracker-v0.2.30-final-full.zip`.
Both archives extract under `sidpulse-tracker/` and retain executable `run.sh`.
No files need deletion and there are no new dependencies. Songs and preferences
need no replacement. The console and app should display **0.2.30**.

SQUEEZER v2.0.2 and the four-version comparison are new. Inline A/D/S/R/PW
recording, centered banks and UI optimizations are retained. v1.0/v2.0/v2.0.1 and
recording display method 1 remain available. The new comparison defaults on;
turn it off in the export panel to analyze only one version.

The export panel shows all versions by default. Uncheck **Show all versions**
for Top 3; the choice is saved as `export_show_all_versions` in user config.
An explicit `false` is honored; missing or invalid values use `true`. Shared scrollbars expose overflowing lists and panels. The supplied
SP window icon is set at startup. For a matching Linux application-menu entry,
optionally run `python3 scripts/install_desktop.py` once from the tracker folder;
see [desktop icon notes](DESKTOP_ICON.md).

The final archive names distinguish this revision from the earlier v0.2.30
delivery. The application version remains 0.2.30; no remote release is published.
