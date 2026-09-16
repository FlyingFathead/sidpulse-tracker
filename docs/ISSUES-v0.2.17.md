# SIDpulse Tracker v0.2.17 — startup splash New song fix

## Reproduced v0.2.16 behavior

Normal startup preloads the bundled **Autumn at five** project before displaying
the welcome dialog. In v0.2.16 the left button was labelled `OK`; dismissing the
dialog only closed it, so the demo remained loaded even though playback did not
start.

That made the left-hand action ambiguous and contradicted the intended normal
workflow: choosing not to play the demo should leave the user with a new blank
project.

## v0.2.17 behavior

The splash buttons are now:

```text
[ New song ]    [ Play demo song ]

[ ] Don't show this on startup
```

- **New song** closes the splash and calls the existing `App.new_project()` path.
  The editor is reset to a blank `Untitled` song, the project path is cleared,
  the browser draft returns to `untitled.sidpulse`, and no playback starts.
- **Escape** has the same result as New song.
- **Play demo song** keeps the already loaded bundled demo and starts/waits for
  playback exactly as before.
- The checkbox preference is still persisted for either choice.

Using the existing new-project operation avoids a second, partial reset path and
keeps browser/editor/audio state consistent with File > New.

## Regression coverage

Tests now verify that the left/default welcome action replaces an actual loaded
welcome song with `Song()` / `Untitled`, clears the path, restores the default
filename draft, and does not start playback. Existing preference and demo-play
coverage remains in place.
