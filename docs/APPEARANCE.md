# Colours and fonts

The default Classic crimson theme uses dark text on beige, green notes inside
black wells, muted crimson slider fills, and a red scope. The bundled DejaVu Sans
Mono font is heavier by default. Fonts are rendered at the chosen size.

F12 or Settings provides Colour theme, Font size (12–28), Bold font and Font file.
Ctrl+F12 jumps to Colour theme; Shift+F12 jumps to Font size. Click theme/bold to
cycle; click a numeric/path value to enter it. Wheel scrolls settings. Classic
crimson, Charcoal crimson and High contrast are built in. Full theme/font changes
apply immediately and persist separately from musical project files.

For detailed editing, preferences.json is in:

- Linux: `${XDG_CONFIG_HOME:-~/.config}/sidpulse-tracker/preferences.json`
- Windows: `%LOCALAPPDATA%/SIDpulse/preferences.json`
- Override: `$SIDPULSE_CONFIG_HOME/preferences.json`

`config/preferences.example.json` shows the font settings and common named colour
roles. Copy/edit individual keys in your preferences.json; restart to reload
manual changes. Hex colours use #RRGGBB. Keys are case insensitive. `colors` values
override the selected theme. Invalid values fall back safely. Font file accepts a
TTF/OTF path; leave empty for the bundled font. Use a monospaced font to retain the
tracker's column alignment. Missing fonts fall back to bundled DejaVu Sans Mono.

Saving an audio buffer setting preserves appearance keys, and saving appearance
preserves audio settings. User presets live in the neighboring presets directory.
The config is machine-local; copying a project never changes another user's theme.
`file_browser_show_modified` is a boolean, true by default. F12's File timestamps
toggle changes and saves it. The browser shows each file/folder's local modified
time in a green right-hand column, hiding that column when the view is too narrow.
The built-in palette is in `sidpulse/ui/themes.py`; the logo retains original SVG
colours independently. Graph stage colours and piano-key shading are semantic
editor indicators, separate from the general theme roles in this checkpoint.

Automation uses `AUTOMATION` (#65dbc5) and `AUTOMATION_DIM` (#52766e) palette entries for A/D/S/R/PW headers and values. These support the existing color override mechanism.

`REC_ARM` (#b53242 by default) colors the armed PW recording button red. Override
it with, for example, `"colors": {"REC_ARM": "#b53242"}` in preferences.json.
This role applies across the built-in themes and resets with user preferences.
While REC PW is off, only the arm button is shown. The Record to channel choice
and recording instructions appear only after arming.

## Pattern and playback display preferences

`pattern_clipboard_buttons` defaults to true. Turn it off to hide the F2 Copy,
Paste and Paste Special buttons. Keyboard and menu actions still work.

`control_panel_visible` defaults to null (responsive): the blue filter pane
starts collapsed in narrow windows. Clicking its triangle saves an explicit true
or false across F2, playback Info and application restarts. Ctrl+Shift+F2 reveals
the pane while it has keyboard focus. Collapsing it does not disable automation.

`channel_visualizers` defaults to true. Red per-channel scopes appear below
their labels in narrow Info panels. Turning this off disables both drawing and
display-only SID scope processing; it leaves sound and the master scope intact.
The three toggles are available from Settings Menu and F12.

The bottom of Settings Menu has **Reset all settings to defaults**, with Cancel
selected in its confirmation. This clears user configuration, including custom
colours and the three display preferences above. Songs, instruments, patterns,
user presets and existing recovery files are preserved. See the
[release notes](RELEASE_NOTES-v0.2.25.md) for reset behavior and audio handling.

`keyboard_mapping` is `modern` by default, or `classic` to retain the earlier
tracker shortcuts. Select it in Settings Menu > Keyboard mapping or F12. Reset
all settings restores Modern. This preference is independent of musical data.
See [keyboard mapping](KEYBOARD_MAPPING.md) for the exact scoped differences.
