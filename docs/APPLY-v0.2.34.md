# Apply v0.2.34

Close SIDpulse Tracker and keep a copy of your installation and projects.
Verify the download against `SHA256SUMS-v0.2.34.txt`.

- **Full:** extract `sidpulse-tracker-v0.2.34-full.zip` into a new folder.
- **Incremental from v0.2.33:** extract
  `sidpulse-tracker-v0.2.34-incremental.zip` into the parent of the existing
  `sidpulse-tracker` folder and allow program files to be replaced.

Both ZIPs use the same `sidpulse-tracker/` root. After extracting the incremental
ZIP, run this **inside the updated sidpulse-tracker folder**:

```bash
python scripts/finish_update.py
```

Use `python3` on Linux or `py` on Windows if that is your Python command. This
removes the obsolete root documents, including the relocated arpeggio and checkpoint guides.
The two guides now live in `docs/`, and development guidance is in the existing
`docs/ROADMAP.md`. ZIP extraction alone cannot remove old files. The cleanup
touches only those three document paths; it is safe to run again. A full ZIP
extracted into a new folder needs no cleanup.

The v0.2.33 installation plus the incremental ZIP and cleanup is verified to
produce exactly the v0.2.34 full ZIP contents.

Start with `run.sh` or `run.cmd`. No dependency changes from v0.2.33 are needed.
FFmpeg remains optional for MP3 and sample-rate conversion. **Auto-squeeze on
import** is enabled by default; turn it off in F3 to import PCM WAV without
rate conversion or FFmpeg. Existing embedded samples are not converted on load.

Projects and user settings are not included in the overlay. See
[release notes](RELEASE_NOTES-v0.2.34.md) and [PCM/audio usage](PCM_AND_AUDIO.md).
