# SIDpulse Tracker v0.2.29

SQUEEZER v2.0.1 adds shared packet sequences, counted repeats and common suffixes.
It includes the larger decoder's full code/state cost before choosing an export.
Original v1.0 and v2.0 remain available, and all their candidate layouts remain
fallbacks. See [design and findings](SQUEEZER-v2.0.1.md).

The export panel now compares all three versions by default. Columns show file
bytes, resident RAM and measured maximum C64 music-routine cycles, each with a
Use Squeezer button. Minimum values are highlighted. The smallest valid output
is selected initially; RAM and cycles break size ties. Complete ties mark every
leader Joint best and preserve the current choice if tied, otherwise choosing
the newer tied version. Unmeasured CPU is a dash, never zero.

Completed version changes are immediate. One cancellable worker shares recorded
playback, candidates and verification across versions. Turning Compare all three
versions off analyzes only the selected version. The Boolean preference is saved
when continuing with export; Cancel preserves previous settings. It affects no
song data or native preview work.

The application, launchers, native save metadata and squeezed PRG credits report
0.2.29. PRG credits also show the selected squeezer version within the original
loader allocation. Native formats remain 6/7. No new runtime dependencies.

The new decoder trades some C64 playback work for reduced resident RAM; use the
comparison when CPU headroom matters. [Performance](PERFORMANCE-v0.2.29.md) and
[validation](VALIDATION-v0.2.29.md) document the results and limits. All previous
inline recording, clipboard, bank scrolling, M/S, scopes and reset safeguards are
retained. [Full and incremental downloads](APPLY-v0.2.29.md) preserve executable
run.sh. Nothing was pushed or published remotely.
