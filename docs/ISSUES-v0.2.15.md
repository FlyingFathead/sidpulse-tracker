# SIDpulse Tracker v0.2.15-cp001: activity dots, ADSR display, song looping

## Instrument activity indicators

### Issue and implementation

The F4 instrument list did not show which instrument slots were being used.
The old audio `active` tuple reports SID voice numbers, not instrument IDs;
current editor selection and sequencer instrument-memory rows are not reliable
substitutes for the identity of a sound that was actually triggered.

The right side of every instrument row now has a small activity dot. A real
note trigger brightens it; an assigned/gated voice keeps it lit, and a 150 ms
visual decay makes short percussion triggers visible between display refreshes.
Playback, pattern looping, normal keyboard audition and cell/row audition share
this display. Moving the cursor or selecting a preset does not light a dot.
Several active SID voices using the same instrument are combined on its row.
Clicking a dot still selects the underlying instrument row; hover help explains
its meaning. Instrument names reserve three character positions for the dot.

A transient instrument ID is captured in `VoicePrograms.trigger()`. Instrument-
only rows and Gxx portamento do not falsely change the source of a held sound.
Delayed notes publish activity only on their actual trigger tick, and retriggers
flash the same slot again. Cell/row audition now passes its source instrument ID
through the existing audio message, as ordinary keyboard audition already did.

The worker publishes immutable snapshots. Trigger storage is bounded to the
three voices and 99 instrument slots. SID register writes, note scheduling and
PCM processing are unchanged by this observer. ADSR lookahead probes explicitly
detach it, including when a probe crosses a song-loop boundary, so future notes
cannot create phantom activity. No additional SID emulator instances or waveform
scopes are enabled for these dots.

Pause, panic, playback resets, master volume zero and monitor mutes suppress
activity appropriately. These dots represent **note/gate activity, not loudness
or measured SID envelopes**. A held gate at sustain zero, or a sound attenuated
by the shared filter, can still be assigned/active. Release tails are not measured;
the short dot fade is UI persistence, not a claim about release time. The display
follows the render worker, so it may lead heard output by the existing PCM queue.

### Sample-bank limitation

F3 now has matching idle dots, but **PCM/digi playback is still not implemented**.
The sample-bank explanation and dot tooltip say this explicitly. An instrument
and a sample with the same number remain separate; SID instrument activity never
lights a PCM sample. There are no fabricated sample-playback events.

A future PCM implementation should supply its own sample IDs and note/lifetime
telemetry. That is a separate engine feature, not something this patch pretends
is already present.

## ADSR attack display

### What was wrong in the graph

The original schematic mapped attack X as `0.04 + 0.22 * attack / 15`, forcing
a visible 4%-of-plot attack width even at hexadecimal `00`. This was not a
physical SID-time scale. The graph now uses `0.26 * attack / 15`, so `00` draws
vertically at the graph's left edge, and dragging the attack handle all the way
left enters `00`. The maximum endpoint is unchanged, and the inverse drag mapping
matches all sixteen values. Both General and ADSR tabs use the same functions.
Decay, sustain, release, numeric input and the undoable edit path are retained.

### The SID-specific distinction

**Attack 00 is not a zero-millisecond attack on SID hardware.** It is the fastest
rate, nominally about **2 ms at a 1 MHz clock**. The MOS 6581 datasheet's Table 2
also explains clock scaling. This is about 2.03 ms with the tracker's PAL clock
and 1.96 ms with its NTSC clock; these are approximate nominal rates, not a promise
about every retrigger/envelope starting state.

The vertical line is therefore a **schematic fastest-setting convention**, not
a change to the SID's envelope behavior. The graph is labelled schematic and
shows the selected attack's approximate time and PAL/NTSC clock. At compact graph
heights that information moves into the title rather than overlapping controls.
No instrument ADSR values, SID rate tables, native emulator behavior or exported
register data are changed by the drawing fix.

