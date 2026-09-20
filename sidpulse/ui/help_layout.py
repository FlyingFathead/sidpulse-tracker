"""Structured tracker help: category, key/control column, explanation column."""
import textwrap

GUIDE = [
    ('PAGES / FILES', [
        ('F2 / F3 / F4', 'Patterns / Sample bank / SID instruments'),
        ('F11 / F12', 'Order list / Song and SID settings'),
        ('Click song / instrument header', 'Open F12 with Song title highlighted / Open that instrument in F4.'),
        ('F9 / Ctrl+L', 'Open an editable .sidpulse project'),
        ('F10 / Ctrl+W', 'Save project, including instruments and song notes'),
        ('Shift+F10', 'Save project as a new file'),
        ('Ctrl+N', 'New project; asks before discarding changes'),
        ('File > Clear pattern data', 'Clear all notes, effects and filter rows; keep instruments and arrangement. Undo is available.'),
        ('File > Clear instruments', 'Empty the bank; keep pattern data. Empty instrument slots are silent. Undo is available.'),
        ('Ctrl+Shift+E', 'Export PSID; offers an editable project save first'),
        ('Shift+F9', 'Song notes. Shift+Enter adds a line; Enter saves the text.'),
        ('Ctrl+Q / Window close', 'Confirm quitting; Cancel is selected first.'),
        ('Settings > Keyboard mapping', 'Modern is the default. Choose Classic to keep the earlier SIDpulse shortcut layout; saved per user.'),
        ('Settings > Reset all settings', 'Restore user preferences after confirmation. Cancel is selected first. Song, presets and recovery files are kept.'),
    ]),
    ('NOTE KEYS', [
        ('NOTE name / octave digit', 'Name: full piano range. Octave: type 0..7; keep the pitch class and other fields.'),
        ('Caps Lock', 'Audition piano keys from any voice field without writing, including the octave slot.'),
        ('Z S X D C V G B H N J M', 'Lower piano row: C through B'),
        ('Q 2 W 3 E R 5 T 6 Y 7 U', 'Upper piano row: C through B, one octave higher'),
        ('I 9 O 0 P', 'Continue the upper piano row into the next octave'),
        ('Physical key positions', 'Use Schism QWERTY positions, including on Finnish keyboard layouts.'),
        ('1 / Key above Tab', 'In NOTE name: cut / release note; the octave slot uses 1 as an octave digit.'),
        ('. / Space', 'Clear current field / Reuse the previous field'),
        ('Caps Lock / F8', 'Audition without writing pattern data / Silence'),
        ('4 / 8', 'In NOTE name: audition current cell / row. In the octave slot: numeric entry.'),
    ]),
    ('NAVIGATION', [
        ('Arrows', 'Move between cells and rows'),
        ('Tab / Shift+Tab', 'Next / Previous voice'),
        ('Home / End', 'Move to the start/end of the field, voice and pattern in stages'),
        ('PageUp / PageDown', 'Move 16 rows'),
        ('Ctrl+PageUp / PageDown', 'First / Last row'),
        ('Keypad / and *', 'Lower / Raise octave'),
        ('Alt+Home / End', 'Lower / Raise octave'),
        ('Oct: value [+1] [0] [-1]', 'Mouse octave controls work in both modes. 0 resets to octave 4; range is 0..7.'),
        ('F3/F4 + / - / 0 (Modern)', 'Raise/lower audition octave or reset to 4. Pattern digits and text dialogs keep their usual meaning.'),
        ('Ctrl+Up / Down', 'Previous / Next instrument'),
        ('+ / -', 'Next / Previous pattern'),
        ('Shift+keypad + / -', 'Move four patterns'),
        ('Ctrl + / -', 'Change the pattern used by the current order'),
        ('Alt+0..9', 'Set row skip'),
        ('Enter / Comma', 'Pick defaults from the current cell / Toggle the edit mask'),
    ]),
    ('EDITING', [
        ('Insert / Delete', 'Insert / Delete a row in the current voice'),
        ('Alt+Insert / Delete', 'Insert / Delete a row across all three voices'),
        ('Ctrl+Backspace', 'Undo'),
        ('Ctrl+Shift+Backspace', 'Redo'),
        ('W column', '1/T triangle, 2/S saw, 3/P pulse, 4/N noise; 0/R instrument/table, . hold. Persists across notes; does not edit the instrument or affect PCM.'),
        ('FX Z10 / Z11 / Z1F', 'Sync off / on / instrument default. Persists on this channel; no gate restart.'),
        ('FX Z20 / Z21 / Z2F', 'Ring modulation off / on / instrument default. Needs triangle and a running source oscillator (CH3 to CH1, CH1 to CH2, CH2 to CH3).'),
        ('AR column / channel Arp button', '0 OFF, 1 ON, R instrument, . hold. Persists per channel; OFF also suppresses Jxy. Existing FX commands keep their meaning.'),
    ]),
    ('MONITOR', [
        ('Alt+F1 / F2 / F3', 'Mute SID voice 1 / 2 / 3'),
        ('Alt+F9 / Alt+F10', 'Mute / Solo the current voice'),
        ('M / S buttons', 'Mute / Solo. Switching solo off restores the previous mute selection.'),
        ('F4 bank M / S', 'Mute/solo that instrument across all voices, beside its activity dot. Preview only; channel monitoring still applies. New/load clears instrument monitoring.'),
        ('F3 sample M / S', 'Use the assigned instrument mute/solo controls for PCM.'),
        ('Voice waveform displays', 'Each display shows its own native SID voice before the shared filter. Narrow Info panels put the waveform below the labels.'),
        ('F12 > Channel visualizers', 'Show/hide all three voice scopes. Off stops their display-only SID processing; audio and the master meter stay active.'),
    ]),
    ('BLOCKS', [
        ('Alt+B / Alt+E', 'Mark a whole-voice block beginning / end; includes all fields'),
        ('Drag / Shift+arrows', 'Select individual fields over rows; NOTE, FX and PW are complete values'),
        ('Click NOTE / A / PW header', 'Select that field across the pattern'),
        ('Alt+L', 'Select whole voice; repeat for the whole pattern'),
        ('Select all button', 'Select every row and all three channels in this pattern; no song data changes.'),
        ('Alt+C / Alt+Z', 'Copy / Cut selection'),
        ('Alt+P / Alt+O / Alt+M', 'Insert / Overwrite / Mix the copied fields; PW pastes into PW on the destination channel'),
        ('Ctrl+Shift+V / Paste Special', 'Notes only / Automation only / Both, limited to the copied fields'),
        ('R in A/D/S/R', 'Restore this parameter from the playing instrument. A dot keeps the running value.'),
        ('RAL in PW', 'Type R, A, L to reset all five A/D/S/R/PW overrides at this row/channel. R then Enter resets only PW. Esc cancels incomplete input.'),
        ('Reset all automation button', 'Write all five reset commands at the current cell or across selected rows/channels. Notes, instruments and FX remain; one Undo restores everything.'),
        ('Copy / Paste buttons', 'Same clipboard as Alt+C / Alt+O. Hide under F12 > Clipboard buttons.'),
        ('Ctrl+Insert / Shift+Insert (Modern)', 'Copy / Paste overwrite, using only copied fields. Notices appear above F8: SILENCE.'),
        ('Alt+U', 'Clear selection and clipboard'),
        ('Alt+Q / Alt+A', 'Transpose up / Down a semitone. Add Shift for an octave.'),
        ('Alt+S', 'Set the instrument across the selection'),
        ('Ctrl+Insert / Delete (Classic)', 'Roll the selected block down/up'),
        ('Ctrl+Shift+Insert / Delete (Modern)', 'Roll selected fields down/up. Ctrl+Delete also retains roll-up.'),
        ('Alt+Enter / Backspace', 'Store / Restore a pattern snapshot'),
    ]),
    ('RECOVERY', [
        ('Settings > Autosave', 'On/Off, interval and writable folder. Default: On, every 5 minutes.'),
        ('Autosave copies', 'Stored separately in autosave/. The original project stays unsaved until F10.'),
        ('After an unclean exit', 'Offer the previous session’s latest autosave when autosave is enabled.'),
        ('Crash reports', 'Kept in the preferences folder under logs/. A frozen interface dumps stacks after 15 seconds.'),
    ]),
    ('DISPLAY', [
        ('Ctrl+Alt + / -', 'Zoom in / Out'),
        ('Ctrl+Alt+0', 'Reset zoom'),
        ('Ctrl+Enter', 'Toggle fullscreen'),
        ('Ctrl+C / Ctrl+H', 'Center cursor / Toggle row highlighting'),
        ('Ctrl+F2', 'Length 1–256: slider / click three-digit field'),
        ('Ctrl+F12 / Shift+F12', 'Colour themes / Font settings'),
        ('F12 > File timestamps', 'Show or hide modification dates in the file browser; enabled by default.'),
        ('Filter-column triangle', 'Expand/collapse CTRL CH / FILTER in pattern and Info views. Narrow defaults favor three voices.'),
        ('preferences.json', 'Edit colours, font, file_browser_show_modified and pattern_clipboard_buttons. control_panel_visible saves the filter-column choice.'),
    ]),
    ('FILTER ROWS', [
        ('Ctrl+Shift+F2', 'Focus CTRL CH / FILTER'),
        ('Arrows / Enter / Delete', 'Choose a filter row / Edit it / Clear it'),
        ('Tab', 'Return to the voice columns'),
        ('Shared SID filter', 'Cutoff, resonance, routing, mode, master volume and signed cutoff sweep per tick.'),
    ]),
    ('INSTRUMENTS', [
        ('F4 / Up / Down', 'Open the instrument bank / Choose a slot'),
        ('Slots 01..99', 'Empty slots remain browsable. Enter opens the preset/manual chooser.'),
        ('Add / Delete buttons', 'Add an instrument / Confirm deletion. Cancel is selected first.'),
        ('Tab / Arrows / Enter', 'Move focus between bank, buttons and parameters; activate a focused button.'),
        ('QWERTY note keys', 'Audition while adjusting parameters. Typing never opens manual parameter entry.'),
        ('Click yellow value', 'Open manual numeric or text entry. This is the only parameter-typing trigger.'),
        ('Drag slider', 'Adjust the parameter directly; no entry dialog'),
        ('REC PW: OFF / ARMED', 'Arm to reveal Record to channel. Play, then drag Pulse width to write PW pattern rows. Off edits the instrument normally.'),
        ('Recording arm color', 'Red by default. Set colors.REC_ARM in preferences.json to override it.'),
        ('Instrument-bank dots', 'Flash on real note triggers; lit while gated. Playback and keyboard audition, not selection.'),
        ('Sample-bank dots', 'Sample and instrument slots remain separate. F3 shows PCM waveforms.'),
        ('General / ADSR', 'Schematic control graph: A00 is drawn vertically but means the fastest SID attack (~2 ms), not zero time.'),
        ('General / ADSR values', 'SID values are hexadecimal; Motion values are decimal.'),
        ('Arp / pitch', 'Draw steps with the mouse; 16-step pages, pitch range and sequence length controls.'),
        ('Motion On/Off buttons', 'Bypass arpeggio, wave/pitch programs, pulse motion, vibrato, gate-off and retrigger; keep their settings.'),
        ('Copy / Paste instrument', 'Copy the complete definition and assigned sample. Paste into the selected slot; occupied slots ask first. One Undo restores it.'),
        ('Choose from presets', 'Built-in categories and user presets; choosing adds an independent editable copy.'),
        ('Save user preset', 'Save the selected instrument to your user preset bank'),
        ('Preset chooser Left/Right', 'Switch Presets / Manual. Click a yellow field to type draft values.'),
    ]),
    ('ORDERS', [
        ('F11 / Tab', 'Open orders and pattern bank / Switch panels'),
        ('L / bottom loop button', 'ON restarts the song at order 000; OFF stops at playlist end. Same saved flag as F12.'),
        ('Up/Down / PgUp/PgDn', 'Choose an order or a pattern; Home/End jumps to the ends.'),
        ('Order number column', 'Click and type 3 decimal digits: apply and move to the next row.'),
        ('Delete / Insert', 'Remove an order and shift later entries up / Insert an order'),
        ('Pattern bank Enter', 'Open the selected pattern in F2, including unused patterns'),
        ('N / Shift+N', 'New pattern and order / Duplicate pattern and insert order'),
    ]),
    ('TRANSPORT', [
        ('F5', 'Start song / Show Info if already playing. Repeated-F5 restart is off by default.'),
        ('Ctrl+F5', 'Always restart the song from the beginning'),
        ('F12 > Restart on repeated F5', 'Enable repeated-F5 restart; this preference is saved for this computer.'),
        ('F6 / Shift+F6', 'Loop pattern / Play song from the current order'),
        ('F7 / Ctrl+F7', 'Play from mark or current row / Set or clear the playback mark'),
        ('Ctrl+F6', 'Loop pattern from the current row'),
        ('F8 / Shift+F8', 'Stop / Pause or resume'),
        ('F2', 'Edit patterns while playback continues'),
        ('Scroll Lock / Ctrl+F', 'Toggle following playback in the pattern editor'),
    ]),
    ('SAMPLES', [
        ('F3', 'Separate PCM/digi sample bank; Sample 01 and Instrument 01 can coexist.'),
        ('Synthesize audio', 'F3 fits a marked sample to SID waveform/pitch tables; audition and choose an instrument slot.'),
        ('Freeze / Unfreeze', 'F4 protects instrument settings. Generated instruments start frozen and keep source information; pattern automation still works.'),
        ('Normalize / Adjust volume', 'F3 edits the marked range with confirmation, original restoration and undo. Volume starts at 100%, up to 200%.'),
        ('PCM import / Digi playback', 'F3 imports and auto-squeezes samples by default; F4 PCM assigns overrides. Originals are embedded for Restore.'),
        ('DIGI method (SID/PRG export)', '#1 (default): packed volume digis, display enabled. #2: waveform DAC, display/sprites blanked. Click the method row or press Space; the choice is saved.'),
    ]),
    ('AUDIO', [
        ('F12', 'Select 6581/8580, PAL/NTSC and the shared filter'),
        ('Alt+F12', 'Audio output, test arpeggio, buffer and underrun detection settings.'),
        ('Output device', 'Choose System default or an SDL output; OK saves its name per machine.'),
        ('Test arpeggio', 'Preview the selected output without saving; song playback resumes afterwards.'),
        ('Refresh outputs', 'Update the device list after connecting audio hardware.'),
        ('Reset defaults', 'Stage System default, 2048 samples and detection ON. OK saves; Cancel discards.'),
        ('Audio buffer', 'Choose buffer size with a slider. 2048 samples is the default.'),
        ('Buffer milliseconds', 'Duration of one block. Queued blocks and the device add to total latency.'),
        ('Audio gaps', 'Cumulative PCM starvation episodes during playback/audition; excludes startup, pauses and idle silence.'),
        ('Late wakes', 'Worker scheduling delays longer than one buffer'),
        ('Render load / Peak', 'PCM generation and conditioning time divided by block duration; not whole-PC CPU usage.'),
        ('Over budget', 'Blocks that took longer to generate than their playback duration'),
        ('Reset audio counters', 'Reset diagnostic totals from the Settings menu'),
        ('Audio device errors', 'Reported in the status area. Editing and saving remain available.'),
        ('Diagnostics limitation', 'These counters cannot detect every driver or hardware dropout.'),
    ]),
]

