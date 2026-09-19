# SIDpulse Tracker v0.2.26

Clipboard buttons previously executed on mouse-down without ever drawing a
pressed state. They now show a depressed bevel while held, activate once on
release inside and cancel when released outside. Fast clicks get a short visible
pressed state. Copy and paste also show a temporary lower-right message above
F8: SILENCE; keyboard actions and Paste Special use the same feedback. Empty
clipboard and incompatible field selections show clear failure messages.

Settings Menu > Keyboard mapping offers Modern (default) and Classic. The choice
is saved per user and is also available from F12. Modern assigns Ctrl+Insert to
copy and Shift+Insert to paste in F2. Classic preserves the previous Ctrl+Insert
roll action. Modern can roll using Ctrl+Shift+Insert/Delete; the existing Alt+C/O
copy/paste commands work in both modes.

The header now shows Oct: current value [+1] [0] [-1], including Pattern,
Instruments and Samples views. The buttons share the clipboard buttons' press
behavior. 0 resets to the default octave 4, and +/- are bounded to 0..7. In Modern
mode, + / - / 0 keys do the same in F3/F4. F2 digits and text dialogs keep their
existing meanings. Changing the octave affects future audition/note entry and
does not alter existing notes or instrument settings.

The profile selector offers two layouts rather than arbitrary per-key rebinding.
Classic means the existing SIDpulse layout; no claim is made of exact parity
with every historical tracker. PCM sample playback remains a future feature.

Instrument-bank rows have M/S beside their activity dots, with the same visual
style as channel monitoring and the new button press feedback. Mute follows an
instrument across all three voices, including held notes and later triggers.
Solo temporarily overrides instrument mutes; turning it off restores them.
Channel mute/solo remains a separate restriction. Neither changes the song,
undo history or exports. Monitor choices persist through stop/start but clear on
new/load; deleted slots lose their monitor state. Compact F4 shows M/S for the
selected instrument. Sample M/S is disabled with an explanation because PCM/digi
playback is not implemented.

REC PW: OFF shows only the arm button. The channel choice and instructions are
hidden, including from keyboard focus, until armed. The expanded label says
Record to channel. The arm color defaults to red; `colors.REC_ARM` in user
preferences overrides it. Narrow panels wrap the expanded controls.

Preview monitoring now resolves instrument ownership in the audio worker at
actual note triggers. Restart lookahead cannot change live monitoring. There are
no export-player, dependency or musical-format changes. The native
writer stamp is 0.2.26 and retains existing compatible-file warnings/preservation.
Resetting user preferences restores Modern. The revised two-line terminal Ctrl-C
warning is included for installations that missed the v0.2.25 wording refresh.

F2 now displays ADSR reset commands as R. Typing R, A, L in PW resets all five
A/D/S/R/PW overrides at the current row/channel only when the command is complete.
R/RA prefixes remain transient and can be cancelled. R then Enter resets only PW.
The new Reset all automation button/menu action writes all five resets across
selected rows/channels, or just the current cell with no selection. Both preserve
notes, instrument numbers and FX, with one-step undo. The existing -1 per-field
encoding is retained; no additional file-format feature is required. See
[automation](AUTOMATION.md) for hold/reset differences. Hxy already supplies
vibrato in FX, so a separate VB column remains deferred.

See [keyboard mapping](KEYBOARD_MAPPING.md), [pattern editing](PATTERN_EDITING.md),
[validation](VALIDATION-v0.2.26.md) and [apply instructions](APPLY-v0.2.26.md).
