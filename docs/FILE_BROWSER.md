# Shared file browser

Load, Save / Save As, Export SID and Export PRG use the same directory-list page.
There is no separate filename popup hiding the list. Native projects and the
chosen export type use their respective file filters; directories are always
shown, along with the existing optional modified-date column.

## Open and save a revision

**F9** opens Load. **F10** opens Save, including for an already named project.
**Shift+F10 / Ctrl+Shift+S** opens the same Save As browser. The File menu's Save
and **Save as .sidpulse...** commands behave the same way. Nothing is written just by opening it.

Dropping a `.sidpulse` file on the window validates its format and project data
before asking to open it. An invalid or unreadable file displays an error and
leaves the current project intact. A valid drop asks before replacing the current
project; with unsaved edits, choose **Save & open**, **Open without saving**, or
**Cancel**. Saving an unnamed project opens the Save browser first. The dropped
file is checked again when opened in case it changed while the prompt was shown.
Native saves record both a project format and the app version that wrote them.
When that version is older or newer than this build, opening shows a compatibility
notice after a successful load. Older supported formats are migrated in memory;
unfamiliar future fields are retained in native saves but cannot be promised to
work in playback/export. A file with no recorded app version cannot be assigned
to a particular release.

The current project's latest successfully opened/saved filename is prefilled.
A named project starts the browser in that project's directory, not in an old
export directory. A new, unsaved project starts with `untitled.sidpulse` in the
last browsed directory. Creating a new project clears the old name.

For Save / Save As, the filename field initially has focus, with the caret just
before the extension and **no implicit select-all**. For example:

```text
Broken_Machine_v21|.sidpulse
                Backspace, 2
Broken_Machine_v22|.sidpulse
```

Press Enter or click Save to write the new revision. After a successful Save As,
F9/F10 will offer `Broken_Machine_v22.sidpulse`, not the older name. Opening or
cancelling the browser does not rename the song's title or change its notes.
There is **no automatic filename-number increment**: the editable default is the
current filename; the user chooses the new revision name.

**Ctrl+S / Ctrl+W** remains quick-save outside the browser: a named project is
saved to its existing path; an unnamed project opens this browser. While the
Save browser is active, Ctrl+S/W or F10 submits the **visible filename draft**,
never a hidden old filename. Shift+F10 moves focus back to the name.

## Keyboard and mouse

| Focus/action | Controls |
|---|---|
| Switch focus | Tab / Shift+Tab: list, filename, directory, action, cancel |
| File list | Up/Down, PageUp/PageDown, Home/End; Enter opens the selection |
| Parent directory | Backspace while in the list, Alt+Up, or Parent button |
| Filename/directory caret | Left/Right, Home/End; Ctrl+Left/Right moves by component |
| Select part of a name | Shift+arrows or Shift+Home/End; Shift+click extends selection |
| Delete text | Backspace before caret; Delete after caret; selection is respected |
| Select/copy/cut/paste | Ctrl+A / Ctrl+C / Ctrl+X / Ctrl+V |
| Edit destination folder | Ctrl+L focuses/selects the directory field; Enter navigates |
| Finish/cancel | Enter in Filename or action button; Escape or Cancel abandons operation |

Keyboard and wheel navigation keep the selected row centered through the middle
of the listing. Near the start/end, the list clamps to its first/last entry so
there is no empty padding. Scrollbar dragging remains manual. A mouse selection
stays under the pointer for double-clicking; the next keyboard/wheel movement
resumes centered following.

Click inside a text field to position the caret. Single-clicking a file selects
its name; double-click or Enter opens it in Load mode. In Save/Export mode an
explicit file choice places its name in the editable field, not an immediate
overwrite. Enter on a directory navigates in all modes. Refresh rereads the list.
Typing while list-focused is not implicitly treated as a new name: use Tab or
click Filename first.

Directory navigation never erases an edited filename. Filenames and directories
accept Unicode text; long text scrolls horizontally to keep the caret visible.
Text arrives through SDL TEXTINPUT instead of the physical piano-key map. AltGr
characters cannot trigger save/export shortcuts while editing a text field.

Absolute paths can be typed in Filename or Directory, including drive/UNC paths
on Windows. Ctrl+L is directory editing **inside** the browser; outside it,
Ctrl+L remains Load. Entering a directory in Filename navigates there instead of
trying to save over it. A changed directory field is validated before a click
on Save/Export: failure never silently writes to the previously displayed path.

## Export

File → Export PSID or Export PRG retains the existing compile/memory checks and
editable-project-save reminder. After **Export only**, or after completing
**Save + export**, the destination is chosen in this same browser. The default
basename comes from the current project, with `.sid` or `.prg` substituted. A
new native name chosen in Save + export becomes the proposed export basename.

Exports do not replace the native project's path, mark unsaved edits as saved,
or remove comments/instruments. Unsupported/oversized exports still fail with
the existing explanation. WAV/MP3 export has its own format selector and does not save an editable project.

An existing destination always asks before a browser-initiated overwrite,
including the current native file. Cancel is the default. The existing atomic
writers preserve the previous file as `.sidpulse.bak`, `.sid.bak` or `.prg.bak`.
Cancelling overwrite returns to the same draft so it can be renamed. Cancelling
the whole browser abandons a pending save-before-export/new/quit continuation.
I/O errors keep the draft visible for correction and do not falsely report success.

The browser uses a compact layout when the viewport/zoom would hide its controls.
This affects only its presentation, not the saved zoom, song timing or audio.
