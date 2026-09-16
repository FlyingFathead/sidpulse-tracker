# SIDpulse Tracker v0.2.17 release checkpoint

This tree is the intended **v0.2.17 startup-splash bug-fix candidate**. The
application version is **0.2.17** and the intended public Git tag/release name is
**v0.2.17**.

## Included work

v0.2.17 is a focused correction over the published v0.2.16 tree:

- rename the startup splash's `OK` button to **New song**;
- make New song and Escape create a blank `Untitled` project via the existing
  `App.new_project()` reset path;
- keep **Play demo song** preserving and playing the bundled editable
  `Autumn at five` project;
- keep the startup opt-out preference and explicit `--play-welcome-song`
  behavior unchanged;
- add regression coverage for the blank-project result.

Native project format remains 6. Dependency pins, audio-buffer defaults,
sequencer/export behavior and the v0.2.16 file-browser work are unchanged.

## Validation required before release

Run the complete current validation from `docs/VALIDATION.md`, including:

```bash
./.venv/bin/python -m pytest -q
./.venv/bin/python -m sidpulse --headless-smoke --example
./.venv/bin/python -m sidpulse --headless-smoke --play-welcome-song
```

Also perform an interactive normal startup and verify:

1. **New song** opens a blank `Untitled` project;
2. Escape does the same;
3. **Play demo song** keeps and plays `Autumn at five`;
4. the startup checkbox still persists both states.

Do not record a passing test count here until that exact v0.2.17 candidate has
actually been validated.

## Remaining release gates

Before publishing:

1. review and commit the intended v0.2.17 tree;
2. push `main` without force;
3. verify the exact pushed commit passes the GitHub Actions matrix;
4. create and push annotated tag `v0.2.17` on that verified commit;
5. build the full source ZIP from the tag;
6. create and verify the SHA-256 checksum file;
7. publish only the reviewed tag-built release assets.

No remote CI result, release tag or GitHub release is implied by this checkpoint
until those steps have actually completed.
