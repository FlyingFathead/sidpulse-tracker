# Installing v0.2.40

For a fresh install, download the full ZIP and SHA256SUMS file from the
**v0.2.40 GitHub release**. Keep both in one directory, then run:

```bash
sha256sum -c sidpulse-tracker-v0.2.40-SHA256SUMS.txt
unzip sidpulse-tracker-v0.2.40-full.zip
cd sidpulse-tracker
./run.sh
```

See the [README](../README.md#quick-install) for Windows and Git-clone
instructions. The full ZIP extracts under `sidpulse-tracker/`.

For an existing Git checkout, preserve any personal changes first. Fetch the
official repository and check out the immutable release tag:

```bash
git fetch origin --tags
git status --short
git switch --detach v0.2.40
```

Do not copy a maintenance checkpoint ZIP on top of another version unless
its accompanying updater has verified the exact base files. Keep personal
songs and update backups outside the repository.
