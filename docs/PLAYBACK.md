# v0.2.4 continuous output and voice displays

A single SDL device callback consumes a continuous PCM stream. The dedicated
emulation worker primes two blocks and replenishes the bounded reserve. It no
longer restarts short pygame mixer Sounds, polls their completion state, or
replaces a queued Sound during a completion transition. Musical ticks still
advance by generated sample count, independent of UI frames and wall-clock sleeps.

The callback fills unavailable samples with silence and counts one **Audio gap**
per continuous starvation episode while music/audition is expected. It does not
count initial priming, pauses or idle silence. This measures software starvation,
not every possible device/driver glitch; the previous queue-poll counter differs.

Only while the Info page is visible, three display-only reSIDfp copies mirror
registers/cycles at 12 kHz and isolate one voice each. Other envelopes are disabled;
source oscillator timing remains available for sync/ring modulation. Monitors
are before the shared filter and centered to remove DC. Enabling them initializes
from current registers; phase can initially differ from the audible chip. They
never feed audible PCM or export. Shared nonlinear filter output cannot be split
into three independent post-filter traces by this API.

# v0.2.4 SID attack timing

The sequencer already placed events on a stable sample clock. Native ENV3
measurements revealed a separate defect: regular First light drum attacks could
begin 2–36 ms after their scheduled note. GATE alone does not reset the SID's
ADSR rate counter.

The sequencer now looks ahead to upcoming note/retrigger events and prepares
GATE-off with zero ADSR rates at least 40 ms beforehand, rounded up to a tick.
It keeps those rates through the GATE pipeline before restoring the instrument's
ADSR. All operations are ordinary SID writes and cycle waits, shared with PSID.
Musical tick spacing is unchanged. Source ADSR values and drawings are preserved;
the previous sound's release tail can be shortened during restart preparation.

Lookahead follows tempo/speed changes, delayed notes, portamento, retriggers and
order/loop transitions through an isolated musical-state probe. A nearer trigger
prevents preparation for a later one. Very rapid retriggers without 40 ms of room
retain native chip behavior. Unscheduled live keyboard notes cannot be prepared
in advance. The fix does not claim to eliminate device/driver queue dropouts.

# v0.2.1 transport and timing

PAL/NTSC in F12 controls the chip clock and pitch calculation; musical tick rate
is tempo/2.5 in either mode. Whole-song loop is shared by preview and PSID export.
At a loop boundary initial speed/tempo/filter, program state and voice gates
restart; elapsed playback time continues. Explicit loop=false in older projects
is preserved. Keyboard audition restores initial master volume after the final
fade, preventing silent notes after playback. It follows current tempo and clock.

# v0.2.0 playback additions

The sample-clocked transport below is retained. VoicePrograms now executes F4
arpeggio/wave/pitch sequences, pulse modulation, delayed vibrato, timed gates and
retrigger in both song playback and keyboard audition. Jazz ticks run at 50 Hz;
song program ticks follow 2.5/tempo seconds. New notes restart their programs;
Gxx targets preserve gate, sounding instrument and program phase. Pattern H/J
replace their instrument counterpart for the current row. E/F/G/H/J/Q have
per-voice effect memory; H remembers each nonzero nibble independently.

The shared filter applies explicit control row fields at row start, then the
persistent signed cutoff slide on every tick (including tick zero), clamped to
0..2047. A dot/null keeps state. New initial-filter edits are adopted at the next
row snapshot, before that row's explicit control values. New instrument programs
apply on the next trigger; sounding notes retain their trigger-time instrument.

Executable row effects are A/B/C, absolute T, E/F/G/H/J, Q0y, SCx and SDx. Fine
slide variants act on tick zero, normal slides/portamento on later ticks. Q0y
restarts gate and instrument program without a fictional volume multiplier.
SCx/SDx outside a row's tick range do nothing. All units are in EFFECTS.md and
SIDPULSE_FORMAT.md. The PSID compiler shares this semantic path; see
PSID_EXPORT.md for its initial output constraints.

## v0.1.1 transport notes (historical effect/export scope below)

# v0.1.1 playback contract

