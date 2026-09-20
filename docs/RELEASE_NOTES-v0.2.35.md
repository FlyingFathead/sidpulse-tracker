# SIDpulse Tracker v0.2.35

The earlier volume-digi player is restored as **DIGI method #1**, selected by
default when exporting PCM instruments. It plays packed four-bit samples through
`$D418` while leaving the C64 display and sprite enables alone. It uses the
current note-trigger preparation, CH3 remapping and lossless music packers.
The bias voice is shut off when a sample finishes or is cut before restoring
master volume. Volume modulation of the other SID parts, clicks and VIC timing
jitter remain possible; this restores the earlier playback choice, not perfect
sample reproduction.

**DIGI method #2** retains the v0.2.34 waveform-DAC player. It blanks the display
and sprites to stabilize DAC capture. The four tested PAL/NTSC, 6581/8580 PRG
binaries are byte-for-byte identical to v0.2.34 when this method is selected.
Method #1 stores two four-bit frames per byte; method #2 uses a frequency byte
per frame plus its tail. No audio method is silently substituted by squeezing.

The export menu has a method selector operated by mouse or keyboard. Its choice
is saved in machine preferences; missing or invalid old preferences select #1.
The CLI uses `--digi-method 1` or `--digi-method 2` with SID/PRG exports.
Changing the method discards previous analysis so the displayed size/cycle
report and exported bytes always correspond to the selected player.

The confirmation describes the selected method. It retains **Continue as DIGI /
Synthesize all samples / Cancel**, with synthesis selected first. Only method #2
warns about display blanking. **Sample-to-SID wavetable synthesis remains the
preferred C64 workflow**, with audition before conversion and one-step undo.
Native playback, editing, W controls, sync/ring effects and source samples retain
their existing behavior.

Guides, the changelog and development notes live under `docs/`. The main README
links to detailed historical notes. Incremental upgrades from v0.2.34 run
`python scripts/finish_update.py` to remove the relocated root changelog.
See [installation](APPLY-v0.2.35.md), [PCM behavior](PCM_AND_AUDIO.md),
[validation](VALIDATION-v0.2.35.md) and [performance](PERFORMANCE-v0.2.35.md).

Keeping the display enabled is distinct from integrating this standalone player
into another program: it still owns CIA timers, IRQ/NMI vectors, memory and its
foreground loop. The method #1 music budget covers a standard screen without
sprite DMA; custom graphics need a coordinated timing budget. Physical C64
listening remains untested in this environment.
