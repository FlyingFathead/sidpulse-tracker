# SIDpulse Tracker v0.2.22 validation checkpoint

Application 0.2.22; native format 6, unchanged.

- Baseline 0.2.21: 1023 passed, zero failures/errors/skips.
- Candidate 0.2.22: 1051 passed, zero failures/errors/skips.
- Seven default-buffer real-time scenarios: 168 seconds, zero missing PCM
  frames, starvation episodes or callback intervals above 1.5 blocks.
- Native PCM, conditioning and ordered SID events match from identical initial
  emulator state across eight song/model/clock combinations (4,608,000 frames).
- Alt+F12, saved detection boolean and unobtrusive lower-left warnings added.
- Linux SDL dummy results only; no Windows/physical-device/VICE/real-C64 or
  assembler-rebuild claim. No remote release has been published by this work.

See docs/VALIDATION-v0.2.22.md for methods, raw evidence, limits and commands.
