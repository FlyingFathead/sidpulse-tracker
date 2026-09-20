# Push and publish v0.2.37

These commands use the maintainer's existing authenticated Git checkout and
GitHub CLI. They have been prepared and syntax-checked; no remote push, tag or
release was performed while preparing the ZIPs. The Windows CI result remains
pending until the pushed commit's Native editor checks finish successfully.

Place the full ZIP, incremental ZIP, checksum file and performance report in
the **parent directory** of the existing `sidpulse-tracker/` checkout. The
incremental base must already contain v0.2.36. For an older source tree, apply
the full ZIP instead. Close the tracker before updating.

## Apply and inspect

From that parent directory:

```bash
sha256sum --check SHA256SUMS-v0.2.37.txt &&
unzip -o sidpulse-tracker-v0.2.37-incremental.zip &&
cd sidpulse-tracker &&
python3 scripts/finish_update.py &&
git diff --check &&
git diff --stat
```

Review the changes in your checkout before committing them. Keep the downloaded
release assets in the parent directory so they do not become tracked source.

## Commit and push

Inside `sidpulse-tracker/`:

```bash
git add -A &&
git commit -m "Release v0.2.37: playback navigation and wavetable drum presets" &&
git push origin HEAD
```

## Wait for this commit's CI, then tag and publish

This block waits for the push-triggered `tests.yml` run for the current commit.
It stops on a failed CI run or command error. It creates an annotated tag,
pushes that tag, and publishes the four downloaded assets with the prepared
release body. Existing tags/releases are not overwritten.

```bash
(
  set -eu
  sidpulse_repo=FlyingFathead/sidpulse-tracker
  sidpulse_head=$(git rev-parse HEAD)
  sidpulse_run=''
  for ((sidpulse_attempt=0; sidpulse_attempt<60; sidpulse_attempt++)); do
    sidpulse_run=$(gh run list --repo "$sidpulse_repo" --workflow tests.yml \
      --commit "$sidpulse_head" --event push --limit 1 \
      --json databaseId --jq '.[0].databaseId // empty')
    if [ -n "$sidpulse_run" ]; then break; fi
    sleep 2
  done
  if [ -z "$sidpulse_run" ]; then
    echo 'No CI run appeared for this commit. Check Actions before publishing.' >&2
    exit 1
  fi
  gh run watch "$sidpulse_run" --repo "$sidpulse_repo" --exit-status
  test "$(git rev-parse HEAD)" = "$sidpulse_head"
  git tag -a v0.2.37 "$sidpulse_head" -m "SIDpulse Tracker v0.2.37"
  git push origin refs/tags/v0.2.37
  gh release create v0.2.37 \
    ../sidpulse-tracker-v0.2.37-full.zip \
    ../sidpulse-tracker-v0.2.37-incremental.zip \
    ../SHA256SUMS-v0.2.37.txt \
    ../PERFORMANCE-v0.2.37.md \
    --repo "$sidpulse_repo" --verify-tag --latest \
    --title "SIDpulse Tracker v0.2.37" \
    --notes-file docs/GITHUB_RELEASE-v0.2.37.md
)
```

The block uses GitHub CLI's [commit-filtered run listing](https://cli.github.com/manual/gh_run_list),
[CI exit status](https://cli.github.com/manual/gh_run_watch), and
[release assets / notes-file support](https://cli.github.com/manual/gh_release_create).
If the GitHub connection is unavailable in the editing workspace, perform these
steps in the authenticated maintainer checkout. Do not infer a remote release
from the existence of the local ZIPs.
