# Apply v0.2.31

Close SIDpulse Tracker before updating. Keep a backup of your existing folder
and projects. Verify the package against `SHA256SUMS-v0.2.31.txt`.

- **Full:** extract `sidpulse-tracker-v0.2.31-full.zip` into a new folder.
- **Incremental from v0.2.30:** extract `sidpulse-tracker-v0.2.31-incremental.zip`
  into the parent of your existing `sidpulse-tracker` folder and allow listed
  program files to be replaced. Both archives have that same root folder.

Start with `run.sh` or `run.cmd` so the launcher installs the new NumPy
dependency in its virtual environment. For a manually managed environment,
run `python -m pip install -r requirements.txt`.

FFmpeg is optional and separately installed for MP3 and sample-rate conversion.
No settings or personal songs are included in the incremental update. The
original v0.2.30 archive plus this overlay is checked against the full archive.
See [PCM/audio usage and C64 limits](PCM_AND_AUDIO.md).
