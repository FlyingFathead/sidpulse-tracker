# SIDpulse Tracker v0.2.31

WAV/MP3 export and playable PCM samples are now integrated into the tracker.
The export browser includes folder, filename, format and extra song loops;
zero loops means one complete pass. Audio jobs run outside the UI/audio
processes and publish only completed files.

F3 now imports and squeezes samples, shows a cached waveform with draggable
start/end markers, and accepts precise frame or millisecond bounds. Samples
map to instrument numbers through F4's new PCM tab. Existing instruments keep
their SID settings when **Override with sample** is enabled or disabled.
Samples, trims, root note, gain and squeeze originals save in the project and
participate in undo. Ordinary SID projects keep their original format/player.

A separate **experimental PCM-enhanced C64 routine** uses CH1/2 for SID and
CH3 for packed, approximately 4 kHz / 4-bit volume digis. The export screen
identifies the routine; `.sid` output is RSID and PRG output is BASIC-loadable.
Notes on CH3 can switch between PCM and SID. PCM on CH1/2 is rejected with an
explanation. The original SID exporter remains in use when overrides are off.

The supplied 189.89-second synthwave demo is included unchanged, together
with a separate version assigning the provided kick and snare to instruments
03 and 04. Instrument 16's combined kick/bass remains SID. The full C64 PCM
demo occupies 35,327 loaded bytes, including player, samples and packed music;
it exports as a 35,453-byte RSID or a 35,329-byte PRG.

Validation includes 1,502 passing regression tests, exact sample nibble/write
checks during compilation, independent py65 interrupt-preemption tests, and
libsidplayfp C64 emulation. The complete demo was emulated through a loop on
PAL/8580, with 32-second checks on PAL/6581 and both NTSC chip models. Worst
verified sample interrupt cost is 109 CPU cycles against a 246-cycle PAL
sample interval. The demo's maximum music call is 7,892 cycles; its conservative
combined music/PCM/VIC bound is 17,178 cycles. Source and binaries are included.

This is an experimental volume-digi implementation: sample playback changes
the other SID voices' volume, and 6581/8580 timbre and levels differ. The player
owns the machine's timers and memory while running. Physical C64 listening and
integration with other programs remain untested. The host WAV/MP3 mix retains
fuller sample quality. See [usage and limitations](PCM_AND_AUDIO.md).

NumPy is a new launcher-installed dependency. FFmpeg remains optional: PCM WAV
import/export needs none, while MP3, compressed sample import and sample-rate
conversion require it. No FFmpeg binary or C64 ROM is distributed.

See [matched performance measurements](PERFORMANCE-v0.2.31.md), raw results in
`validation/v0.2.31`, and [installation/update instructions](APPLY-v0.2.31.md).
Both release ZIPs extract under `sidpulse-tracker/`; the v0.2.30 overlay is
verified to produce exactly the full v0.2.31 archive.
