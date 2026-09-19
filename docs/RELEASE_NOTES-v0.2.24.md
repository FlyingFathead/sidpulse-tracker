# SIDpulse Tracker v0.2.24

F2 now has `NOTE IN EX FX A D S R PW` on each channel. The new teal fields control
the sounding SID voice without changing its instrument preset or using another
oscillator. PW uses all 12 bits; ADSR uses the four hardware nibbles. Blank holds
the running value and R restores the corresponding instrument default.

F4 General adds PW touch recording: arm REC PW, choose the target channel, play,
and drag Pulse width. The sequencer captures row steps, one pattern pass per
drag, and the completed take is one undoable edit. Other sliders still edit the
instrument; ADSR automation is entered in F2. Native playback and SID/PRG exports
share the new semantics.

The main status line describes the cursor field or active gesture. Completed
edits appear as a temporary Last action message. The blue shared-filter lane is
also present on the playback Info page, with live filter state, and stays visible
after pause/stop.

Saves include the writing application's version. Ordinary projects remain
format 6; row-automation projects use format 7. The new reader opens structurally
compatible newer files with a warning and retains unfamiliar fields through
normal editing/saving. It does not claim to execute unknown future features.
Deleting an owning object also deletes its extension data. Malformed/incompatible
core structures still fail visibly and leave the source file intact.

See [automation controls](AUTOMATION.md), [file compatibility](SIDPULSE_FORMAT.md)
and [validation](VALIDATION-v0.2.24.md). Existing releases are not changed by this
source update. No remote release is published by this package.
