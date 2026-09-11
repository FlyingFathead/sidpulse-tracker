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
