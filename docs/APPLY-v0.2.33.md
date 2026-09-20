# Apply v0.2.33

Close SIDpulse Tracker and keep a copy of your installation and projects.
Verify the download against `SHA256SUMS-v0.2.33.txt`.

- **Full:** extract `sidpulse-tracker-v0.2.33-full.zip` into a new folder.
- **Incremental from v0.2.32:** extract
  `sidpulse-tracker-v0.2.33-incremental.zip` into the parent of the existing
  `sidpulse-tracker` folder and allow program files to be replaced.

Both ZIPs use the same `sidpulse-tracker/` root. The incremental package contains
only additions and changed files; applying it to the original v0.2.32 full ZIP
is verified to produce exactly the v0.2.33 full ZIP contents.

Start with `run.sh` or `run.cmd`. No dependency changes from v0.2.32 are needed.
FFmpeg remains optional for MP3 and sample-rate conversion. **Auto-squeeze on
import** is enabled by default; turn it off in F3 to import PCM WAV without
rate conversion or FFmpeg. Existing embedded samples are not converted on load.

Projects and user settings are not included in the overlay. See
[release notes](RELEASE_NOTES-v0.2.33.md) and [PCM/audio usage](PCM_AND_AUDIO.md).
