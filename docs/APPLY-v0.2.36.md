# Apply v0.2.36

Both archives contain the `sidpulse-tracker/` directory. Use the full ZIP for
a fresh installation or the incremental ZIP over the supplied v0.2.35 snapshot.
Close the tracker and preserve local edits before extracting an update.

```bash
sha256sum --check --ignore-missing SHA256SUMS-v0.2.36.txt
unzip -o sidpulse-tracker-v0.2.36-incremental.zip
cd sidpulse-tracker
python scripts/finish_update.py
```

Windows users can extract with their archive tool and run the same Python
command inside the tracker. No source file deletions or project migrations
are required for this overlay. Existing projects and saved instrument fits
retain their settings. Resynthesize a sample to use the improved fitter.
