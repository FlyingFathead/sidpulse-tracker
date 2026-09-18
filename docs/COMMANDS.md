# Command / shortcut lookup table

Generated from `sidpulse/assets/commands.json`. Edit that file; restart the app to reload.

Flags are independent: `keybind_in_use` controls dispatch, `visible_in_help` controls help listing, and `visible_in_menu` controls menu listing. Both views also respect `visible`. Implementation and applicability must both be true for execution.

Disabled commands stay grey in F1. `NA` means the single-SID target does not support that feature. `--` means pending or manually disabled. A shortcut's context matters: Alt+S sets instruments in the pattern editor, while Info-page stereo switching is inapplicable.

The table inventories command groups and historical bindings. Some entries such as Arrows or the physical piano row describe a family whose argument is decoded by `keyboard.py`; JSON is never evaluated as Python. The `target` column names the semantic destination. Some IDs retain their original `future.*` names for stability even after implementation; the capability flags and target determine availability.

| ID | Context | Shortcut | Action / target | Applicable | Implemented | Binding active | Visible | Help | Menu |
|---|---|---|---|---|---|---|---|---|---|
| audio.reset_stats | global | (menu only) | Reset audio diagnostics → App.execute | true | true | false | true | true | true |
| settings.f5_restart | global | (menu only) | Restart on repeated F5: optional, off by default → App.execute | true | true | false | true | true | true |
| audio.settings | global | Alt+F12 | Audio output, test arpeggio, buffer and underrun settings → App.execute | true | true | true | true | true | true |
| playback.follow | pattern | Scroll Lock / Ctrl+F | Toggle playback tracing → App.execute | true | true | true | true | true | true |
| audio.mute.3 | global | Alt+F3 | Toggle SID voice 3 monitor mute → App.toggle_monitor | true | true | true | true | true | false |
| audio.mute.2 | global | Alt+F2 | Toggle SID voice 2 monitor mute → App.toggle_monitor | true | true | true | true | true | false |
| audio.mute.1 | global | Alt+F1 | Toggle SID voice 1 monitor mute → App.toggle_monitor | true | true | true | true | true | false |
| page.help | global | F1 | Context help → App.change_page | true | true | true | true | true | true |
| page.pattern | global | F2 | Pattern editor → App.change_page | true | true | true | true | true | true |
| page.samples | global | F3 | Sample bank → App.change_page | true | true | true | true | true | true |
| page.instrument | global | F4 | SID instrument bank → App.change_page | true | true | true | true | true | true |
| page.info | global | (menu only) | Info page → App.change_page | true | true | false | true | true | true |
| page.orders | global | F11 | Order list / pattern bank → App.change_page | true | true | true | true | true | true |
| page.settings | global | F12 | Song and SID settings → App.change_page | true | true | true | true | true | true |
| file.open | global | F9 / Ctrl+L | Open native project → App.browse | true | true | true | true | true | true |
| file.save | global | F10 | Save through the shared browser; default to the current project name → App.browse | true | true | true | true | true | true |
| file.quick_save | global | Ctrl+S / Ctrl+W | Quick-save to the current project file; browse when unsaved → App.save_project | true | true | true | true | true | false |
| file.save_as | global | Shift+F10 / Ctrl+Shift+S | Save a new revision using the shared file browser → App.browse | true | true | true | true | true | true |
| file.new | global | Ctrl+N | New project → App.new_project | true | true | true | true | true | true |
| file.quit | global | Ctrl+Q | Quit with unsaved-work check → App.confirm_discard | true | true | true | true | true | true |
| file.comments | global | Shift+F9 | Edit song comments → App.text_dialog | true | true | true | true | true | true |
| ui.escape | global | Escape | Return / main menu → App.open_menu | true | true | true | true | true | true |
| ui.fullscreen | global | Ctrl+Alt+Enter / Ctrl+Enter | Toggle fullscreen → App.execute | true | true | true | true | true | true |
| ui.zoom | global | Ctrl+Alt +/- / Ctrl+Alt+0 | Adjust/reset UI zoom → App.zoom | true | true | true | true | true | true |
| audio.stop | global | F8 | Silence SID audition → AudioEngine.send | true | true | true | true | true | true |
| editor.undo | global | Ctrl+Backspace | Undo edit → History.undo | true | true | true | true | true | true |
| editor.redo | global | Ctrl+Shift+Backspace | Redo edit → History.redo | true | true | true | true | true | true |
| future.midi | global | Shift+F1 | MIDI configuration → future.midi | true | false | false | true | true | true |
| future.system | global | Ctrl+F1 | System configuration → future.system | true | false | false | true | true | true |
| future.palette | global | Ctrl+F12 | Colour themes → settings.theme | true | true | true | true | true | true |
| future.font | global | Shift+F12 | Font settings → settings.font | true | true | true | true | true | true |
| future.samples | global | Ctrl+F3 | Sample library → future.samples | true | false | false | true | true | true |
| future.instruments | global | Ctrl+F4 | Instrument library → future.instruments | true | false | false | true | true | true |
| future.play_song | global | F5 / Ctrl+F5 | Song playback → App.start_playback | true | true | true | true | true | true |
| future.play_pattern | global | F6 | Pattern playback → App.start_playback | true | true | true | true | true | true |
| future.play_order | global | Shift+F6 | Playback from order → App.start_playback | true | true | true | true | true | true |
| future.play_cursor | global | F7 | Playback from cursor → App.start_playback | true | true | true | true | true | true |
| future.pause | global | Shift+F8 | Pause/resume → App.execute | true | true | true | true | true | true |
| future.logging | global | Ctrl+F11 | Logging view → future.logging | true | false | false | true | true | true |
| future.psid | global | Ctrl+Shift+E | Export .sid (PSID); offer native project save → App.begin_export | true | true | true | true | true | true |
| future.prg | global | (menu only) | Export runnable C64 .prg; offer native project save → App.begin_export | true | true | false | true | true | true |
| future.remap | global | (menu only) | SID remapping → future.remap | true | false | false | true | true | true |
| future.macros | global | (menu only) | Macro editor → F4 Motion / tables | true | true | false | true | true | true |
| future.programs | global | (menu only) | Instrument programs → F4 Motion / tables | true | true | false | true | true | true |
| future.pcm | global | (menu only) | PCM sample import → future.pcm | true | false | false | true | true | true |
| future.digi | global | (menu only) | Digi conversion → future.digi | true | false | false | true | true | true |
| pattern.piano | pattern, instrument | Z S X D C V G B H N J M / Q 2 W 3 E R 5 T 6 Y 7 U I 9 O 0 P | Physical piano rows; Caps Lock auditions only → Editor.enter_note / AudioEngine.send | true | true | true | true | true | true |
| pattern.cut | pattern | 1 | Note cut → Editor.enter_note | true | true | true | true | true | true |
| pattern.off | pattern | Grave / non-US hash | Note off → Editor.enter_note | true | true | true | true | true | true |
| pattern.clear | pattern | . | Clear current field → Editor.clear_field | true | true | true | true | true | true |
| pattern.mask | pattern | , | Toggle field-copy mask → Editor.edit_mask | true | true | true | true | true | true |
| pattern.digits | pattern | 0..9 / A..F | Numeric field entry / hex effect parameters → Editor.enter_digit | true | true | true | true | true | true |
| pattern.letters | pattern | A..Z | Effect letter entry → Editor.enter_digit | true | true | true | true | true | true |
| pattern.arrows | pattern | Arrows / Shift+Arrows | Arrows → Editor.move | true | true | true | true | true | true |
| pattern.page_move | pattern | PgUp/PgDn / Ctrl+Home/End | Page move → Editor.move | true | true | true | true | true | true |
| pattern.voice | pattern | Tab/Shift+Tab / Alt+Left/Right / Ctrl+Left/Right | Voice → Editor.voice | true | true | true | true | true | true |
| pattern.home_end | pattern | Home/End | Home end → Editor cursor | true | true | true | true | true | true |
| pattern.edge | pattern | Ctrl+PgUp/PgDn | Edge → Editor.row | true | true | true | true | true | true |
| pattern.pattern | pattern | +/- / Shift+keypad +/- | Pattern → Editor.select_pattern | true | true | true | true | true | true |
| pattern.order_pattern | pattern | Ctrl +/- | Order pattern → Editor.select_pattern | true | true | true | true | true | true |
| pattern.octave | global | Keypad / and * / Alt+Home/End | Octave → Editor.octave | true | true | true | true | true | true |
| pattern.instrument | global | Ctrl+Up/Down / < / > | Instrument → Editor.select_instrument | true | true | true | true | true | true |
| pattern.skip | pattern | Alt+0..9 | Skip → Editor.skip | true | true | true | true | true | true |
| pattern.repeat | pattern | Space | Repeat → Editor.repeat_field | true | true | true | true | true | true |
| pattern.pick | pattern | Enter | Pick → Editor.last_cell | true | true | true | true | true | true |
| pattern.center | pattern | Ctrl+C | Center → Editor.centered | true | true | true | true | true | true |
| pattern.highlight | pattern | Ctrl+H | Highlight → Editor.highlight | true | true | true | true | true | true |
| pattern.pattern_length | pattern | Ctrl+F2 | Pattern length → Editor pattern rows | true | true | true | true | true | true |
| pattern.snapshot | pattern | Alt+Enter | Snapshot → Editor.stored_pattern | true | true | true | true | true | true |
| pattern.restore | pattern | Alt+Backspace | Restore → Editor.edit | true | true | true | true | true | true |
| pattern.start | pattern | Alt+B | Block start → Editor.mark | true | true | true | true | true | true |
| pattern.end | pattern | Alt+E | Block end → Editor.mark | true | true | true | true | true | true |
| pattern.all | pattern | Alt+L | Select voice / whole pattern → Editor.mark | true | true | true | true | true | true |
| pattern.unmark | pattern | Alt+U | Clear selection and clipboard → Editor.mark | true | true | true | true | true | true |
| pattern.copy | pattern | Alt+C | Copy block → Editor.copy | true | true | true | true | true | true |
| pattern.cut_block | pattern | Alt+Z | Cut block → Editor.copy | true | true | true | true | true | true |
| pattern.paste_insert | pattern | Alt+P | Insert paste → Editor.paste | true | true | true | true | true | true |
| pattern.paste_overwrite | pattern | Alt+O | Overwrite paste → Editor.paste | true | true | true | true | true | true |
| pattern.paste_mix | pattern | Alt+M | Mix into empty cells → Editor.paste | true | true | true | true | true | true |
| pattern.set_instrument | pattern | Alt+S | Set selected instrument on block → Editor.block_instrument | true | true | true | true | true | true |
| pattern.transpose | pattern | Alt+Q/A / Alt+Shift+Q/A | Transpose semitone / octave → Editor.transpose | true | true | true | true | true | true |
| pattern.insert | pattern | Insert / Alt+Insert | Insert voice / whole row → Editor.insert_delete | true | true | true | true | true | true |
| pattern.delete | pattern | Delete / Alt+Delete | Delete voice / whole row → Editor.insert_delete | true | true | true | true | true | true |
| pattern.roll | pattern | Ctrl+Insert/Delete | Roll selected block → Editor.roll | true | true | true | true | true | true |
| pattern.audition_cell | pattern | 4 | Audition cell while held → AudioEngine.send | true | true | true | true | true | true |
| pattern.audition_row | pattern | 8 | Audition row while held → AudioEngine.send | true | true | true | true | true | true |
| instrument.navigation | instrument | Arrows / Tab / Enter / Insert / PgUp/PgDn: General / Motion | Bank / properties / buttons / new instrument; click yellow values to type → App.page_key | true | true | true | true | true | true |
| samples.navigation | samples | Up/Down | Select sample slot → App.sample_index | true | true | true | true | true | true |
| orders.song_loop | orders | L | Loop song when playlist ends: restart at order 000 or stop → Editor.set_song_loop | true | true | true | true | true | false |
| orders.navigation | orders | Up/Down / Enter / N / Shift+N / Insert/Delete / PgUp/PgDn / Home/End | Select and edit orders; browse all patterns, Enter opens in F2 → Editor.order_edit | true | true | true | true | true | true |
| help.navigation | help | 1..8 / Left/Right / Tab / Up/Down / PgUp/PgDn | Select help topic / scroll → App.help_topic | true | true | true | true | true | true |
| files.navigation | files | Arrows / Home/End / Enter / Tab / Shift+Tab / Ctrl+L / Alt+Up / Ctrl+A/C/X/V | Shared file browser with inline editable filename and directory → App.select_file | true | true | true | true | true | true |
| settings.navigation | settings | Arrows / Enter | Edit song / SID settings → App.change_property | true | true | true | true | true | true |
| legacy.global.001 | global | 2*F11 | Order List and Channel Volume → future.global | true | false | false | true | true | true |
| legacy.global.002 | global | { } | Decrease/Increase playback speed → future.global | true | false | false | true | true | true |
| legacy.global.003 | global | Ctrl-[ ] | Decrease/Increase playback tempo → future.global | true | false | false | true | true | true |
| legacy.global.004 | global | [ ] | Decrease/Increase global volume → future.global | true | false | false | true | true | true |
| legacy.global.005 | global | Alt-F1 -> Alt-F8 | Toggle channels 1->8 → future.global | true | false | false | true | true | true |
| legacy.global.006 | global | Ctrl-D | DOS Shell → future.global | false | false | false | true | true | true |
| legacy.global.007 | global | Ctrl-E | Refresh screen and reset cache identification → future.global | true | false | false | true | true | true |
| legacy.global.008 | global | Ctrl-G | Go to order/pattern/row given time → future.global | true | false | false | true | true | true |
| legacy.global.009 | global | Ctrl-I | Reinitialise sound driver → future.global | true | false | false | true | true | true |
| legacy.global.010 | global | Ctrl-M | Toggle mouse cursor → future.global | true | false | false | true | true | true |
| legacy.global.011 | global | Ctrl-P | Calculate approximate song length → future.global | true | false | false | true | true | true |
| legacy.global.012 | global | Ctrl-Shift-Q | Quit without confirmation → future.global | true | false | false | true | true | true |
| legacy.global.013 | global | Ctrl, Ctrl | Digraph entry: → future.global | true | false | false | true | true | true |
| legacy.pattern.014 | pattern | <x Panning slide to left by x | [$D0-$DF] → future.pattern | true | false | false | true | true | true |
| legacy.pattern.015 | pattern | >x Panning slide to right by x | [$E0-$EF] → future.pattern | true | false | false | true | true | true |
| legacy.pattern.016 | pattern | Shift-` | Note fade (~~~) → future.pattern | true | false | false | true | true | true |
| legacy.pattern.017 | pattern | Alt-Up/Down | Slide pattern up/down by 1 row → future.pattern | true | false | false | true | true | true |
| legacy.pattern.018 | pattern | Shift-A/F | Move to previous/next note/instrument/volume/effect → future.pattern | true | false | false | true | true | true |
| legacy.pattern.019 | pattern | Alt-N | Toggle Multichannel mode for current channel → future.pattern | true | false | false | true | true | true |
| legacy.pattern.020 | pattern | 2*Alt-N | Multichannel Selection menu → future.pattern | true | false | false | true | true | true |
| legacy.pattern.021 | pattern | Ctrl-V | Toggle default volume display → future.pattern | true | false | false | true | true | true |
| legacy.pattern.022 | pattern | Ctrl-O | Export current pattern to selected sample → future.pattern | true | false | false | true | true | true |
| legacy.pattern.023 | pattern | Ctrl-Shift-O | Export current pattern to unused samples by channel → future.pattern | true | false | false | true | true | true |
| legacy.pattern.024 | pattern | Ctrl-B | Bind current pattern to selected sample → future.pattern | true | false | false | true | true | true |
| legacy.pattern.025 | pattern | Ctrl-Shift-B | Bind current pattern to unused samples by channel → future.pattern | true | false | false | true | true | true |
| legacy.pattern.026 | pattern | Alt-T | Cycle current track's view → future.pattern | true | false | false | true | true | true |
| legacy.pattern.027 | pattern | Alt-R | Clear all track views → future.pattern | true | false | false | true | true | true |
| legacy.pattern.028 | pattern | Alt-H | Toggle track view divisions → future.pattern | true | false | false | true | true | true |
| legacy.pattern.029 | pattern | Ctrl-0 | Deselect current track → future.pattern | true | false | false | true | true | true |
| legacy.pattern.030 | pattern | Ctrl-1 - Ctrl-5 | View current track in scheme 1-5 → future.pattern | true | false | false | true | true | true |
| legacy.pattern.031 | pattern | Ctrl-1 - Ctrl-6 | View current track in scheme 1-6 → future.pattern | true | false | false | true | true | true |
| legacy.pattern.032 | pattern | Ctrl-Left/Right | Move left/right between track view columns → future.pattern | true | false | false | true | true | true |
| legacy.pattern.033 | pattern | Ctrl-Shift 1-6 | Quick view scheme setup → future.pattern | true | false | false | true | true | true |
| legacy.pattern.034 | pattern | Ctrl-T | Toggle View-Channel cursor-tracking → future.pattern | true | false | false | true | true | true |
| legacy.pattern.035 | pattern | Alt-D | Quick mark n/2n/4n/... lines (n=Row Hilight Major) → future.pattern | true | false | false | true | true | true |
| legacy.pattern.036 | pattern | Alt-V | Set volume/panning → future.pattern | false | false | false | true | true | true |
| legacy.pattern.037 | pattern | Alt-W | Wipe vol/pan not associated with a note/instrument → future.pattern | true | false | false | true | true | true |
| legacy.pattern.038 | pattern | Alt-K | Slide volume/panning column → future.pattern | false | false | false | true | true | true |
| legacy.pattern.039 | pattern | 2*Alt-K | Wipe all volume/panning controls → future.pattern | false | false | false | true | true | true |
| legacy.pattern.040 | pattern | Alt-J | Volume amplifier   / Fast volume attenuate → future.pattern | true | false | false | true | true | true |
| legacy.pattern.041 | pattern | Alt-Y | Swap block → future.pattern | true | false | false | true | true | true |
| legacy.pattern.042 | pattern | Alt-X | Slide effect value → future.pattern | true | false | false | true | true | true |
| legacy.pattern.043 | pattern | 2*Alt-X | Wipe all effect data → future.pattern | true | false | false | true | true | true |
| legacy.pattern.044 | pattern | Shift-L | Copy block to clipboard honoring current mute-settings → future.pattern | true | false | false | true | true | true |
| legacy.pattern.045 | pattern | 2*Alt-O | Grow pattern to clipboard length → future.pattern | true | false | false | true | true | true |
| legacy.pattern.046 | pattern | 2*Alt-M | Mix each field from clipboard with pattern data → future.pattern | true | false | false | true | true | true |
| legacy.pattern.047 | pattern | Alt-F | Double block length → future.pattern | true | false | false | true | true | true |
| legacy.pattern.048 | pattern | Alt-G | Halve block length → future.pattern | true | false | false | true | true | true |
| legacy.pattern.049 | pattern | Alt-I | Select Template mode / Fast volume amplify → future.pattern | true | false | false | true | true | true |
| legacy.pattern.050 | pattern | Ctrl-J | Toggle fast volume mode → future.pattern | true | false | false | true | true | true |
| legacy.pattern.051 | pattern | Ctrl-U | Selection volume vary / Fast volume vary → future.pattern | true | false | false | true | true | true |
| legacy.pattern.052 | pattern | Ctrl-Y | Selection panning vary / Fast panning vary → future.pattern | false | false | false | true | true | true |
| legacy.pattern.053 | pattern | Ctrl-K | Selection effect vary / Fast effect vary → future.pattern | true | false | false | true | true | true |
| legacy.pattern.054 | pattern | Ctrl-F6 | Play from current row → App.start_playback | true | true | true | true | true | true |
| legacy.pattern.055 | pattern | Ctrl-F7 | Set/Clear playback mark (for use with F7) → App.execute | true | true | true | true | true | true |
| legacy.pattern.056 | global | Alt-F9 | Toggle current channel → App.toggle_monitor | true | true | true | true | true | true |
| legacy.pattern.057 | global | Alt-F10 | Solo current channel → App.toggle_monitor | true | true | true | true | true | true |
| legacy.pattern.058 | pattern | Ctrl-Z | Change MIDI playback trigger → future.pattern | true | false | false | true | true | true |
| legacy.pattern.059 | pattern | Alt-Scroll Lock | Toggle MIDI input → future.pattern | true | false | false | true | true | true |
| legacy.samples.060 | samples | Enter | Load new sample → future.samples | true | false | false | true | true | true |
| legacy.samples.061 | samples | Tab | Move between options → future.samples | true | false | false | true | true | true |
| legacy.samples.062 | samples | PgUp/PgDn | Move up/down (when not on list) → future.samples | true | false | false | true | true | true |
| legacy.samples.063 | samples | Alt-A | Convert Signed to/from Unsigned samples → future.samples | true | false | false | true | true | true |
| legacy.samples.064 | samples | Alt-B | Pre-Loop cut sample → future.samples | true | false | false | true | true | true |
| legacy.samples.065 | samples | Alt-C | Clear Sample Name & Filename (Used in Sample Name window) → future.samples | true | false | false | true | true | true |
| legacy.samples.066 | samples | Alt-D | Delete Sample → future.samples | true | false | false | true | true | true |
| legacy.samples.067 | samples | Alt-Shift-D | Downmix stereo sample to mono → future.samples | true | false | false | true | true | true |
| legacy.samples.068 | samples | Alt-E | Resize Sample (with interpolation) → future.samples | true | false | false | true | true | true |
| legacy.samples.069 | samples | Alt-Shift-E | Resample Sample (with interpolation) → future.samples | true | false | false | true | true | true |
| legacy.samples.070 | samples | Alt-F | Resize Sample (without interpolation) → future.samples | true | false | false | true | true | true |
| legacy.samples.071 | samples | Alt-Shift-F | Resample Sample (without interpolation) → future.samples | true | false | false | true | true | true |
| legacy.samples.072 | samples | Alt-G | Reverse Sample → future.samples | true | false | false | true | true | true |
| legacy.samples.073 | samples | Alt-H | Centralise Sample → future.samples | true | false | false | true | true | true |
| legacy.samples.074 | samples | Alt-I | Invert Sample → future.samples | true | false | false | true | true | true |
| legacy.samples.075 | samples | Alt-L | Post-Loop cut sample → future.samples | true | false | false | true | true | true |
| legacy.samples.076 | samples | Alt-M | Sample amplifier → future.samples | true | false | false | true | true | true |
| legacy.samples.077 | samples | Alt-N | Toggle Multichannel playback → future.samples | true | false | false | true | true | true |
| legacy.samples.078 | samples | Alt-O | Save current sample to disk (IT Format) → future.samples | true | false | false | true | true | true |
| legacy.samples.079 | samples | Alt-P | Copy sample → future.samples | true | false | false | true | true | true |
| legacy.samples.080 | samples | Alt-Q | Toggle sample quality → future.samples | true | false | false | true | true | true |
| legacy.samples.081 | samples | Alt-R | Replace current sample in song → future.samples | true | false | false | true | true | true |
| legacy.samples.082 | samples | Alt-S | Swap sample (in song also) → future.samples | true | false | false | true | true | true |
| legacy.samples.083 | samples | Alt-T | Save current sample to disk (Export Format) → future.samples | true | false | false | true | true | true |
| legacy.samples.084 | samples | Alt-V | Crossfade sample loop → future.samples | true | false | false | true | true | true |
| legacy.samples.085 | samples | Alt-W | Save current sample to disk (RAW Format) → future.samples | true | false | false | true | true | true |
| legacy.samples.086 | samples | Alt-X | Exchange sample (only in Sample List) → future.samples | true | false | false | true | true | true |
| legacy.samples.087 | samples | Alt-Y | Text to sample data → future.samples | true | false | false | true | true | true |
| legacy.samples.088 | samples | Alt-Z | Edit/create AdLib (FM) sample → future.samples | false | false | false | true | true | true |
| legacy.samples.089 | samples | Alt-Shift-Z | Load predefined AdLib sample by MIDI patch number → future.samples | false | false | false | true | true | true |
| legacy.samples.090 | samples | Alt-Ins | Insert sample slot (updates pattern data) → future.samples | true | false | false | true | true | true |
| legacy.samples.091 | samples | Alt-Del | Remove sample slot (updates pattern data) → future.samples | true | false | false | true | true | true |
| legacy.samples.092 | samples | Alt-Up/Down | Swap sample with previous/next → future.samples | true | false | false | true | true | true |
| legacy.samples.093 | samples | Alt-F9 | Toggle current sample → future.samples | true | false | false | true | true | true |
| legacy.samples.094 | samples | Alt-F10 | Solo current sample → future.samples | true | false | false | true | true | true |
| legacy.samples.095 | samples | < > | Decrease/Increase playback channel → future.samples | true | false | false | true | true | true |
| legacy.samples.096 | samples | Alt-Grey + | Increase C-5 Frequency by 1 octave → future.samples | true | false | false | true | true | true |
| legacy.samples.097 | samples | Alt-Grey - | Decrease C-5 Frequency by 1 octave → future.samples | true | false | false | true | true | true |
| legacy.samples.098 | samples | Ctrl-Grey + | Increase C-5 Frequency by 1 semitone → future.samples | true | false | false | true | true | true |
| legacy.samples.099 | samples | Ctrl-Grey - | Decrease C-5 Frequency by 1 semitone → future.samples | true | false | false | true | true | true |
| legacy.instrument.100 | instrument | Enter | Load new instrument → future.instrument | true | false | false | true | false | true |
| legacy.instrument.101 | instrument | Ctrl-PgUp/PgDn | Move instrument up/down (when not on list) → future.instrument | true | false | false | true | true | true |
| legacy.instrument.102 | instrument | Alt-C | Clear instrument name & filename → future.instrument | true | false | false | true | true | true |
| legacy.instrument.103 | instrument | Alt-W | Wipe instrument data → future.instrument | true | false | false | true | true | true |
| legacy.instrument.104 | instrument | Spacebar | Edit instrument name (ESC to exit) → future.instrument | true | false | false | true | true | true |
| legacy.instrument.105 | instrument | Alt-D | Delete instrument & all related samples → future.instrument | true | false | false | true | true | true |
| legacy.instrument.106 | instrument | Alt-Shift-D | Delete instrument & all related unused samples → future.instrument | true | false | false | true | true | true |
| legacy.instrument.107 | instrument | Alt-L | Post-Loop cut envelope → future.instrument | true | false | false | true | true | true |
| legacy.instrument.108 | instrument | Alt-N | Toggle Multichannel playback → future.instrument | true | false | false | true | true | true |
| legacy.instrument.109 | instrument | Alt-O | Save current instrument to disk (IT Format) → future.instrument | true | false | false | true | true | true |
| legacy.instrument.110 | instrument | Alt-P | Copy instrument → future.instrument | true | false | false | true | true | true |
| legacy.instrument.111 | instrument | Alt-R | Replace current instrument in song → future.instrument | true | false | false | true | true | true |
| legacy.instrument.112 | instrument | Alt-S | Swap instruments (in song also) → future.instrument | true | false | false | true | true | true |
| legacy.instrument.113 | instrument | Alt-T | Save current instrument to disk (Export Format) → future.instrument | true | false | false | true | true | true |
| legacy.instrument.114 | instrument | Alt-U | Update pattern data → future.instrument | true | false | false | true | true | true |
| legacy.instrument.115 | instrument | Alt-X | Exchange instruments (only in Instrument List) → future.instrument | true | false | false | true | true | true |
| legacy.instrument.116 | instrument | Alt-Ins | Insert instrument slot (updates pattern data) → future.instrument | true | false | false | true | true | true |
| legacy.instrument.117 | instrument | Alt-Del | Remove instrument slot (updates pattern data) → future.instrument | true | false | false | true | true | true |
| legacy.instrument.118 | instrument | < > | Decrease/Increase playback channel → future.instrument | true | false | false | true | true | true |
| legacy.instrument.note_map.119 | instrument.note_map | Enter | Pickup sample number & default play note → future.instrument.note_map | true | false | false | true | true | true |
| legacy.instrument.note_map.120 | instrument.note_map | < > | Decrease/Increase sample number → future.instrument.note_map | true | false | false | true | true | true |
| legacy.instrument.note_map.121 | instrument.note_map | Alt-A | Change all samples → future.instrument.note_map | true | false | false | true | true | true |
| legacy.instrument.note_map.122 | instrument.note_map | Alt-N | Enter next note → future.instrument.note_map | true | false | false | true | true | true |
| legacy.instrument.note_map.123 | instrument.note_map | Alt-P | Enter previous note → future.instrument.note_map | true | false | false | true | true | true |
| legacy.instrument.note_map.124 | instrument.note_map | Alt-Up/Down | Transpose all notes a semitone up/down → future.instrument.note_map | true | false | false | true | true | true |
| legacy.instrument.note_map.125 | instrument.note_map | Alt-Ins/Del | Insert/Delete a row from the table → future.instrument.note_map | true | false | false | true | true | true |
| legacy.instrument.envelope.126 | instrument.envelope | Enter | Pick up/Drop current node → future.instrument.envelope | true | false | false | true | true | true |
| legacy.instrument.envelope.127 | instrument.envelope | Insert | Add node → future.instrument.envelope | true | false | false | true | true | true |
| legacy.instrument.envelope.128 | instrument.envelope | Delete | Delete node → future.instrument.envelope | true | false | false | true | true | true |
| legacy.instrument.envelope.129 | instrument.envelope | Alt-Arrow Keys | Move node (fast) → future.instrument.envelope | true | false | false | true | true | true |
| legacy.instrument.envelope.130 | instrument.envelope | Alt-B | Pre-Loop cut envelope → future.instrument.envelope | true | false | false | true | true | true |
| legacy.instrument.envelope.131 | instrument.envelope | Alt-F | Double envelope length → future.instrument.envelope | true | false | false | true | true | true |
| legacy.instrument.envelope.132 | instrument.envelope | Alt-G | Halve envelope length → future.instrument.envelope | true | false | false | true | true | true |
| legacy.instrument.envelope.133 | instrument.envelope | Alt-E | Resize envelope → future.instrument.envelope | true | false | false | true | true | true |
| legacy.instrument.envelope.134 | instrument.envelope | Alt-Z | Generate envelope from ADSR values → future.instrument.envelope | true | false | false | true | true | true |
| legacy.instrument.envelope.135 | instrument.envelope | Press Spacebar | Play default note → future.instrument.envelope | true | false | false | true | true | true |
| legacy.instrument.envelope.136 | instrument.envelope | Release Space | Note off command → future.instrument.envelope | true | false | false | true | true | true |
| legacy.orders.137 | orders | N | Insert next pattern → future.orders | true | false | false | true | false | true |
| legacy.orders.138 | orders | Shift-N | Copy current pattern to new pattern, and insert order → future.orders | true | false | false | true | false | true |
| legacy.orders.139 | orders | - | End of song mark → future.orders | true | false | false | true | true | true |
| legacy.orders.140 | orders | + | Skip to next Order mark → future.orders | true | false | false | true | true | true |
| legacy.orders.141 | orders | Tab/Shift-Tab | Switch order list / pattern bank → App.page_key | true | true | true | true | true | true |
| legacy.orders.142 | orders | Ctrl-F7 | Play this Order next → future.orders | true | false | false | true | true | true |
| legacy.orders.143 | orders | Alt-F11 | Lock/unlock order list → future.orders | true | false | false | true | true | true |
| legacy.orders.144 | orders | Alt-R | Sort order list → future.orders | true | false | false | true | true | true |
| legacy.orders.145 | orders | Alt-U | Search for unused patterns → future.orders | true | false | false | true | true | true |
| legacy.orders.146 | orders | Ctrl-B | Link (diskwriter) this pattern to the current sample → future.orders | true | false | false | true | true | true |
| legacy.orders.147 | orders | Ctrl-O | Copy (diskwriter) this pattern to the current sample → future.orders | true | false | false | true | true | true |
| legacy.orders.148 | orders | C | Continue to next position of current pattern → future.orders | true | false | false | true | true | true |
| legacy.orders.149 | orders | Alt-Enter | Save order list → future.orders | true | false | false | true | true | true |
| legacy.orders.150 | orders | Alt-Backspace | Swap order list with saved order list → future.orders | true | false | false | true | true | true |
| legacy.info.151 | info | Insert | Add a new window → future.info | true | false | false | true | true | true |
| legacy.info.152 | info | Delete | Delete current window → future.info | true | false | false | true | true | true |
| legacy.info.153 | info | Tab/Shift-Tab | Move between windows → future.info | true | false | false | true | true | true |
| legacy.info.154 | info | PgUp/PgDn | Change window type → future.info | true | false | false | true | true | true |
| legacy.info.155 | info | Alt-Up/Down | Move window base up/down → future.info | true | false | false | true | true | true |
| legacy.info.156 | info | I | Toggle between sample/instrument names → future.info | true | false | false | true | true | true |
| legacy.info.157 | info | Q | Mute/Unmute current channel → App.toggle_monitor | true | true | true | true | true | true |
| legacy.info.158 | info | S | Solo current channel → App.toggle_monitor | true | true | true | true | true | true |
| legacy.info.159 | info | Grey +, Grey - | Move forwards/backwards one pattern in song → future.info | true | false | false | true | true | true |
| legacy.info.160 | info | Alt-S | Toggle Stereo playback → future.info | false | false | false | true | true | true |
| legacy.info.161 | info | Alt-R | Reverse output channels → future.info | false | false | false | true | true | true |
| legacy.info.162 | info | G | Goto pattern currently playing → future.info | true | false | false | true | true | true |
| ui.helper | global | (menu only) | Toggle bottom context helper → App.helper_strip | true | true | false | true | true | true |
| pattern.control_focus | global | Ctrl+Shift+F2 | Toggle CTRL CH / FILTER row editor → App.edit_control | true | true | true | true | true | true |
| app.about | global | (menu only) | About SIDpulse Tracker / vector logo → App about dialog | true | true | false | true | true | true |

Schism reference: https://github.com/schismtracker/schismtracker/tree/84d2c46c1d3b5660edbc3eca259bf1219e59623e/helptext
