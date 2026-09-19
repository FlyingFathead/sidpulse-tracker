# SIDpulse Tracker v0.2.30

SQUEEZER v2.0.2 adds one-byte dictionary IDs for frequently reused literal blocks
and single-execution phrase calls. On the unchanged v8 arrangement it saves
1,245 bytes beyond v2.0.1 after paying for its larger player. All v1.0, v2.0 and
v2.0.1 implementations remain available and are fallback candidates. The new
algorithm is export-only and makes no changes to native playback or song data.

The export panel analyzes four versions and shows **all versions** by default.
Uncheck **Show all versions** for Top 3. The checkbox immediately saves the
Boolean `export_show_all_versions` preference, including when export is cancelled;
missing or invalid settings default to `true`. The dropdown permits every choice.
Larger results remain selectable. Each column shows size, resident RAM and
measured maximum C64 cycles, with a Use button. Metric minima and complete ties
remain highlighted. The smallest valid output is selected initially, with RAM
and measured cycles breaking ties. A current tied choice is retained. Completed
choices switch instantly, and comparison can still be disabled.

Shared vertical scrollbars appear wherever the integrated view overflows:
export, pattern grid, instrument/sample banks, instrument fields, settings, help,
menus, orders/pattern bank, files, presets and long messages/comments. Thumb drag
and track paging affect only the viewport. Selection changes resume the existing
centering/following rules; the song and filename draft remain untouched.

A prototype for exact arithmetic packets was rejected because its savings on
the best stress-song layout did not pay for the decoder. The design document
records this result and the study of GoatTracker 2.77 and the supplied explanation
of Rob Hubbard's player. Both references are acknowledged; no source code or
music data from either is incorporated into SIDpulse.

The supplied SP logo is now the window icon, loaded once at startup. A stable
Windows application identity and optional Linux desktop launcher support desktop
grouping. The README includes a short GIF preview and a complete 1:36 MP4 playthrough
with audio and all three scopes, using the bundled Autumn at Five song.
No runtime recording is enabled. The official-source notice sits directly
below the main logo.
Quick features and installation instructions sit below the preview; links to
audio-bitsqueezer and c64-3d-toolkit close the README after the acknowledgments.

The app, launchers, native save metadata and PRG credits report 0.2.30. Squeezed
PRGs also show the selected squeezer version. Native formats remain 6/7, existing
preferences are honored, and there are no new runtime dependencies.

Read [design and findings](SQUEEZER-v2.0.2.md),
[performance](PERFORMANCE-v0.2.30.md), [validation](VALIDATION-v0.2.30.md) and
[apply instructions](APPLY-v0.2.30.md). Full/incremental archives preserve
executable run.sh. No remote push, tag or publication is performed.
