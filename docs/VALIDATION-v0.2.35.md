# Validation: v0.2.35

**286 focused regressions passed**: 168 PCM/method-selection, waveform,
batch-synthesis and export-job/UI checks, plus 118 ordinary SID squeezer,
PRG and squeezer-UI compatibility checks. This is a targeted run, not a claim
that the entire historical suite was rerun.

- Both DIGI methods compile PAL/NTSC, looping and non-looping PRG/RSID output.
  Every compilation verifies sample bytes, music writes, timer values, loop/stop
  behavior and conservative instruction budgets.
- Independent py65 tests interrupt all three music decoders at arbitrary
  instruction boundaries. Method #1 entry/replay leaves populated screen RAM
  and VIC registers unchanged, including a nonzero sprite-enable mask. This
  CPU-only test verifies register ownership, not the added cost of sprite DMA.
- Method #1 retains every packed nibble and uses smaller sample storage. Tests
  cover sample cuts, SID handoffs, channel remapping and source preservation.
- Method/target cache separation is checked against independent compilation.
  Old preferences default to #1; explicit #2 survives save/load; invalid values
  are rejected or defaulted appropriately.
- The selector works by keyboard and mouse at 640x480 and 1280x900. Changing it
  invalidates stale size/cycle reports. The confirmation identifies the method,
  keeps synthesis selected first, and retains cancellation and one-step undo.
- CLI exports both methods successfully and rejects the flag outside SID/PRG
  export. Six bundled player images rebuild exactly using 64tass.
- The 29 audio, sequencer, SID, song and project Python modules are unchanged
  from v0.2.34. W and sync/ring export regressions also pass.

## VICE playback

A private mixed SID/PCM arrangement was exported with method #1 for PAL and
NTSC, with 6581 and 8580 selected. All four PRGs autostarted and ran into the
song loop in VICE 3.7.1 classic reSID, with nonzero audio at the end. At every
observed sample trigger, the VIC display-enable bit remained set. Screenshots
retain the title while the samples play. A method #2 PAL/8580 control shows the
expected blanked screen and clear display-enable bit.

All four method #2 PRG binaries match the v0.2.34 baseline byte for byte.
Evidence hashes, display observations and screenshots are under
`validation/v0.2.35/`. The private arrangement and its exports are delivered
separately and are not included in the repository.

## Limits and packaging

Method #1 still modulates the overall SID mix and can have clicks or VIC timing
jitter. Its combined music budget reserves the standard screen's badline cost,
not arbitrary sprite/raster workloads. Both standalone players own CIA timers,
IRQ/NMI vectors and the foreground loop; neither is a drop-in graphics driver.
Physical C64 listening and physical audio-device testing remain outstanding.
See [matched performance measurements](PERFORMANCE-v0.2.35.md).

The incremental ZIP is checked by applying it over the v0.2.34 full ZIP and
running the cleanup twice. The resulting file bytes must exactly match the new
full ZIP. Guides, development notes and the changelog are under `docs/`.
