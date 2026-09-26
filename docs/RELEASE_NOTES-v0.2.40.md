# v0.2.40: pattern bank controls and safer project changes

F11 shows each pattern's row count. Double-click **Rows** to open the slider
and numeric entry, or click the left/right triangles to change the length by
one row. Ctrl+F2 opens the length dialog from F2 or F11. A reduction is blocked
when it would hide populated notes, effects, automation or filter controls;
permitted changes can be undone.

F4 adds **Clear all instruments** below the individual instrument controls.
Two Cancel-default confirmations precede a verified project backup and the
undoable clear. The application displays the backup path after clearing.

Dropping a `.sidpulse` project validates it before offering to replace the
current song. With unsaved changes, the dialog offers **Save & open**, **Open
without saving**, and **Cancel**. It checks the dropped source again before
accepting it, including a failure path for unreadable or damaged files.

The octave controls now read **−1, 0, +1** left to right. Opening a project
stamped by an older app version shows a compatibility notice; future format
and unknown-field warnings remain. A version warning does not guarantee that
every feature of another version can play or export correctly.

The existing F2 selected-row preview uses **8**. This release does not change
that binding.

See [validation](VALIDATION-v0.2.40.md), [pattern editing](PATTERN_EDITING.md),
[instrument actions](INSTRUMENTS.md), and [project files](FILE_BROWSER.md).
