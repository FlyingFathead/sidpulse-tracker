# PCM samples and audio export (v0.2.35)

## Import, assign and trim

1. Open **F3**, select a sample slot (01–99), and choose **Import / replace**.
   The normal file browser loads WAV, MP3, FLAC, OGG, AIFF or M4A.
   **Auto-squeeze on import** at the top right defaults on: 4,000 Hz / 4-bit,
   with the original retained for Restore. Turn it off to keep import quality.
   Its saved config key is `sample_auto_squeeze_on_import` (boolean, default true).
   It applies to F3 imports and F4 instrument imports, and resets with Settings.
2. Choose **Assign instrument**, enter an instrument number, then use that
   number in the pattern. Existing SID settings are preserved. An empty
   instrument slot is created when needed.
3. An unmapped instrument can use **F4 → PCM → Override with sample**.
   **Assign instrument** enables this mapping directly. Slot 00 is unassigned.
   While mapped, F4 shows **Using sample number: name** and
   **Unmap sample from this instrument**. SID waveform, ADSR, pulse and
   sync/ring controls are hidden; unmapping restores access without changing
   their saved values. PCM programs retain arpeggio, pitch, vibrato, gate
   and retrigger controls because these still affect sample playback.
4. Drag the overlaid START/END markers in F3, or click their values. Values
   accept integer frame indexes or a number followed by `ms`. End is exclusive.
   Changes, assignments, imports and deletes participate in ordinary undo.

Root note 48 (C-4) plays a newly imported sample at its original speed. Set
the root to the note already used by a drum pattern to preserve that pattern.
Other notes change playback speed and pitch together. Instrument PCM gain is
0–100%, default 50%. The selected range is a one-shot, not an internal loop.
Retrigger, pitch, arpeggio, vibrato, gate and note-cut commands still apply.
SID ADSR, waveform, pulse and filter programs do not shape host PCM. Disable
unwanted pitch/gate programs when replacing a synthesized drum.

Host playback supports a sample on any of the three tracker channels. A sample
replaces that channel's SID oscillator. Channel and instrument mute/solo work
on samples too. F3's disabled M/S indicators direct you to the assigned
instrument controls. F3 shows the PCM waveform; the existing voice scopes
still show SID oscillator output. The master scope includes mixed PCM.

Imported samples are embedded in `.sidpulse`, including their trims, root
note and optional unsqueezed original. No external file is needed to reopen
the project. PCM projects use native format 8; arpeggio row commands use
format 9; W waveform or sync/ring row commands use format 10. Ordinary SID-only
projects still save format 6/7. Missing assigned samples play silently; audio and C64
exports reject missing samples instead of dropping them. Imports are limited
to 30 seconds each, 48 kHz, and 24 MiB of decoded bank data including originals.

## Squeeze

F3 **Squeeze** applies the selected range, anti-aliased sample-rate conversion,
and 4-, 8- or 16-bit quantization. Defaults are 4,000 Hz / 4-bit (about 2,000
packed bytes/second). Four-bit storage uses low nibble first and quantization
bin centers, following audio-bitsqueezer's convention. This is lossy.
**Restore original** restores the first imported source and its original trim.
Repeated squeezing does not accumulate nested originals. Undo also works.

**Normalize before squeezing** defaults on; **Normalize after squeezing**
defaults off. Both are saved preferences (`sample_normalize_before` and
`sample_normalize_after`) and can be changed in F3 or the squeeze dialog.
Before normalization helps quiet inputs use more quantizer levels; after
normalization restores peaks reduced by resampling. Existing projects are not
normalized on load.

**Normalize** opens **Normalize audio? OK / Cancel**, with Cancel selected first.
**Adjust volume** opens a linked percentage slider and numeric field, 0–200%,
initially 100% (no change), with OK / Cancel. These edits affect only the marked
range, preserve its markers and bit depth, retain the original, and support undo.
Overdriving the available range clips; increasing already quantized audio cannot
recover lost detail. Constant data is left unchanged by normalization.

## Synthesize audio into a SID wavetable

Choose **Synthesize audio (create wavetable)** in F3 after importing and marking
a sample. The current prototype accepts 12 ms–2 seconds. A cancellable worker
compares actual SID renders against the source's spectrum, pitch and envelope.
The result uses ordinary SID settings plus waveform/pitch sequences, up to 64
steps; no new pattern effect code or playback engine is required.

The result window lets you **Play sample**, **Play instrument**, stop, and browse
all 99 instrument slots. Choose an empty slot directly; replacing any occupied
slot requires OK / Cancel. Accepting is one undoable edit. The source sample is
retained, and the instrument has no PCM override or dependency on that sample.
It can play on any tracker channel and use ordinary SID/PRG export when the song
has no remaining PCM overrides.

