# Releasing SIDpulse Tracker

## Release contract

Release from `main` using an annotated `vX.Y.Z` tag and these two public assets:

```text
sidpulse-tracker-vX.Y.Z-full.zip
sidpulse-tracker-vX.Y.Z-SHA256SUMS.txt
```

The full ZIP must be built from the verified Git tag and extract under
`sidpulse-tracker/`. Local incremental-update ZIPs/apply scripts are maintenance
artifacts, not public release assets.

`VERSION`, `pyproject.toml` and `sidpulse/__init__.py` must match the release
version. README filenames, CHANGELOG, docs/CHECKPOINT.md and release notes should agree
with that version. Describe export and playback features according to their current documented
limits. Compact trace-derived encoding is documented in SQUEEZER.md; its
candidate validation gates still apply.

The source tree currently has no project-wide `LICENSE`. Choosing one is an owner
decision and is separate from the release mechanics described here.

## 1. Check the checkout

From the repository root:

```bash
git status --short --branch
git remote -v
git diff --stat
git diff --cached --stat
git diff --check
git diff --cached --check
git fetch origin --tags
git rev-list --left-right --count HEAD...origin/main
```

Review every staged path before committing. Do not include `.git`, `.venv`,
`*.egg-info`, caches, autosaves, update backups, private working notes, user songs
or unrelated project files. Bundled demo projects under tracked `examples/` and
`sidpulse/assets/` are intentional.

## 2. Run the complete local validation

On Linux:

```bash
set -euo pipefail
./.venv/bin/python -m pip install -e '.[dev]'
./.venv/bin/python -m pytest -q
./.venv/bin/python -m sidpulse --headless-smoke --example
./.venv/bin/python -m sidpulse --headless-smoke --play-welcome-song
./.venv/bin/python scripts/build_command_reference.py
./.venv/bin/python scripts/build_effect_reference.py
git diff --check
```

If the generated references change, review those changes and rerun validation.
Also do a short interactive desktop check of the current release's user-facing
changes. For v0.2.40, inspect the F11 row count double-click and step arrows, a protected
shorten, the F4 clear confirmations and backup, and valid/invalid project drops.
Also check file browsing and actual audio playback.

The stable checklist lives in `docs/VALIDATION.md`.

## 3. Commit and push `main`

Stage only reviewed paths, inspect the staged diff, then commit:

```bash
git add -p
# Add each reviewed new file explicitly with git add -- its/path
git diff --cached --check
git diff --cached --name-status
git diff --cached --stat
git commit -m "Release v0.2.40"
git push origin main
```

Do not force-push.

Record the exact commit:

```bash
commit=$(git rev-parse HEAD)
printf '%s
' "$commit"
```

## 4. Verify CI for that exact commit

Using GitHub CLI:

```bash
gh run list \
  --workflow tests.yml \
  --branch main \
  --commit "$commit" \
  --event push \
  --json databaseId,headSha,status,conclusion,url
```

A missing run is not a pass. Watch the returned run ID:

```bash
gh run watch RUN_ID --exit-status
```

Confirm its `headSha` is the release commit and its conclusion is success. The
workflow currently covers Ubuntu and Windows on Python 3.10 and 3.12, including
the Windows launcher path.

## 5. Tag the verified commit

Make sure `v0.2.40` does not already point somewhere else:

```bash
git show-ref --tags --verify --quiet refs/tags/v0.2.40 && git show v0.2.40 || true
git ls-remote --tags origin refs/tags/v0.2.40
```

If no conflicting tag exists:

```bash
git tag -a v0.2.40 -m "SIDpulse Tracker v0.2.40" "$commit"
git push origin v0.2.40
```

Do not move or force-update an existing release tag. Check the tag-triggered CI
run as well.

## 6. Build assets from the tag

From the repository root:

```bash
set -euo pipefail

git archive \
  --format=zip \
  --prefix=sidpulse-tracker/ \
  --output=../sidpulse-tracker-v0.2.40-full.zip \
  v0.2.40

cd ..
sha256sum sidpulse-tracker-v0.2.40-full.zip > sidpulse-tracker-v0.2.40-SHA256SUMS.txt
sha256sum -c sidpulse-tracker-v0.2.40-SHA256SUMS.txt
```

Inspect the tagged tree and archive before publishing:

```bash
git -C sidpulse-tracker ls-tree -r --name-only v0.2.40 | less
unzip -l sidpulse-tracker-v0.2.40-full.zip | less
```

Extract the ZIP into a fresh temporary directory and verify `VERSION`, launchers,
source files, assets and examples are present. Never rebuild different bytes
under an already-published immutable release identity.

## 7. Create and review a draft release

From the directory containing the two assets:

```bash
gh release create v0.2.40 \
  sidpulse-tracker-v0.2.40-full.zip \
  sidpulse-tracker-v0.2.40-SHA256SUMS.txt \
  --verify-tag \
  --draft \
  --title "SIDpulse Tracker v0.2.40" \
  --notes-file sidpulse-tracker/docs/RELEASE_NOTES-v0.2.40.md
```

Review the draft target, notes and the two uploaded assets before publishing.
After publication, download the public assets into a clean directory and verify
the published ZIP against the published checksum.

## References

- [Git archive](https://git-scm.com/docs/git-archive)
- [GitHub CLI run list](https://cli.github.com/manual/gh_run_list)
- [GitHub CLI run watch](https://cli.github.com/manual/gh_run_watch)
- [GitHub CLI release create](https://cli.github.com/manual/gh_release_create)

These links document command behavior; they are not evidence that a particular
CI run or release has completed.
