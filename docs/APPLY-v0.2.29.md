# Apply the v0.2.29 update

Close the tracker and review any local source edits before replacing files.
Download `sidpulse-tracker-v0.2.29-incremental.zip` and `SHA256SUMS-v0.2.29.txt`
into the parent of the existing `sidpulse-tracker/` directory, then run:

```bash
sha256sum --check --ignore-missing SHA256SUMS-v0.2.29.txt &&
unzip -o sidpulse-tracker-v0.2.29-incremental.zip &&
cd sidpulse-tracker &&
./run.sh
```

The incremental supports v0.2.26, all delivered v0.2.27 candidates and v0.2.28. For older
installations or a new checkout use `sidpulse-tracker-v0.2.29-full.zip`.
Both archives extract under `sidpulse-tracker/` and retain executable `run.sh`.
No files need deletion and there are no new dependencies. Songs and preferences
need no replacement. The console and app should display **0.2.29**.

SQUEEZER v2.0.1 and the three-version comparison are new. Inline A/D/S/R/PW
recording, centered banks and UI optimizations are retained. v1.0/v2.0 and
recording display method 1 remain available. The new comparison defaults on;
turn it off in the export panel to analyze only one version.