F4 shows **Synthesized from sample NN: "filename"** between solid lines.
Generated instruments start **Frozen** to protect their settings and tables.
Choose **Unfreeze instrument** to experiment, then optionally freeze again.
Freeze is available to ordinary instruments too. It protects editor controls;
pattern automation, audition and export still work. Freeze changes are undoable
and saved. Source provenance is also saved, including the original sample name,
slot, marked-audio hash and analysis settings. It remains after sample deletion.

This is an approximation to audition, not exact waveform reconstruction. Root
note, tempo and SID model affect the fit; tables advance at the song tick rate.
Polyphonic material, long reverb, independent resonances and very fast transients
may fit poorly. See [findings and design references](SAMPLE_SYNTHESIS.md).

PCM WAV import works without FFmpeg when auto-squeeze is off; WAV export
always works without it. MP3 encoding, compressed
audio import, and rate conversion need an FFmpeg build with the corresponding
decoder and `libmp3lame` encoder. Install with `sudo apt install ffmpeg` on
Ubuntu/Debian, or `winget install Gyan.FFmpeg` on Windows. Restart the launcher
after installation. A portable binary can go in `tools/ffmpeg/bin`, or set
`SIDPULSE_FFMPEG` to its executable. FFmpeg is not bundled or downloaded by
the application. NumPy is installed by the normal project launchers.

## WAV and MP3

Choose **File Menu → Export WAV / MP3**. The output browser includes format,
filename, folder, and **Loops**. `0` plays once, `1` plays twice; up to 99 extra
passes are supported, with a two-hour total limit. Loops default to zero each
time the browser opens. The song's live loop switch does not override this.

WAV is mono 48 kHz / 16-bit PCM; MP3 is mono LAME VBR quality 2. Both render
the complete arrangement with SID and host PCM, ignoring preview mute/solo.
Tempo/speed changes and finite order jumps are honored. Backward/revisited
order jumps are rejected; make a finite order list and use the Loops field.
There is a short end ramp inside the exact duration, with no appended tail.

Rendering/import/squeeze work runs outside the UI/audio processes. Cancel
discards the staged result. Existing destinations are replaced only after a
complete export, with the previous file copied to `.bak`.

Headless examples:

```bash
python -m sidpulse song.sidpulse --export-audio song.wav --audio-loops 0
python -m sidpulse song.sidpulse --export-audio song.mp3 --audio-loops 2
```

## Experimental C64 PCM-enhanced routine

The export menu offers two **DIGI methods**, separate from squeezer versions:

| Method | Sample playback | Display | Main tradeoff |
|---|---|---|---|
| **#1 (default)** | Original packed four-bit `$D418` volume digis | Display and sprite enables preserved | Modulates the SID mix; clicks and VIC timing jitter can remain |
| **#2** | Timed waveform DAC on CH3 | Display and sprites blanked | More sample RAM; steady master volume between music commands |

Click the method row or focus it and press Space. The choice persists as
`export_squeeze.digi_method`; missing/invalid settings use method #1.
CLI exports use `--digi-method 1` (default) or `--digi-method 2`.
Changing the method invalidates the previous analysis and packing comparison.

Before saving, the popup describes the selected method. Only method #2 warns
about display blanking. Both reserve hardware CH3 and timer interrupts. Choose **Continue as DIGI**, **Synthesize all samples**
(recommended and selected first), or **Cancel**. The synthesis route fits every
PCM-mapped instrument in the background, then offers source/result audition.
**Apply all + review export** replaces the listed instrument slots in one undo
step and reanalyzes the normal SID export. Names, numbers and embedded sources
stay intact. The normal export/save controls then continue to the file browser.
Cancel or a failed fit leaves the song unchanged. Merely retaining unmapped
samples in the bank does not select the PCM routine or trigger this warning.
WAV/MP3 export uses the host engine and has no display warning.

Fitting approximates the sample, replacing PCM gain/pitch/gate/retrigger programs
with the generated SID settings. Always audition the converted arrangement.
See [batch synthesis behavior and limits](SAMPLE_SYNTHESIS.md).

SID/PRG export selects a separate routine when any instrument has a sample
override. The export analysis screen identifies it explicitly. All overrides
off selects the original SID player and its existing squeezer choices.

The experimental routine supports **CH1/2 SID + one PCM stream on CH3**.
PCM notes may use any **one tracker channel**. **Auto-remap PCM to CH3**
defaults on in the export dialog and is saved as `export_squeeze.pcm_auto_remap`.
A warning triangle identifies actual PCM notes outside tracker CH3. The mapping
is applied only to the export, with a cyclic rotation of all three SID voices
and filter-routing bits. The native project and its channel order are untouched.
For a CH1 sample part: tracker CH1 → C64 CH3, CH2 → CH1, CH3 → CH2.
For CH2: tracker CH1 → C64 CH2, CH2 → CH3, CH3 → CH1.