TOPICS = {
    1: ('NOTE KEYS','NAVIGATION','EDITING','BLOCKS','MONITOR','TRANSPORT','FILTER ROWS'),
    2: ('INSTRUMENTS',), 3: ('SAMPLES',), 4: ('PAGES / FILES','ORDERS','RECOVERY'),
    5: ('AUDIO',), 6: ('DISPLAY',),
}


def groups(topic):
    if topic == 7:
        from sidpulse.ui.registry import help_entries, available
        result = {}
        for entry in help_entries():
            if not entry['shortcuts']:
                continue
            category = 'SHORTCUTS / ' + ' / '.join(entry['contexts']).upper()
            label = ' / '.join(entry['shortcuts'])
            status = '' if available(entry,keyboard=True) else '[inactive] ' if entry['applicable'] else '[not applicable] '
            result.setdefault(category,[]).append((label,status+entry['description']))
        return list(result.items())
    if topic == 8:
        from sidpulse.ui.effects import visible_effects, STATUS
        return [('EFFECTS', [(entry['code']+' / '+STATUS[entry['status']],
                 entry['description']+'. '+entry['reason']) for entry in visible_effects()])]
    names = TOPICS.get(topic)
    return [(title,rows) for title,rows in GUIDE if names is None or title in names]


def layout(topic, key_width, description_width):
    """Rows remain independently scrollable, with aligned wrapped continuations."""
    result = []
    for title, entries in groups(topic):
        if result:result.append(('space','',''))
        result.extend([('rule','',''),('heading',title,''),('rule','','')])
        for key,description in entries:
            keys = textwrap.wrap(key,key_width,break_long_words=True,break_on_hyphens=False) or ['']
            explanations = textwrap.wrap(description,description_width,break_long_words=True,break_on_hyphens=False) or ['']
            for i in range(max(len(keys),len(explanations))):
                result.append(('entry',keys[i] if i<len(keys) else '',explanations[i] if i<len(explanations) else ''))
    return result
