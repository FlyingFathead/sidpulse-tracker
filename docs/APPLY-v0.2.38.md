# Apply v0.2.38

Close the tracker. Put the incremental ZIP in the parent of the existing
`sidpulse-tracker/` directory. It applies over v0.2.37.

```bash
unzip -o sidpulse-tracker-v0.2.38-incremental.zip &&
cd sidpulse-tracker &&
python3 scripts/finish_update.py &&
./run.sh
```

The finisher is included and updated for v0.2.38. It only removes the same
obsolete root documentation paths; projects and settings are not migrated.
Windows: extract over the existing directory, run `python scripts/finish_update.py`,
then `run.cmd`. For a fresh installation, use the full ZIP.
