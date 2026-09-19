# Apply the v0.2.25 source update

Close SIDpulse Tracker and keep a copy of the current project directory.

The incremental ZIP contains changed/new files relative to the delivered v0.2.24
source release. Extract it into the parent of the existing `sidpulse-tracker/`
directory and allow file replacement. No file deletions are required. Review or
merge any local source edits before overwriting them.

The full ZIP contains the complete v0.2.25 source tree and can be extracted into
a new parent directory for a separate installation. Both ZIPs have the same
top-level `sidpulse-tracker/` directory. Use the full ZIP if the starting tree
predates v0.2.24. The update adds no dependencies; existing launch/install steps
in README.md apply. SHA256SUMS-v0.2.25.txt checks both archive files.

Your existing .sidpulse projects and the v4 PW sweep demo do not need replacing.
See PATTERN_EDITING.md for copying only PW, ADSR or notes to another channel.
