# Apply the v0.2.28 update

Close the tracker and review any local source edits before replacing files.
Download `sidpulse-tracker-v0.2.28-incremental.zip` and `SHA256SUMS-v0.2.28.txt`
into the parent of the existing `sidpulse-tracker/` directory, then run:

```bash
sha256sum --check --ignore-missing SHA256SUMS-v0.2.28.txt &&
unzip -o sidpulse-tracker-v0.2.28-incremental.zip &&
cd sidpulse-tracker &&
./run.sh
```

The incremental supports v0.2.26 and all delivered v0.2.27 candidates. For older
installations or a new checkout use `sidpulse-tracker-v0.2.28-full.zip`.
Both archives extract under `sidpulse-tracker/` and retain executable `run.sh`.
No files need deletion and there are no new dependencies. Songs and preferences
need no replacement. The console and app should display **0.2.28**.

The inline A/D/S/R/PW recorder, bank scrolling fixes and SQUEEZER v2.0 from the
revised build are retained. v1.0 and recording display method 1 remain available.
