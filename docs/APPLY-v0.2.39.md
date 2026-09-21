# Install or update v0.2.39

Close SIDpulse before updating.

## Git checkout

From an existing checkout with no local source changes:

```bash
git pull --ff-only
```

Then use `./run.sh` on Linux or `run.cmd` on Windows. Project files and per-user
preferences keep their existing locations. F2 three-voice fitting defaults to
on when the new preference is absent.

## Release ZIP

Download `sidpulse-tracker-v0.2.39-full.zip` and `SHA256SUMS-v0.2.39.txt` from the
[v0.2.39 release](https://github.com/FlyingFathead/sidpulse-tracker/releases/tag/v0.2.39).
Verify and extract into a new directory:

```bash
sha256sum --check SHA256SUMS-v0.2.39.txt &&
unzip sidpulse-tracker-v0.2.39-full.zip
```

Windows users can verify the ZIP with PowerShell `Get-FileHash -Algorithm SHA256`,
then extract it. Start the launcher inside the extracted `sidpulse-tracker/`
directory. Open existing `.sidpulse` projects from their saved locations.
Keep the earlier folder if it contains projects or other files you still need.

The public release supplies a full ZIP and checksum file. The development
checkpoint updater applies only to the exact CI-fixed v0.2.38 baseline; it is
not needed for a fresh installation or a Git update.

## F2 display option

**Settings Menu > UI Settings > Fit 3 voice channels (F2)** controls the saved
preference. The control/filter column remains independently collapsible. F5
keeps its existing layout. See [pattern editing](PATTERN_EDITING.md#three-channel-fit).
