# References and dependencies

- [Schism Tracker](https://github.com/schismtracker/schismtracker), GPL-2.0 family:
  behavioral and visual reference; no Schism source files or font assets are
  bundled. Hand-written Python implementation.
- [Impulse Tracker](https://github.com/jthlim/impulse-tracker): historical UX reference.
- [pygame-ce](https://pyga.me/): native window/input and SDL PCM delivery; installed
  via requirements.txt, not redistributed inside these source ZIPs.
- [pyresidfp 0.17.0](https://github.com/pyresidfp/pyresidfp), GPL-2.0-or-later:
  Python binding and native reSIDfp chip emulation, installed via requirements.txt.
  Credit Sebastian Klemke, Dag Lem, Antti S. Lankila, Ken Händel, Leandro Nini
  and the libsidplayfp contributors. Native binaries/source are not bundled here.
- [DejaVu Sans Mono](https://dejavu-fonts.github.io/): bundled scalable font,
  with the complete distribution copyright/license in `sidpulse/assets/FONT_LICENSE.txt`.

The project is private at this stage. No public license for Harry's original
SIDpulse source has been selected in this initial handoff. Resolve public release
licensing, including compatibility with the GPL native SID dependency, before
publishing/distributing a combined application. This does not change how the
source prototype is run locally.

## v0.2.0 export validation

The bundled `assets/player.bin` is assembled from our original
`export/player.asm`; it contains no Schism/libsidplayfp player code. 64tass is an
optional development assembler and is not bundled. py65 1.2.0 is a development
CPU test dependency, not part of the shipped runtime. Independent validation
used libsidplayfp 2.6.0; that executable/library is not bundled in checkpoint ZIPs.
See PSID_EXPORT.md for primary specification and library references.

The project logo SVG was supplied by Harry. The original vector bytes are
preserved in assets/sidpulse-tracker-logo.svg and rasterized by pygame only
at the requested display size. No bitmap substitution is shipped.
