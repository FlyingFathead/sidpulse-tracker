# Apply the v0.2.27 update

Close the tracker. Keep a copy of the source directory and review any local
source edits before replacing files. Extract the incremental ZIP into the parent
of the existing `sidpulse-tracker/` directory and allow replacement.

The incremental archive updates **v0.2.26 and earlier v0.2.27 candidates**. For earlier installations or a new
checkout, use the full archive. Both extract under `sidpulse-tracker/`; no files
need deletion and there are no new dependencies. Verify both ZIPs against
`SHA256SUMS-v0.2.27.txt`.

Existing songs, PW sweep files and user preferences need no replacement. Cut
confirmation and instrument/sample M/S default to enabled. The UI display
controls are now under **Settings Menu > UI Settings**.

Both ZIPs preserve the executable bit on `run.sh`, including the overlay.
If an older extraction removed it, `chmod +x sidpulse-tracker/run.sh` repairs
that installation. The revised recorder defaults to inline display 2; choose
display 1 in UI Settings to retain the old window. Bank selection now starts
at 001 on new/load and centers independently of F2. Squeezer v2.0 is the export
default; the version dropdown also retains v1.0.