Source: [MOS 6581 datasheet reproduction, Attack/Decay, Table 2 and clock note](https://www.waitingforfriday.com/?p=661).
The approximate caption uses the datasheet's nominal attack rates and the existing
`CLOCKS` constants. It is not a shared linear time axis: sustain duration depends
on note-off and the editable stage widths remain schematic controls.

## F11: loop the song at playlist end

The existing control was buried in F12 as **Song / PSID loop**. It now also
appears at the bottom of F11 (Order List / Pattern Bank):

```text
Loop song when the playlist ends                       ON [L]
ON: restart from order 000.
Saved in project; also used by SID/PRG export. F6 loops one pattern.
```

OFF instead reads **OFF: stop after the last playlist entry.** Narrow layouts use
**Loop at playlist end**; compact heights reserve space above the status strip.
Click ON/OFF or press **L** in either F11 panel. Holding L toggles only once until
release; Ctrl+L still opens a project. An invalid inline order number blocks the
operation rather than losing its draft. F12's renamed **Loop song at end** row
uses the same setter; Enter now toggles directly.

This is one per-song `export_config.loop` flag, not another machine preference.
Ctrl+S saves it and Ctrl+Backspace undoes it. Missing values retain the old ON
default; explicitly saved OFF stays OFF. The supplied Broken Machine v20/v21
Shuffle and Vocal_Edit files all store OFF and are not silently rewritten.
F6 still loops only the current pattern; SID/PRG export uses the existing shared
flag. Explicit musical Bxx jumps are not cancelled by end-of-playlist OFF.

### Related transport bug fixed

A loop edit received during the final row was previously applied too late:
ON -> OFF could restart once more, while OFF -> ON could stop anyway. The end
boundary now consults the queued song's flag before deciding to stop/restart.
A restart uses that snapshot. Explicit one-pass `loop=False` overrides still
win. Changes apply after receipt by the audio worker; queued PCM is not rewound.

## Validation and limits

Executed in Linux / Python 3.13.5:

- **273 core tests passed, 4 pygame-dependent checks/modules skipped.** Includes
  actual trigger IDs, delayed/retriggered notes, memory-only and portamento rows,
  multi-voice aggregation, masks, master volume zero, pause/reset, immutable and
  bounded telemetry, no future-lookahead events, identical observer/no-observer
  register traces, all ADSR rates/inverse mappings, native round trips, loop
  boundaries, octave input, exporter diagnostics and updater safety.
- A worker integration test executes the actual worker/observer with explicitly
  fake SID and PCM I/O. It checks audition ID publication, release and panic.
  This is not an audible or native-emulator test.
- **108 F11 layout cases and 54 ADSR layout/endpoint cases passed** using actual
  drawing functions with a recording renderer/rectangle adapter. Dot color/hit
  metadata and loop key routing were also checked. This is not SDL rendering.
- The existing four bundled PAL/NTSC example SID hashes remain unchanged.
- Real-pygame tests are included for dot selection versus playback identity,
  marker clicks, separate sample slots, audition message IDs, attack drag/undo,
  F11/F12 synchronization and repeated-key suppression.

pygame-ce installation failed in this environment; a direct PyPI request also
failed DNS resolution. **Windows/Linux desktop rendering, physical keyboard and
mouse behavior, native reSIDfp output and real-device audio were not tested.**
The source patch adds no dependencies and leaves the configured audio buffer alone.

## Packaging and retained work

Cumulative **v0.2.15-cp001** against the exact supplied v0.2.12, v0.2.13-cp001 or
v0.2.14-cp001 source snapshots. ZIP paths begin `sidpulse-tracker/` for extraction
from the repository's parent. The versioned standard-library apply script checks
the ZIP and known baseline hashes, accepts LF/CRLF, refuses conflicts, backs up
replacements and is idempotent. It performs no downloads, Git commits or pushes.
Direct unzip is supported but has no conflict/backup protection.

Octave-digit input, grid shading, effect-status fixes, and the prominent
**Shorten or simplify the project and try again** oversized-export refusal are
retained. No song files, preferences, virtual environments, native binaries,
fonts or history bundles are included. Native project format remains 6.
WAV/MP3 export and player compression are not implemented in this update.

## Further proposals, not implemented

Run the included GUI tests and a real desktop playback/audition acceptance pass.
A sample-specific activity feed should be added when PCM/digi playback exists.
An optional envelope/volume meter would require actual per-voice measurement or
an explicitly identified envelope model; it must not be confused with these
lightweight trigger/gate dots. Native performance profiling should accompany
that work rather than enabling multiple extra SID instances by default.