One native SID, three fixed pattern voices, PAL or NTSC chip clock and 48 kHz mono PCM.
The sequencer advances only when its caller requests PCM frames. Tick duration
is `2.5 / tempo` seconds; fractional sample deadlines accumulate rationally.
Resizing, zoom, page changes and UI frame rate do not set musical time.

F5 starts the song when stopped and otherwise shows Info without restarting.
F12 **Restart on repeated F5** enables restart on every press; default OFF.
The machine preference `restart_on_f5` is saved independently of the song.
Ctrl+F5 always restarts, regardless of this setting. F6 loops the current pattern. Shift+F6 starts at
the current order. Ctrl+F6 loops the current pattern from the current row.
F7 uses the Ctrl+F7 mark, otherwise the current row. It searches the order list
from the selected order, wraps the search, and falls back to a pattern loop if
that pattern is not sequenced. The playback mark is separate from Alt+B/E block
selection. Repeat Ctrl+F7 at the same position to clear it.

Every row can trigger one event per voice. Instrument numbers update each
voice's instrument memory; instrument-only rows do not retrigger. Empty notes
continue the previous SID sound. Off clears GATE; cut disconnects the waveform.
A new note uses the existing backend's 32-chip-cycle gate gap before retrigger.
The emulator generates those samples too; they are retained in its PCM queue.
Starting transport clears audition allocations and initializes the selected
SID model, shared filter and monitor mask. Host startup settles the emulator's
power-up offset before the musical sample clock begins.

Supported effects are deliberately small:

| Effect | Current execution |
|---|---|
| A01..AFF | Set ticks per row immediately; A00 leaves speed unchanged. |
| Bxx | Jump to zero-based order after this row. Target beyond list stops. |
| Cxx | Break to zero-based hexadecimal row in the next order. B+C combines. |
| T20..TFF | Set absolute tempo immediately. T00/T0x/T1x are not implemented. |

The last command of each global type encountered from voice 1 through voice 3
wins. Break rows beyond the destination pattern begin at row zero. F6 keeps
pattern-loop mode: B/C can restart/break within that pattern but never leave it.
Other effects are preserved and reported in Info, not silently emulated with
invented SID behavior. There is no PSID compiler or executable CTRL CH lane yet.

Edits, including undo/redo, send isolated song snapshots to the audio worker.
The next row boundary adopts the latest received snapshot and preserves the
transport position, clamping positions when the edited structure shrinks.
Changed starting speed/tempo settings take effect at that boundary; unrelated
edits do not undo timing effects already in force. Filter settings are applied
immediately. Switching the actual SID model stops playback because chip state
must be reinitialized. F4 audition is available while stopped; editing notes
during playback does not steal song voices for independent keyboard jazz.

Pause freezes the sequencer and SDL channel, including queued PCM. F8 cuts all
voices and ramps host output down. The renderer reads an immutable transport
snapshot; its playhead may lead the speakers by the output queue/device delay.
Tracing is optional and does not modify song data.

The worker keeps a bounded reserve of two PCM blocks for the SDL callback. Buffer changes reopen
SDL, discard already queued sound and continue from the next generated frame.
A 5 Hz DC blocker and 5 ms transport ramps affect host output, never source
register values. Render budget and callback starvation counts help assess
scheduling pressure. They cannot identify all driver, hardware or system-wide
causes of crackle.

The native backend and the future C64 player must ultimately agree on musical
semantics. This checkpoint validates native PCM and sample-clock scheduling;
it does not yet claim cycle-identical C64 replay.


### v0.2.6 device-control deadlock fix

The pygame-ce 2.5.7 AudioDevice wrapper calls SDL_PauseAudioDevice while holding
Python's GIL. SDL waits for an in-flight callback, which needs that same GIL.
This reproduced the intermittent three-note/F5 freeze. `audio/device.py` calls
the same SDL library shipped with pygame through ctypes.CDLL, releasing the GIL
while SDL waits. Close first pauses and drains the callback, then closes the
device. It never loads an unrelated system SDL with different device IDs.

The regression suite forces an in-flight Python callback during both pause and
close, in a subprocess with a timeout. It also restarts native playback after
three-note edits and repeatedly switches two sparse patterns with F5/F6.
Windows uses pygame's bundled SDL2.dll; Windows execution needs a Windows host.