Ordinary SID notes on the sample channel still work: a kick sample, SID noise
hi-hat and snare sample can alternate on that channel. Instrument memory,
order/global-effect processing and note cuts retain tracker semantics. There
is no channel-routing work in the C64 playback loop. With remapping off, PCM
notes outside CH3 produce an error. PCM notes distributed across multiple
tracker channels are rejected, even when they do not overlap; this player has
one PCM voice. No sample part is silently discarded.

The normal squeezer comparison also runs for PCM-enhanced PRG/RSID exports:
v1.0, v2.0, v2.0.1 and v2.0.2 use their actual lossless music encodings.
**Show all versions** can be turned off for Top 3. All candidates use the same
baked sample bytes, and share recording/preparation work. File/RAM size and
executed music cycles are measured; PCM NMI and scheduling reserve are checked in
the combined deadline. Unsafe encodings are rejected. Squeeze/packing off
still exports PCM with uncompressed music data.

Samples are resampled
to approximately 4 kHz and quantized to four bits. Method #1 stores two frames
per byte, as in v0.2.32. Method #2 uses one frequency byte per frame in the
export, plus a midpoint and stop sentinel.
The project retains its compact packed sample storage. Pitch/effects,
gain and trims are baked into deduplicated one-shot renders on a copy.
This can cost more RAM when many different sample pitches are used.

The C64 player uses CIA1 timer A for music and CIA2 timer A/NMI for samples,
owns CH3, `$F8/$F9`, and RAM `$0801..$CFFF`, and banks ROM out while playing.
It needs no decompression buffer. PRGs load at `$0801` and run from BASIC;
RUN/STOP returns to BASIC. SID output is **RSID v2**, which requires a player
that emulates the C64's timers and interrupts. Older PSID-only players will
reject it. Export for the intended PAL/NTSC clock.

Method #1 restores the v0.2.32 volume-digi routine, with CH3 bias shut off
on sample completion, cut and handoff before restoring mixer volume. The
current trigger baking, channel remapping and all music packing versions remain
in use. Neither method changes native host playback or the source project.

Method #2 uses timed oscillator resets and brief triangle-wave captures.
It does not write master volume for every sample. A calibrated neutral level is
held between hits; ordinary notes explicitly reclaim the voice. A short mixer
ramp runs before musical time. SID model and PAL/NTSC selection determine the
DAC calibration and timer stabilization. Emulated 6581 and 8580 output levels
and distortion still differ, and neither exactly matches the host PCM balance.

Method #1 does not write VIC registers during playback. Its timing check
reserves CPU for the standard display's badlines, sample interrupts and music;
additional sprite DMA and custom raster code need their own integration budget.
Its PRG prints a title at startup; keeping the display enabled does not make its
standalone main loop a drop-in music driver for an existing game or demo.

Method #2 disables the display and sprites so VIC DMA cannot disrupt DAC timing.
RUN/STOP restores the display and returns to BASIC. Both methods own their
CIA timers, IRQ/NMI vectors, memory and foreground replay loop. Combining either
with an existing graphics engine requires coordinating those resources.
Screen blanking is a property of method #2, not a requirement of DIGI playback. The F3 and export screens mark PCM as experimental.

The bundled players are assembled from `sidpulse/export/pcm_volume_player.asm`
(method #1) and `sidpulse/export/pcm_player.asm` (method #2).
`scripts/build_pcm_player.py --check` checks reproducibility with 64tass.
Export requires no assembler. Every compile verifies packed bytes, executed
music writes, sample/DAC writes, loop/stop behavior and instruction-cycle budgets.
An independent py65 test checks interrupts inside the decoder. Physical C64
listening and integration testing remain outstanding; treat this as experimental.

## Supplied demo

`examples/autumn-at-five-synthwave-pcm-drums.sidpulse` is a separate version of
the supplied synthwave mix. Instrument 03 uses the supplied kick (sample 01,
root A-2 / 33, gain 45%); 04 uses the snare (sample 02, root B-3 / 47, gain 35%).
Their original drum pitch/gate programs are disabled for the replacement.
Instrument 16 remains SID because it combines a kick attack with a bass line.
Patterns and orders are preserved. The original supplied file is unmodified.

Updated PRG examples for each squeezer are under
`validation/v0.2.32/demo-squeezer-*.prg`; earlier captures remain under v0.2.31.
The optional listening previews
are clearly labeled **host PCM** and **C64 PCM**; they demonstrate the different
mixing paths rather than interchangeable sound quality.

References: [audio-bitsqueezer](https://github.com/FlyingFathead/audio-bitsqueezer),
[HVSC SID/RSID specification](https://www.hvsc.c64.org/download/C64Music/DOCUMENTS/SID_file_format.txt),
[FFmpeg documentation](https://ffmpeg.org/ffmpeg.html).
