# Apply v0.2.37

Both ZIPs contain the `sidpulse-tracker/` directory. Use the full ZIP for a fresh
installation or the incremental ZIP over the supplied v0.2.36 full/incremental
release. Older installations should use the full ZIP in a fresh directory.
Close the tracker and preserve local edits before extracting an update.

From the directory containing the downloaded ZIP and your `sidpulse-tracker/`
folder:

```bash
sha256sum --check --ignore-missing SHA256SUMS-v0.2.37.txt &&
unzip -o sidpulse-tracker-v0.2.37-incremental.zip &&
cd sidpulse-tracker &&
python3 scripts/finish_update.py &&
./run.sh
```

Windows users can extract the incremental ZIP over the existing directory,
run `python scripts/finish_update.py` inside it, then launch `run.cmd`.
The cleanup is idempotent and only removes the legacy root documentation paths
listed in the script. No project migration or instrument refitting is required.

The fitted drums are in F4 > Choose from presets > Wavetable drums.
The full category title is `[Wavetable] Drums & Percussion`.
