## UI scale hotfix

Fixes the interface getting smaller when entering F2 Pattern Editor or F5 Info.
The layout keeps the requested font size instead of shrinking the whole page
to fit extra channels. Narrow pattern views follow the selected channel;
minimum fitting is retained for very small windows and large zoom.

Audio playback, sequencing, sample fitting and C64 export code are unchanged.
Includes all v0.2.37 features and its Windows FFmpeg CI setup.

Download the full ZIP for a fresh installation. Existing v0.2.37 installations
can use the incremental ZIP. Close the tracker, extract from the parent of
`sidpulse-tracker/`, then run `python3 scripts/finish_update.py` inside it
(`python scripts/finish_update.py` on Windows).

See `docs/VALIDATION-v0.2.38.md` and `docs/PERFORMANCE-v0.2.38.md` for checks and
measurement limits. The SHA-256 file covers the attached release archive.
