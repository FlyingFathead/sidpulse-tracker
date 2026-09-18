# SIDpulse Tracker v0.2.22 - audio isolation and diagnostics

UI stalls could delay the Python SDL callback even while its PCM queue was full,
leaving the old gap counter at zero. The audio device and render worker now run
in a separate spawned process with their own interpreter/GIL. Control commands
and display snapshots cross IPC; PCM stays in the audio process.

PCM buffering and output conditioning also avoid unnecessary per-sample Python
operations. Native SID settings, timing, scopes, audio quality, 48 kHz rate,
2048-sample default, saved overrides and two-block reserve are preserved.

Alt+F12 opens audio settings, including the saved default-on underrun detector.
Set `audio_underrun_detection` to false in machine preferences, or clear the
checkbox, to disable its live notifications. Actual PCM starvation and late
callbacks have separate reddish lower-left messages, expiring after 12 seconds.
There is no popup, focus change or playback interruption. Raw counters remain
available for diagnostics and tests.

[Validation and measurements](VALIDATION-v0.2.22.md) document the baseline,
results, test limits and reproducible commands. No driver/hardware guarantee
is inferred from the Linux SDL dummy output tests. Windows native execution
and physical audio-device checks remain required before public release claims.

The source ZIPs are reviewable local update packages; no remote release was
published by this work. Native project format remains 6. Export compilation,
C64 player binaries and runtime dependency pins are unchanged.
