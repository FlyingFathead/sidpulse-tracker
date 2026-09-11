# Autosave and crash reports

Autosave is enabled by default, with a five-minute interval. It creates
`autosave/` in the application directory, beside the launchers. The directory is
ignored by Git and omitted from full and incremental ZIPs. Updates preserve it.

Use **Settings Menu > Autosave settings**, also available at the bottom of F12:

- Autosave On/Off.
- Interval slider, 1–60 minutes; default 5.
- Folder field: click to enter another path.
- Create folder / Retry: create the chosen directory and check write access.
- OK applies and saves the settings; Cancel leaves them unchanged.

If the directory cannot be created or written, an OK warning appears. Autosave
pauses until you apply a working folder in Settings. Turning it off stops new
snapshots and recovery prompts; existing recovery files are retained.

Snapshots use timestamped `.sidpulse` files. They are independent of your normal
save: they do not overwrite it, change its filename, or remove the unsaved mark.
Only changed, unsaved projects are copied at the interval. A newly opened
project starts its own interval. Disk serialization runs in a separate worker;
the UI makes the song copy only when a snapshot is due.

Session metadata is saved atomically under `recovery/` in the preferences
folder. An OS-released session lock distinguishes an unclean exit from another
running instance. After an unclean exit, **Load autosave / Skip** offers that
session's latest snapshot, when autosave is enabled. Loading leaves the project
marked unsaved and restores its original save destination; F10 saves normally.
Recovery copies remain available through F9 after either choice. A clean exit
does not trigger recovery on the next launch.

## Reports and freezes

Each launch opens a report in the preferences folder's `logs/` directory:

- Windows: `%LOCALAPPDATA%\SIDpulse\logs\`
- Linux: `~/.config/sidpulse-tracker/logs/` (or the configured XDG location).
- With `SIDPULSE_CONFIG_HOME`: `<that directory>/logs/`.

If those locations cannot be written, reports fall back to a `SIDpulse-logs`
folder in the system temporary directory. The error message gives the actual
path. Reports include app/Python/platform versions, safe editor state, recent
key/scancode events, and exception tracebacks. Typed text from entry dialogs is
not logged. Native fatal errors use Python's fault handler. If the UI stops
responding for approximately 15 seconds, its native watchdog dumps thread stacks
repeatedly. These logs stay on the computer; they are not uploaded automatically.

A caught main-thread Python failure attempts an immediate recovery snapshot,
then displays the report and recovery paths. The Windows launcher keeps its
console open after a nonzero exit. Audio worker/callback failures also write
tracebacks and leave an audio-error message in the editor.

A forced kill, power loss or native fatal error cannot reliably run an emergency
save. Recovery then uses the last completed periodic autosave. Edits made since
that snapshot, or before the first interval, may be absent. For a frozen window,
allow about 15 seconds for the watchdog before terminating it, then keep the
latest `.log` alongside the project that reproduced the problem.

## Preferences

These fields are machine settings, not part of the song:

```json
{
  "autosave_enabled": true,
  "autosave_minutes": 5,
  "autosave_directory": ""
}
```

An empty folder setting selects the application directory's `autosave/`.
Snapshots are retained until manually removed; there is no automatic expiry.
