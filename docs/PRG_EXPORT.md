# PRG export

**File > Export PRG** compiles the current song as a standalone C64 program.
It offers to save the editable project first. **Export only** leaves the project
filename and unsaved status intact. Existing PRGs get a `.prg.bak` backup before
atomic replacement.

Command-line export requires no audio device or editor window:

```bash
bash run.sh path/to/song.sidpulse --export-prg song.prg
bash run.sh --play-welcome-song --export-prg autumn-at-five.prg
```

On Windows, replace `bash run.sh` with `.\run.cmd`. CLI export also saves the
editable `.sidpulse` beside the output. Use `--save-project PATH` to choose a
different native destination. `--export-sid` and `--export-prg` are alternatives.

## Playing the program

Choose the song's **PAL / NTSC** setting to match the target C64 before exporting.
The program checks the machine's video standard and returns with a message if
it differs. The selected 6581/8580 model describes the intended sound; the
program cannot change the physical SID chip.

On a normal C64 BASIC screen, with the PRG accessible on device 8:

```basic
LOAD "SONG",8,1
RUN
```

Use the filename exposed by your disk or storage device. In VICE, autostart the
PRG directly with the matching PAL/NTSC machine configuration. The program shows
the title, author and intended clock/model. **RUN/STOP** silences the music and
returns to BASIC. Song looping follows F12's existing loop option; a non-looping
song becomes silent at its end and waits for RUN/STOP.

No c1541 or assembler is needed to export a PRG. A disk-image utility is only
needed if your chosen transfer method requires a disk image. The exporter does
not create a D64 image or handle physical transfer to hardware.

## Music and implementation

The PRG contains the same compiled payload as [PSID export](PSID_EXPORT.md).
Native instrument arpeggios, delayed vibrato, ADSR and filter automation therefore
use the same ordered SID writes. There is no sampled audio or substitute synth.
SIDpulse's rounded welcome sound uses low-pass-filtered triangles; the SID has
no native sine-wave oscillator. Real chip/filter variations still affect timbre.

The two-byte load address is $0801. A BASIC `SYS 2061` line starts the loader at
$080D; the music player stays at $1000 with its play entry at $1003. The wrapper
polls CIA1 Timer A with CPU interrupts masked and calls the player on underflow.
Tempo changes and slow ticks follow the compiler's CIA period and idle-call
records. This is a standalone player that owns the machine while playing, not
an interrupt routine for a game or demo. It expects the normal BASIC environment
with KERNAL and I/O mapped in. RUN/STOP restores normal I/O and screen routines.

All PSID size, CPU, effect and arrangement limits also apply. Unsupported music
is rejected before writing. The extra loader occupies $0801–$0FFF; the compiled
music remains within $1000–$9FFF. Titles/authors are uppercase and limited to
32 display characters; unsupported characters are replaced with a warning.
The full original text remains in the native project.

The loader binary is bundled, so users do not need an assembler. Its source is
`sidpulse/export/prg_loader.asm`. Developers can rebuild it with:

```bash
64tass --nostart -o sidpulse/assets/prg-loader.bin sidpulse/export/prg_loader.asm
```

`tests/test_prg.py` executes the real loader/player in a 6502 CPU emulator with
scripted CIA flags, keyboard input and KERNAL API stubs. It checks startup,
ordered SID writes, tempo changes, mismatch exit, RUN/STOP, file backups and
CLI/menu integration. This is not a full C64 hardware or VICE execution test.
See [validation](VALIDATION.md) for the checks performed for this release.
