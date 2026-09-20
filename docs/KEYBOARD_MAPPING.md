# Keyboard mapping and audition octave

Open **Esc > Settings Menu > Keyboard mapping**, or the Keyboard mapping row
in F12. Choose **Modern** or **Classic**. The choice applies immediately and is
saved in user preferences as `keyboard_mapping`; it does not modify the song.
Missing or invalid preferences use Modern, including when upgrading from an
earlier version. Reset all settings also restores Modern.

Classic preserves SIDpulse's pre-v0.2.26 tracker-style bindings. It is not a claim
that every shortcut exactly matches every historical tracker. This selector
offers two profiles; it is not an arbitrary per-key rebinding editor.

| Action / view | Modern (default) | Classic |
|---|---|---|
| Copy selected fields, F2 | Ctrl+Insert or Alt+C | Alt+C |
| Paste overwrite, F2 | Shift+Insert or Alt+O | Alt+O |
| Paste Special, F2 | Ctrl+Shift+V | Ctrl+Shift+V |
| Roll selected fields down/up, F2 | Ctrl+Shift+Insert / Ctrl+Shift+Delete | Ctrl+Insert / Ctrl+Delete |
| Raise/lower octave, F3/F4 | + / - | Keypad * / keypad /, or Alt+End / Alt+Home |
| Reset octave to 4, F3/F4 | 0 | Mouse 0 button |
| Previous / next song order, F5 Info | − / +, including keypad | − / +, including keypad |
| Mouse octave controls | +1 / 0 / -1 | +1 / 0 / -1 |

Other established bindings remain, including Alt+C/O, insert/mix paste,
Ctrl+C for center-cursor and Ctrl+Backspace for undo. The existing Ctrl+Delete
roll-up binding also remains available in Modern. Copy/paste use the internal
tracker field clipboard; this is not operating-system text clipboard exchange.

The + key works with a dedicated plus key, Shift+= and keypad plus. Minus and
zero also accept keypad equivalents. Num Lock and Caps Lock do not change these
shortcuts. Modern +/-/0 overrides apply only in Instruments and Samples. In F2,
digits retain note/parameter-entry behavior and +/- still navigate patterns.
Numeric/text dialogs receive normal text input in both profiles.

## Playback order navigation

While a song is playing, **− / +** on the Info page visits the previous/next
entry in the song order list, starting at row zero. Repeated pattern numbers
remain separate order entries. The header's triangle buttons do the same thing;
a button is disabled at its respective end, while stopped/paused, or in pattern
loop mode. Navigation does not wrap around the order list. F2 pattern navigation
and F3/F4 octave keys keep their existing meanings.

The audio worker resolves navigation at the next tracker tick using the existing
sample clock and order transition. It retains tempo, instrument memory and voices;
destination notes/effects take effect normally. The device is not reopened and
the song is not restarted. Any active automation take finishes before the jump.
Already queued audio plays first, so response includes the configured buffer
latency. Playback navigation does not edit the song or get written into exports.

## Visible octave controls

The header shows **Oct: current value [+1] [0] [-1]**, including in F2, F3 and F4.
The controls are available in both keyboard profiles. **0 resets the octave to 4**;
it does not select octave zero. Use -1 repeatedly to reach zero if needed.
The octave is clamped to 0..7 and affects subsequent keyboard audition/note entry.
Existing notes, sounding held notes and instrument definitions are not transposed.
Samples shares this octave setting; PCM/digi audition remains unimplemented.

## Button and clipboard feedback

Copy, Paste, Paste Special and octave buttons depress while the mouse is held
inside them. Release inside to activate once; drag away and release to cancel.
Focus loss, resize, changing page or a keyboard command also cancels an unfinished
press. A quick completed click retains its pressed appearance for 160 ms, without
blocking the UI or audio.

Copy/cut/paste show a 2.5-second notice at the lower right, one row above
F8: SILENCE. Keyboard shortcuts and Paste Special use the same feedback. Empty
clipboard and incompatible-field paste attempts show a message instead of a false
success notice. Feedback remains visible with the helper strip or clipboard
toolbar hidden. See [field selection and paste](PATTERN_EDITING.md).

Since v0.2.27, Ctrl+Shift+R opens channel recording inline in F4 by default.
Choose A/D/S/R/PW and a channel; 1/2/3 selects the destination, Space arms/disarms,
F5/F6 starts playback and F8 stops. Tab focuses the blue slider. Left/Right
adjusts it; Shift is coarse and Ctrl is fine. Holding an arrow during armed
playback is one take, completed on release. Escape during a gesture cancels it.
Normal F4 sliders still edit the instrument. UI Settings retains legacy window
method 1; method 2 is inline. See [recording details](AUTOMATION.md).

F2 Ctrl+C saves **Center pattern row**, also available in UI Settings. Instrument
and sample banks always center independently: first slot at the top, selected
row centered through the middle, and final slot at the bottom. New/load starts
both banks at 001; changing views preserves each bank's selection.
Ctrl+Insert remains the Modern copy shortcut.
