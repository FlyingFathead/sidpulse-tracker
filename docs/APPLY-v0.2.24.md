# Apply the v0.2.24 source update

Close SIDpulse Tracker and keep a copy of your current project directory.

The incremental ZIP contains changed/new files relative to the supplied
v0.2.23 archive. Extract it into the parent of your existing `sidpulse-tracker/`
directory and allow file replacement. No file deletions are required. If you
have local source edits, review or merge the changed files first.

The full ZIP contains the complete v0.2.24 source tree. Extract it into a new
parent directory for a separate installation. Both ZIPs have the same top-level
`sidpulse-tracker/` directory. Existing launch/install instructions in README.md
still apply; this update adds no dependencies. SHA256SUMS-v0.2.24.txt accompanies
the downloads for checking the archive bytes.

The synthwave sweep demo is supplied separately from the application. Open its
`.sidpulse` file with v0.2.24; the SID and PRG are standalone full-song exports.
See AUTOMATION.md for typing row values and recording PW movements.
