# Publish v0.2.38

After applying the incremental ZIP and running `scripts/finish_update.py`,
run this inside the authenticated local checkout. It creates an annotated tag,
a full source ZIP from that tag, a checksum, and the GitHub release.
It stops on command errors and does not overwrite existing tags or releases.

```bash
(
set -euo pipefail
sid_repo="FlyingFathead/sidpulse-tracker"
sid_tag="v0.2.38"
sid_out="$(pwd)/../release-${sid_tag}"
sid_zip="sidpulse-tracker-${sid_tag}-full.zip"
sid_sums="SHA256SUMS-${sid_tag}.txt"
test "$(cat VERSION)" = "0.2.38"
git diff --check
git add -A
if ! git diff --cached --quiet; then
    git commit -m "Release v0.2.38: fix F2 and F5 UI scaling"
fi
git push origin main
git tag -a "$sid_tag" -m "SIDpulse Tracker $sid_tag"
git push origin "refs/tags/$sid_tag"
mkdir -p "$sid_out"
git archive --format=zip --prefix=sidpulse-tracker/ \
    --output="$sid_out/$sid_zip" "$sid_tag"
(
    cd "$sid_out"
    sha256sum "$sid_zip" > "$sid_sums"
)
gh release create "$sid_tag" "$sid_out/$sid_zip" "$sid_out/$sid_sums" \
    --repo "$sid_repo" --verify-tag --latest \
    --title "SIDpulse Tracker $sid_tag" \
    --notes-file docs/GITHUB_RELEASE-v0.2.38.md
gh release view "$sid_tag" --repo "$sid_repo"
)
```

Publication runs immediately. Inspect the pushed commit's GitHub Actions result
for Windows runner confirmation. No remote push or release was performed while
preparing these packages.
