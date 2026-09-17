> Implementation update (v0.2.18 candidate, 2026-09-17): export-only resident
> stream squeezing is implemented and export-core tested. The native instrument/
> table replay engine, full desktop/audio validation and hardware release gates
> remain distinct work. See [SQUEEZER.md](SQUEEZER.md) and
> [candidate validation](SQUEEZER_VALIDATION-v0.2.18.md).

# SIDpulse Tracker
## Canonical Project Roadmap

**Document status:** Canonical roadmap  
**Date:** 2026-09-10  
**Project name:** **SIDpulse Tracker**  
**Native editable format:** **`.sidpulse`**  
**Primary export targets:** `.sid`, `.prg`, player/data binaries  
**Implementation direction:** Python + pygame-ce  
**Musical target:** Commodore 64 SID  
**UX lineage:** deliberate homage to Impulse Tracker / Schism Tracker

**PROJECT EXPLANATION:** SIDpulse Tracker is an homage to Impulse Tracker and Schism Tracker, using Schism Tracker as the primary modern visual and interaction reference while preserving the fundamental workflow and muscle memory inherited from Impulse Tracker.

---

# WHAT?

Use **pygame-ce as the application shell**, not as the synth engine.

The clean split is:

```text
pygame-ce
├── resizable window / fullscreen
├── scalable tracker UI
├── keyboard input
├── cursor / selections
├── pattern + instrument screens
├── mouse only where useful
└── event loop

Python core
├── .sidpulse song model
├── patterns / orders
├── SID instruments
├── effects / macros
├── undo/redo
└── export compiler

native SID backend
├── 6581 / 8580 emulation
├── SID register writes
└── PCM generation

C64 backend
└── compile song → .sid / .prg
```

## Scalable UI

The UI should **not be permanently locked to 640×400, 640×480, or any other historical resolution**.

SIDpulse Tracker should preserve the visual structure and proportions of Impulse Tracker / Schism Tracker while being properly usable on modern displays.

The user must be able to:

* freely resize the application window;
* maximize it;
* use fullscreen;
* automatically fit the tracker UI to the available window;
* increase or decrease UI scale manually;
* zoom the interface substantially for poor eyesight or high-DPI displays;
* retain readable text and usable controls at every supported scale.

In other words:

```text
window size
    +
user UI zoom
    ↓
layout calculation
    ↓
font/cell dimensions
    ↓
tracker interface
```

The application should maintain a configurable **UI scale / zoom factor** independently of the operating-system window size.

For example:

```text
50%
75%
100%
125%
150%
175%
200%
250%
300%
```

or a continuous equivalent.

Keyboard shortcuts should allow quick zoom adjustment, in addition to settings/menu controls.

A user with a large display should be able to choose between:

```text
smaller UI
→ more pattern rows / information visible

larger UI
→ bigger text / easier readability
```

This should not merely stretch a tiny 640×400 framebuffer into a blurry mess.

Instead, SIDpulse Tracker should draw its interface using scalable layout metrics:

```text
base character width
base character height
row height
channel width
margin
panel dimensions
font scale
```

and derive the actual on-screen geometry from the current UI scale.

Where practical, bitmap-style fonts and graphical elements should be scaled cleanly so the interface retains the crisp tracker aesthetic. Integer scaling and nearest-neighbor rendering can be preferred for explicitly pixel-style modes, but **readability takes priority over rigid pixel purity**.

The design goal is:

> **Impulse Tracker / Schism Tracker structure and feel, without forcing the user's eyes to live in 1997.**

The tracker should also react sensibly when the available space changes. A larger window can expose:

* more pattern rows;
* more order entries;
* more instrument information;
* wider names or status information;

rather than merely surrounding a fixed-size interface with empty space.

Do not use conventional GUI widgets for the central tracker interface. Draw the tracker ourselves:

* text cells;
* pattern rows;
* selections;
* cursor;
* order list;
* instrument page;
* envelope/macro displays;
* status areas.

That gives us complete control over layout, scaling and appearance while keeping it recognizably Schism/IT-like.

## Input

For input, pygame is particularly valuable because **the tracker owns the keyboard**.

Build a central key dispatcher around `KEYDOWN` / `KEYUP`, modifiers, and preferably scancodes where appropriate.

The pattern editor should receive semantic commands such as:

```python
note_entry(...)
set_instrument_digit(...)
move_cursor(...)
note_cut()
note_off()
insert_row()
delete_row()
block_copy()
play_from_cursor()
```

rather than scattering raw key checks throughout the UI.

Separate **physical input mapping from editor behavior**:

```text
physical key
    ↓
IT/Schism keymap
    ↓
editor command
    ↓
song mutation
```

That makes IT/Schism compatibility testable and allows alternative keyboard mappings without contaminating the editor logic.

UI zoom commands should go through this same system:

```text
physical key
    ↓
zoom_in / zoom_out / zoom_reset
    ↓
UI scale
    ↓
layout recalculation
```

Changing UI scale must **never affect song state, playback timing, keyboard-note mapping or editor semantics**.

## Audio

Do **not** make `pygame.mixer` the SID engine.

A native SID emulator should produce PCM.

The tracker engine should communicate with the SID backend through SID register writes:

```python
sid.write(0x00, value)
sid.write(0x01, value)
...
pcm = sid.render(samples)
```

Pygame can initially be used to get that PCM to the sound device, but the SID emulation and tracker timing remain independent from the UI.

Eventually use a proper buffered/callback audio path so audio timing is authoritative.

The UI frame rate, window resizing and UI zoom level must **never affect music timing**.

Conceptually:

```text
UI thread / loop
├── pygame events
├── keyboard
├── layout
├── zoom
└── rendering

audio/playback path
├── tracker ticks
├── SID register events
├── SID emulation
└── PCM output
```

These systems interact through application/song state, but they do not share timing.

## Main loop

The application loop remains deliberately straightforward:

```python
while running:
    handle_pygame_events()
    process_editor_commands()
    update_editor()

    recalculate_layout_if_needed()
    render_tracker()

    pygame.display.flip()
```

Window resize or zoom changes trigger layout recalculation:

```python
if window_resized or ui_scale_changed:
    recalculate_layout(
        window_size=current_window_size,
        ui_scale=user_ui_scale,
    )
```

Audio continues independently.

## Condensed architecture rule

> **Pygame owns pixels, window scaling and keys. Python owns the tracker. A native SID library owns chip emulation. The exporter owns the C64.**

And for the UI specifically:

> **Fit the tracker to the window, let the user zoom it as large as they need, and preserve the IT/Schism feel at every scale.**

---

Here’s a tightened version that incorporates the import/remapping distinction and the separate instrument/sample namespaces without muddying the project intent.

# PREFACE 1: THE INTERFACE (AND PRIMARY SOURCES)

* Take inspiration freely from the original **Impulse Tracker**:
  [https://github.com/jthlim/impulse-tracker](https://github.com/jthlim/impulse-tracker)

* Also use **Schism Tracker** as a major modern reference and homage:
  [https://github.com/schismtracker/schismtracker](https://github.com/schismtracker/schismtracker)
  License: GPL-2.0

* **Schism Tracker should generally be the stronger visual and practical reference**, because it preserves the Impulse Tracker workflow while presenting it through a newer, cleaner and more polished interface.

* SIDpulse Tracker does **not** need to be a literal fork of either project. What matters is preserving the **feel, keyboard workflow, pattern-editing behavior and muscle memory** of Impulse Tracker / Schism Tracker.

## MUST PRESERVE

As much as reasonably possible:

* note entry;
* instrument-number entry;
* note-off / note-cut;
* insert/delete;
* block operations;
* copy/paste;
* pattern selection;
* order list;
* row highlighting;
* keyboard jazz;
* effect entry;
* follow-song;
* pattern looping;
* playback from cursor/order;
* familiar IT/Schism keybindings;
* keyboard-first editing.

This is one of the project's defining requirements.

> If SIDpulse Tracker feels like "a modern synth with an Impulse Tracker skin", it has missed the point.

The goal is for an experienced IT/Schism user to sit down and immediately recognize how the tracker wants to be operated.

---

# PREFACE 2: THE EXECUTION / DEVELOPMENT

SIDpulse Tracker is a **modern desktop application**.

It is **not** intended to run on a Commodore 64.

The Commodore 64 is the **playback/export target**.

Because Impulse Tracker / Schism Tracker relies heavily on direct keyboard control, a browser-first implementation is undesirable. Web applications cannot reliably own every keyboard shortcut required to preserve the original tracker feel.

The preferred implementation is therefore:

* **Python**
* **pygame-ce**
* a platform-agnostic native SID emulation backend
* Linux and Windows as primary development/runtime platforms

The application itself should remain largely source-driven and easy to run without compiling SIDpulse Tracker into a native binary during ordinary development.

Native dependencies underneath Python are acceptable where performance or hardware emulation requires them.

## MUST HAVE

### Native editable project format

```text
.sidpulse
```

This is SIDpulse Tracker's own lossless working/project format.

It should preserve:

* patterns;
* order list;
* SID instruments;
* samples/digis;
* ADSR;
* waveform settings;
* pulse settings;
* macros;
* filter programs;
* metadata;
* comments;
* editor/project state where useful;
* SID model preference;
* export configuration.

### C64 export

At minimum:

```text
.sid
.prg
```

The `.sid` exporter should initially target **PSID**, with RSID support added where genuinely necessary.

Additional useful output later:

```text
player.bin
song.bin
song.inc
```

for integration into games, demos and other C64 software.

---

# PREFACE 3: THE SID ENGINE, INSTRUMENTS AND SAMPLES

SIDpulse Tracker must use a **platform-agnostic SID implementation** for realtime preview.

The host application should support accurate emulation of at least:

* MOS 6581;
* MOS 8580.

The SID emulator itself does not need to be written in Python. A native implementation exposed through a Python binding is preferable.

The important architectural separation is:

```text
SIDpulse Tracker
      |
      v
SID-native song engine
      |
      +--> host SID emulator -> realtime preview
      |
      +--> C64 compiler -> .sid / .prg / player + data
```

The host-side song engine and the exported 6510 replay engine should ultimately implement the same musical semantics.

---

# PREFACE 4: INSTRUMENTS AND SAMPLES ARE SEPARATE THINGS

Impulse Tracker distinguished between **instruments** and **samples**.

SIDpulse Tracker should preserve that conceptual separation.

Therefore:

```text
Instrument 01
```

and:

```text
Sample 01
```

may both exist.

They belong to **different namespaces**.

A SID instrument describes synthesis behavior such as:

* waveform;
* ADSR;
* pulse width;
* sync;
* ring modulation;
* gate/retrigger behavior;
* pitch macros;
* waveform/arpeggio macros;
* pulse macros;
* filter intent/macros.

A sample represents actual PCM/digi data.

This is important because C64 SID music sometimes incorporates small digital samples or other digi techniques in addition to ordinary SID synthesis.

SIDpulse Tracker should therefore not artificially force the user to choose:

> instrument 01 **or** sample 01

The tracker should be capable of containing both.

Exactly how digi playback is compiled for the C64 can evolve separately from the instrument model.

---

# PREFACE 5: `.SID` IMPORT AND REMAPPING

SIDpulse Tracker must support `.sid` import, but the meaning of "import" must be stated honestly.

A `.sid` file is generally **not a tracker project file**.

It can contain:

* executable 6510 code;
* an arbitrary replay routine;
* custom timing;
* custom instrument logic;
* self-modifying code;
* digi/sample techniques;
* structures that bear no direct relationship to tracker rows, patterns or instruments.

Therefore arbitrary `.sid` import cannot promise a perfect reconstruction of the original composition.

## Import behavior

### `.sidpulse`

Opening a `.sidpulse` project should be:

> **native and lossless**

### `.sid` created by SIDpulse Tracker

SIDpulse-generated files should be identifiable by the application where practical.

If the exported song format is recognized, SIDpulse may be able to reconstruct a project very accurately from its own compiled data.

### Third-party `.sid`

Import should be presented as:

> **Import SID → Remap to SIDpulse Project**

The application should clearly warn:

> This SID was not created as a SIDpulse Tracker project. SID files may contain arbitrary C64 playback code and do not necessarily preserve tracker patterns, instruments, effects or original composition structure. SIDpulse will analyze the tune and create the closest editable `.sidpulse` interpretation it can. The result may not be 1:1 with the original.

The importer may analyze:

* note frequencies;
* gate transitions;
* ADSR changes;
* waveform changes;
* pulse width;
* filter state;
* timing;
* repeated instrument-like register patterns;
* digi/sample activity where detectable.

The result is a **best-effort editable reconstruction**, not a claim of magical source-code recovery.

---

# PREFACE 6: THE FUNDAMENTAL DESIGN RULE

SIDpulse Tracker should preserve the **workflow and feel** of Impulse Tracker / Schism Tracker while treating the SID as the actual hardware synthesizer underneath.

The project is therefore:

```text
Impulse Tracker / Schism Tracker
        |
        | UX, keyboard workflow,
        | pattern-editing philosophy
        v
SIDpulse Tracker
        |
        | new SID-native internals
        v
6581 / 8580
        |
        v
.sid / .prg / C64 replay data
```

The workstation is modern.

The tracker workflow is deliberately old-school.

The synthesis model is SID-native.

The editable source is `.sidpulse`.

The exported artifact can run on a real Commodore 64.

> **SIDpulse Tracker is an homage to Impulse Tracker, not an attempt to turn Impulse Tracker into something it never was.**

I’d use this version as the new front matter for the roadmap.

---

# PREFACE X: FIGURING IT OUT

- Figure out a way to handle the C64 sound chip; a platform agnostic SID chip implementation is required 
- Mapping of traditional IT/Schism instruments and samples, but maybe in a way where if you use an instrument, you can't use a sample with the same number: or can you? As in, what about the small digis that people use with SID music?

---

# 0. Project identity

**SIDpulse Tracker** is a modern SID-native music tracker inspired by, and explicitly paying homage to, the workflow, keyboard feel, editing philosophy, and pattern-centric interaction model of **Impulse Tracker** (AND **Schism Tracker**).

It is not intended to be:

- a literal fork of Impulse Tracker;
- a literal fork of Schism Tracker;
- a sample tracker with a SID emulator bolted onto it;
- a tracker that runs on the Commodore 64;
- a browser-first application;
- a mouse-heavy modern synthesizer wearing an IT-style skin.

It is a **new tracker** whose user-experience contract is:

> **Preserve the feel and muscle memory that made Impulse Tracker exceptional, then reinterpret the instrument and playback model honestly for the SID.**

The name deliberately echoes the lineage:

```text
Impulse Tracker
      ↓
SIDpulse Tracker
```

The project should openly describe itself as:

> **An homage to Impulse Tracker, reimagined as a modern SID-native tracker.**

---

# 1. The core product idea

The workstation is modern.

The target synthesizer is the SID.

The compiled artifact runs on the C64.

Conceptually:

```text
Modern PC
   |
   v
SIDpulse Tracker
Python + pygame-ce
   |
   +-- IT-style pattern editing
   +-- IT-style keyboard workflow
   +-- SID instruments
   +-- ADSR
   +-- waveform control
   +-- pulse width
   +-- macros
   +-- shared SID filter
   +-- 6581 / 8580 preview
   |
   v
.sidpulse project
   |
   +--------------+----------------+----------------+
   |              |                |                |
   v              v                v                v
 .sid           .prg          player.bin        song.bin
PSID/RSID    standalone C64   replay engine      song data
```

The C64 is an **export/playback target**, not the editor host.

---

# 2. Requirement zero: preserve IT muscle memory

This is the single most important requirement.

Preserve as much as possible:

- note entry;
- instrument-number entry;
- note-off;
- note-cut;
- insert/delete;
- block operations;
- copy/paste;
- pattern selection;
- order list;
- row highlighting;
- keyboard jazz;
- effect entry;
- follow-song;
- pattern looping;
- playback from cursor;
- playback from order;
- keyboard-first editing;
- familiar IT keybindings;
- familiar cursor movement;
- field navigation;
- selection semantics;
- edit masks where practical;
- hexadecimal numeric entry;
- fast pattern editing without depending on a mouse.

Acceptance test:

> An experienced Impulse Tracker or Schism Tracker user should be able to sit down and immediately recognize the workflow.

If the first reaction is:

> “Where the fuck did my tracker keys go?”

the design has failed.

If the program feels like:

> “a modern synth with an IT skin”

the design has failed.

---

# 3. Schism Tracker and Impulse Tracker are references, not shackles

SIDpulse Tracker should use:

## Original Impulse Tracker

as the historical reference for:

- keyboard behavior;
- pattern editing;
- cursor movement;
- order-list behavior;
- instrument philosophy;
- playback/navigation semantics;
- historical collaboration behavior;
- visual and interaction conventions.

## Schism Tracker

as a modern reference implementation for:

- IT-like editing behavior on current systems;
- practical keyboard behavior;
- page organization;
- pattern rendering;
- navigation;
- full-screen tracker feel.

But SIDpulse Tracker should not inherit irrelevant architecture merely to inherit the UI.

We do **not** need to inherit:

- PCM sample mixers;
- MOD/XM/S3M compatibility;
- high virtual-channel counts;
- generic sample-player abstractions;
- legacy module playback machinery.

Instead:

> **Preserve behavior. Rebuild internals around the SID.**

---

# 4. Why Python + pygame-ce

The canonical implementation should be a modern desktop application written primarily in Python using **pygame-ce** for display, keyboard input, timing/UI infrastructure, and application framing.

This suits the actual problem extremely well.

SIDpulse Tracker is fundamentally:

- a pattern editor;
- a keyboard state machine;
- an instrument editor;
- a sequencer;
- an audio-preview frontend;
- a compiler.

It does not need a giant widget framework.

Pygame gives us:

- direct keyboard events;
- scancode access where needed;
- modifier-state handling;
- key-repeat control;
- custom cursor behavior;
- pixel-perfect drawing;
- fixed logical resolutions;
- fullscreen/windowed control;
- explicit redraw logic;
- a natural fit for a retro tracker UI.

---

# 5. Canonical source-first deployment

Development should remain easy.

## Linux

```bash
git clone <repo>
cd sidpulse-tracker

python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt

python -m sidpulse
```

## Windows

```powershell
git clone <repo>
cd sidpulse-tracker

py -m venv .venv
.venv\Scripts\Activate.ps1

pip install -r requirements.txt

py -m sidpulse
```

Optional packaged releases can later use:

- PyInstaller;
- Nuitka;
- platform-specific packaging.

The canonical project remains source-first.

---

# 6. Important qualification about “no compilation”

SIDpulse Tracker itself can remain Python source.

However:

- pygame contains compiled/native components;
- a serious SID emulator backend will almost certainly contain native compiled code.

That is fine.

The intended development model is:

> Python owns the tracker, editor, compiler, song model, project format, and most application logic.

Optimized native code owns expensive low-level SID emulation.

---

# 7. Browser status

A browser implementation is **not** a primary target.

The browser is technically powerful enough.

The problem is keyboard ownership.

Impulse Tracker uses the keyboard too heavily to casually accept browser interception of:

- Ctrl+W;
- Ctrl+T;
- Ctrl+L;
- F5;
- focus/navigation shortcuts;
- browser-specific reserved combinations.

Some bindings can be intercepted.

Some cannot be relied upon.

Requirement Zero wins.

Therefore:

> **The native desktop application defines canonical keyboard behavior.**

A browser or WASM build may be revisited later as a secondary port, but it must not contaminate the primary UX.

---

# 8. Canonical UI model

Recommended logical display:

```text
640×400-ish
or
640×480-ish
```

with:

- fixed character grid;
- tracker-style font;
- nearest-neighbor scaling;
- explicit selection;
- explicit cursor;
- row highlighting;
- windowed/fullscreen modes;
- deterministic placement.

Do not start with conventional GUI widgets.

The tracker should feel like a tracker terminal.

---

# 9. Pattern editor

The central view remains IT-like.

Primary channels:

```text
SID VOICE 1
SID VOICE 2
SID VOICE 3
```

Primary cell concept:

```text
NOTE  INS  VOL/EXPR  FX  PARAM
```

Example:

```text
VOICE 1       VOICE 2       VOICE 3

C-4 01 40 H04 G-3 07 .. ... --- .. .. ...
... .. .. ... ... .. .. ... D-4 04 32 G08
=== .. .. ... ... .. .. ... ... .. .. ...
```

MVP should expose the three actual hardware voices honestly.

Do not begin with 64 virtual channels and automatic voice allocation.

That can be explored later if genuinely useful.

---

# 10. Keyboard system

The keyboard layer is foundational infrastructure.

Implement:

- KEYDOWN;
- KEYUP;
- scancode-based handling where appropriate;
- modifier masks;
- configurable repeat;
- focus-loss handling;
- octave control;
- keyboard jazz;
- hexadecimal entry;
- pattern navigation;
- block editing;
- transport controls.

Maintain a compatibility document against:

- Impulse Tracker behavior;
- Schism Tracker behavior.

Where they differ, preserve whichever behavior best matches expected IT muscle memory unless there is a strong practical reason not to.

---

# 11. SID-native song model

The internal model should be explicitly designed around one SID first.

MVP hardware assumptions:

- one SID;
- three voices;
- PAL first;
- 6581 / 8580 selectable host preview;
- stock C64-compatible export.

Future expansion:

- NTSC;
- 2SID;
- 3SID;
- configurable SID addresses;
- hardware SID output;
- optional digi/sample techniques.

Do not design the MVP as a generic multi-synth workstation.

---

# 12. Instrument editor

The IT-style instrument concept maps beautifully onto SID synthesis.

A SIDpulse instrument should expose real SID state.

## Waveform / control

- triangle;
- sawtooth;
- pulse;
- noise;
- supported combined waveforms where intentional;
- sync;
- ring modulation;
- gate behavior.

## ADSR

Correct hardware terminology:

- Attack;
- Decay;
- Sustain;
- Release.

These map directly to SID envelope registers.

## Pulse width

- initial pulse width;
- pulse macro;
- sweep behavior.

## Gate / retrigger

- normal retrigger;
- legato;
- no retrigger;
- hard restart;
- gate delay;
- retrigger delay;
- pretrigger ADSR where needed.

## Filter intent

- route through filter;
- initial cutoff;
- initial resonance;
- filter mode;
- assigned filter macro.

## Macros

- waveform;
- arpeggio;
- pitch;
- pulse;
- filter;
- gate/control.

---

# 13. Example instrument screen

Conceptual only:

```text
INSTRUMENT 01 : RESONANT BASTARD

OSCILLATOR
WAVEFORM      SAW + PULSE
PULSE WIDTH   $0800
SYNC          OFF
RING          OFF

ADSR
ATTACK        2
DECAY         5
SUSTAIN       A
RELEASE       4

GATE
MODE          HARD
DELAY         2

FILTER
ROUTE         YES
MODE          LP
CUTOFF        $680
RESONANCE     B

MACROS
WAVE          03
PULSE         06
PITCH         01
FILTER        04
GATE          02
```

The exact screen should evolve through use.

The important thing is that it feels like an IT instrument page, not a VST plugin.

---

# 14. ADSR versus higher-level envelopes

Impulse Tracker had rich multi-point instrument envelopes.

SIDpulse Tracker should preserve that spirit while distinguishing hardware truth from editor convenience.

## Hardware ADSR

Actual SID:

```text
A D S R
```

## Higher-level host structures

Can include:

- pitch envelopes;
- pulse envelopes;
- waveform sequences;
- arpeggios;
- filter curves;
- gate programs;
- pseudo-expression curves.

These compile to tick-level SID actions.

Thus:

```text
IT-style editing power
+
SID-native output
```

---

# 15. Filter model

The SID has **one shared filter block**.

SIDpulse Tracker must not pretend otherwise.

Expose:

- cutoff;
- resonance;
- low-pass;
- band-pass;
- high-pass;
- voice 1 route;
- voice 2 route;
- voice 3 route;
- master volume.

Possible UI representations:

1. global pattern lane;
2. global effect commands;
3. instrument “filter intent” that activates/modifies global filter macros.

Prototype these before freezing the UX.

---

# 16. Volume-column semantics

Impulse Tracker users expect a volume-like field.

The SID does not offer clean independent PCM-style volume registers per voice.

Therefore the field may remain for muscle memory, but its meaning must be SID-native.

Potential interpretations:

- expression;
- sustain manipulation;
- macro intensity;
- envelope scaling;
- gate behavior;
- explicitly global volume where appropriate.

Never fake hardware capabilities for cosmetic compatibility.

---

# 17. Macros / tables

A serious SID tracker needs per-tick programs.

Likely macro families:

```text
WAVE
ARPEGGIO
PITCH
PULSE
FILTER
GATE
CONTROL
```

Example:

```text
WAVE/ARP MACRO 04

00 SAW +0
01 SAW +7
02 SAW +12
03 JUMP 00
```

Pulse example:

```text
PULSE MACRO 12

00 SETPW $0600
01 ADDPW +$0020
02 WAIT 24
03 ADDPW -$0020
04 WAIT 24
05 JUMP 01
```

The editor can use rich structures.

The exported representation should be optimized for cheap 6510 execution.

---

# 18. Pattern effects

Preserve IT-style hexadecimal effect entry where the semantics make sense.

Possible initial vocabulary:

```text
Axx  speed / tick control
Bxx  order jump
Cxx  pattern break
Exx  pitch slide down
Fxx  pitch slide up
Gxx  tone portamento
Hxx  vibrato
Jxx  arpeggio
Sxx  special SID subcommands
Txx  tempo
Zxx  filter/global macro control
```

This is provisional.

Where IT effects map naturally, preserve the mnemonic.

Where they do not, preserve the editing workflow but define SID-native behavior.

---

# 19. SID emulation

Do not implement the SID emulator in Python.

Use an established optimized backend through a Python binding.

Preferred direction:

- reSIDfp/libsidplayfp-derived backend;
- pyresidfp or equivalent if suitable.

Required preview:

```text
6581
8580
```

Abstract behind a clean interface.

Example:

```python
class SIDBackend:
    def reset(self): ...
    def set_model(self, model): ...
    def write(self, register, value): ...
    def render(self, frames): ...
```

This keeps song semantics independent from one emulator implementation.

---

# 20. Audio architecture

Early versions may use pygame audio output.

Long-term:

```text
song tick engine
      |
      v
SID register events
      |
      v
native SID emulator
      |
      v
PCM ring buffer
      |
      v
audio callback/device
```

The audio clock should eventually be the timing authority.

Requirements:

- low latency for keyboard jazz;
- stable timing;
- glitch-free playback;
- deterministic register behavior;
- host playback close to exported C64 playback.

---

# 21. Keyboard jazz

Mandatory.

Workflow:

```text
select instrument
hit tracker note keys
hear SID immediately
change ADSR
hit notes
hear result
change pulse
hit notes
hear result
change filter
hit notes
hear result
```

The first version that does this convincingly is a major project milestone.

---

# 22. Internal Python data model

Suggested classes:

```python
Song
Pattern
PatternRow
Voice
Instrument
Macro
FilterProgram
OrderList
PlaybackState
SIDState
ProjectMetadata
CompilerConfig
```

Avoid generic abstractions that exist only because sample trackers need them.

Design for the SID directly.

---

# 23. Explicit edit operations

Represent user edits as explicit commands:

```python
SetCell(...)
SetInstrumentField(...)
InsertRows(...)
DeleteRows(...)
SetOrder(...)
SetMacroStep(...)
SetFilterState(...)
SetSongSetting(...)
```

Benefits:

- undo/redo;
- deterministic tests;
- history;
- future collaboration;
- replay/debugging.

This should be designed early enough that collaboration does not later require rewriting the editor.

---

# 24. Native editable file format: `.sidpulse`

The canonical project/song extension is:

> **`.sidpulse`**

Example:

```text
starlit-theme.sidpulse
```

This is the editable source project.

It must remain distinct from exported C64 artifacts.

Example flow:

```text
my_tune.sidpulse
      |
      +--> my_tune.sid
      +--> my_tune.prg
      +--> player.bin + song.bin
```

---

# 25. What `.sidpulse` stores

The native project format should preserve everything necessary for continued editing:

- patterns;
- order list;
- instruments;
- ADSR;
- waveforms;
- pulse settings;
- macros;
- filter programs;
- comments;
- names;
- song metadata;
- editor metadata where useful;
- selected SID model;
- PAL/NTSC intent;
- export settings;
- future collaboration metadata.

A `.sid` export cannot be expected to preserve all of this.

---

# 26. `.sidpulse` versioning

Version the format from day one.

The first format can be simple.

Candidates:

- JSON;
- MessagePack;
- CBOR;
- zip/container around structured metadata;
- another versioned binary format later.

Start simple.

Example conceptual magic/version:

```text
SIDPULSE
format_version=1
```

or equivalent structured metadata.

The requirement is not a fancy binary format.

The requirement is:

> old projects must be detectable, migratable, and recoverable.

---

# 27. Deterministic tick engine

The same song semantics should drive:

1. host preview;
2. compiled C64 playback.

Host engine responsibilities:

- order processing;
- rows;
- ticks;
- note triggers;
- instrument changes;
- ADSR/gate state;
- effects;
- macros;
- shared filter state;
- desired SID register events.

The exported C64 player should implement equivalent semantics.

---

# 28. Golden host-vs-C64 register trace

This should become a central regression test.

For the same `.sidpulse` project:

```text
Python engine
     |
     v
SID register trace
```

versus:

```text
compiled 6510 player
     |
    VICE
     |
     v
SID register trace
```

Compare:

- tick;
- register;
- value;
- order.

This catches semantic drift between editor preview and the real C64 export.

---

# 29. C64 replay engine

The replay engine is a first-class deliverable.

Write in 6502/6510 assembly.

Responsibilities:

- row/tick processing;
- note frequency;
- instruments;
- ADSR;
- waveform state;
- gate behavior;
- effects;
- macros;
- shared filter state;
- real SID writes.

Goals:

- compact;
- deterministic;
- cycle-conscious;
- configurable/relocatable where practical;
- feature-strippable.

Possible build modes:

```text
MINIMAL
STANDARD
FULL
```

---

# 30. Host compiler

The host compiler can spend modern CPU time to save C64 resources.

Potential optimizations:

- pattern deduplication;
- empty-row compression;
- repeated-row compression;
- macro deduplication;
- instrument deduplication;
- feature stripping;
- compact note encoding;
- state reuse;
- register-write minimization;
- size-vs-CPU export modes.

The compiler can take seconds if that saves meaningful bytes on the target machine.

---

# 31. `.SID` export

Primary music distribution target:

```text
.sid
```

Initial implementation should likely produce PSID.

Export payload:

```text
PSID header
+
6510 replay routine
+
compiled song data
+
instrument/macro data
```

Support:

- load address;
- init address;
- play address;
- song count;
- start song;
- PAL/NTSC metadata;
- 6581/8580 preference;
- title;
- author;
- released string;
- flags.

Add RSID only when real execution requirements justify it.

---

# 32. `.PRG` export

Required.

Useful for:

- VICE;
- real C64 testing;
- musicians;
- direct standalone execution.

A basic exported PRG should:

- initialize safely;
- initialize the player;
- install timing;
- play the song;
- optionally display minimal status text.

---

# 33. Raw integration exports

Also valuable:

```text
player.bin
song.bin
song.inc
symbols/map
```

Use cases:

- games;
- demos;
- C64 3D toolkit;
- cartridges;
- custom productions.

---

# 34. Collaboration

Impulse Tracker historically supported collaborative editing.

SIDpulse Tracker should preserve the possibility of restoring this idea.

Not MVP.

Future architecture can use:

- asyncio;
- WebSockets;
- TCP;
- LAN sessions;
- internet sessions;
- compact command transport.

Because edits are explicit operations, networking can synchronize:

```text
SetCell
SetInstrument
SetADSR
SetMacro
SetOrder
InsertRows
DeleteRows
```

without inventing an entirely separate collaborative document model.

---

# 35. Collaboration philosophy

Do not turn SIDpulse Tracker into a mandatory cloud application.

Desired future modes:

- fully offline;
- optional LAN collaboration;
- optional internet collaboration;
- optionally self-hostable.

The historical spirit is:

> two people can work on the same tracker song at once.

Not:

> upload your song to a SaaS dashboard.

---

# 36. Browser future

Browser remains possible later.

Possible future forms:

- pygame/SDL-compatible WASM build;
- a secondary frontend using the same project/song semantics;
- PWA/fullscreen mode.

But browser support must obey:

> **The keyboard belongs to the tracker.**

If browser limitations require too many incompatible shortcuts, browser remains secondary or is dropped.

---

# 37. Proposed repository structure

```text
sidpulse-tracker/
├── README.md
├── pyproject.toml
├── requirements.txt
│
├── sidpulse/
│   ├── __main__.py
│   ├── app.py
│   │
│   ├── ui/
│   │   ├── renderer.py
│   │   ├── font.py
│   │   ├── keyboard.py
│   │   ├── pattern_view.py
│   │   ├── order_view.py
│   │   ├── instrument_view.py
│   │   ├── macro_view.py
│   │   └── status_view.py
│   │
│   ├── song/
│   │   ├── model.py
│   │   ├── pattern.py
│   │   ├── instrument.py
│   │   ├── macro.py
│   │   ├── filter.py
│   │   ├── effects.py
│   │   └── tick.py
│   │
│   ├── sid/
│   │   ├── backend.py
│   │   ├── backend_residfp.py
│   │   ├── registers.py
│   │   └── frequency.py
│   │
│   ├── audio/
│   │   ├── engine.py
│   │   └── ringbuffer.py
│   │
│   ├── export/
│   │   ├── compile_song.py
│   │   ├── psid.py
│   │   ├── prg.py
│   │   └── raw.py
│   │
│   ├── project/
│   │   ├── sidpulse_format.py
│   │   ├── serialize.py
│   │   └── migrations.py
│   │
│   ├── commands/
│   │   ├── base.py
│   │   ├── pattern.py
│   │   ├── instrument.py
│   │   └── history.py
│   │
│   └── collaboration/
│       └── future/
│
├── c64/
│   ├── player.asm
│   ├── effects.asm
│   ├── macros.asm
│   ├── startup.asm
│   └── test_harness.asm
│
├── docs/
│   ├── ROADMAP.md
│   ├── IT_HOMAGE.md
│   ├── IT_KEY_COMPAT.md
│   ├── SID_MODEL.md
│   ├── EFFECTS.md
│   ├── SIDPULSE_FORMAT.md
│   └── C64_EXPORT.md
│
└── tests/
    ├── test_keys.py
    ├── test_effects.py
    ├── test_adsr.py
    ├── test_macros.py
    ├── test_project.py
    └── test_trace_compare.py
```

---

# 38. Roadmap phases

## Phase 0 — document the homage

Before major implementation:

- document which IT behaviors are sacred;
- document Schism equivalents;
- build `IT_KEY_COMPAT.md`;
- define language for public project description.

Public framing:

> **SIDpulse Tracker is an homage to Impulse Tracker, reimagined as a modern SID-native tracker.**

Success:

> The project knows exactly what it is preserving and why.

---

## Phase 1 — pygame tracker shell

Implement:

- application window;
- logical surface;
- tracker font;
- pattern grid;
- row numbers;
- row highlighting;
- cursor;
- fullscreen/windowed;
- keyboard event logger.

No SID yet.

Success:

> It already looks and moves like a tracker.

---

## Phase 2 — silent IT muscle-memory test

Implement:

- QWERTY note entry;
- octave controls;
- instrument numbers;
- note cut/off;
- cursor movement;
- insert/delete;
- selection;
- copy/paste;
- block operations;
- pattern navigation;
- order list.

Success:

> An experienced IT user can edit a silent pattern without relearning the interface.

Do not proceed until this feels right.

---

## Phase 3 — SID backend proof

Integrate an accurate SID emulator backend.

Implement:

- reset;
- register writes;
- 6581;
- 8580;
- triangle;
- saw;
- pulse;
- noise;
- gate;
- PCM output.

Success:

> Python application can make authentic SID sound.

---

## Phase 4 — keyboard jazz

Connect the tracker keyboard to SID playback.

Implement:

- selected instrument;
- three preview voices;
- waveform;
- ADSR;
- gate;
- model switching.

Success:

> It feels like IT, but the instrument coming out is a SID.

This is the first major emotional proof of concept.

---

## Phase 5 — SID instrument page

Implement:

- waveform;
- ADSR;
- pulse width;
- sync;
- ring;
- gate modes;
- hard restart options;
- filter intent;
- macro assignment.

Success:

> The IT instrument concept has been successfully transformed into a SID instrument concept.

---

## Phase 6 — native `.sidpulse` format

Introduce:

```text
.sidpulse
```

Store:

- song;
- patterns;
- orders;
- instruments;
- macros;
- filters;
- metadata;
- version.

Success:

> Real editable projects survive save/reload.

Version 1 from day one.

---

## Phase 7 — pattern playback

Implement:

- three SID voices;
- order flow;
- row/tick timing;
- note triggers;
- instrument changes;
- note cut/off;
- playback from cursor;
- follow song;
- pattern loop.

Success:

> A simple complete SID composition works entirely in SIDpulse Tracker.

---

## Phase 8 — tracker effects

Implement:

- arpeggio;
- pitch slides;
- tone portamento;
- vibrato;
- speed/tempo;
- order jump;
- pattern break;
- SID special commands.

Preserve IT-style effect entry where sensible.

---

## Phase 9 — macros

Implement:

- wave/arpeggio macro;
- pulse macro;
- pitch macro;
- gate macro;
- filter macro.

Success:

> Serious SID timbral programming becomes possible.

---

## Phase 10 — global SID filter

Implement:

- shared filter;
- cutoff;
- resonance;
- routing;
- LP/BP/HP;
- filter commands;
- instrument filter intent.

Success:

> Filter behavior is powerful without lying about SID hardware.

---

## Phase 11 — C64 replay engine

Write 6510 replay code.

Implement:

- tick engine;
- pattern decode;
- instruments;
- ADSR;
- effects;
- macros;
- filter.

Success:

> A compiled SIDpulse song plays correctly under VICE.

---

## Phase 12 — register-trace equivalence

Generate:

```text
Python engine trace
vs
VICE/C64 engine trace
```

Compare writes.

Success:

> Host and exported engine agree semantically.

---

## Phase 13 — `.PRG` exporter

Generate runnable C64 program.

Success:

> Export, launch, hear the tune.

---

## Phase 14 — `.SID` exporter

Generate PSID.

Implement:

- header;
- metadata;
- init/play;
- clock/model flags;
- song payload.

Success:

> Standard SID players accept SIDpulse output.

---

## Phase 15 — host compiler/optimizer

Implement:

- pattern compression;
- macro deduplication;
- feature stripping;
- repeated-state compression;
- register-write optimization;
- size-vs-CPU export profiles.

Success:

> Export is suitable for real demos and games.

---

## Phase 16 — native alpha

Ship:

- source;
- Linux;
- Windows;
- optional packaged builds;
- documentation;
- original example `.sidpulse` songs;
- example instruments;
- `.sid` and `.prg` output.

Success:

> Somebody besides the author can make music with it.

---

## Phase 17 — collaboration command layer

Formalize:

- edit operations;
- revision IDs;
- deterministic undo/redo;
- mutation history.

Success:

> Two simulated clients can apply the same operations and converge.

---

## Phase 18 — LAN/network collaboration

Implement:

- host;
- join;
- remote cursors;
- pattern edits;
- instrument edits;
- macro edits;
- optional shared transport.

Success:

> Two people can jam on the same tracker song again.

---

## Phase 19 — optional browser experiment

Only after native application maturity:

- assess pygame/WASM;
- assess keyboard losses;
- assess WebAudio;
- assess file persistence;
- assess fullscreen/PWA.

Success requires:

> Browser version remains recognizably SIDpulse Tracker without redefining the keyboard model.

If not, browser remains secondary.

---

# 39. MVP definition

A credible first serious SIDpulse Tracker release should contain:

- Python + pygame-ce desktop application;
- IT-style pattern view;
- IT-style keyboard workflow;
- three SID voices;
- SID instruments;
- ADSR;
- waveform selection;
- pulse width;
- note-off / note-cut;
- keyboard jazz;
- patterns/orders;
- basic effects;
- macros;
- 6581/8580 preview;
- `.sidpulse` save/load;
- `.prg` export;
- `.sid` export.

Not required for MVP:

- browser;
- collaboration;
- multi-SID;
- arbitrary `.SID` import;
- sample/digi support;
- NTSC.

---

# 40. Non-goals

Do not:

- run the editor on a C64;
- become browser-first;
- preserve sample-tracker internals that do not serve SID composition;
- emulate arbitrary `.IT` songs on three voices;
- fake per-voice volume or filter hardware;
- become a mouse-first synth workstation;
- implement a SID emulator in Python;
- build collaboration before core composition works;
- promise arbitrary SID decompilation;
- chase multi-SID before one SID is excellent.

---

# 41. Naming and file-format rules

Canonical spelling:

> **SIDpulse Tracker**

Not:

- SidPulse;
- SIDPulse;
- SID Pulse Tracker;
- SchismSID.

Native source extension:

> **`.sidpulse`**

Compiled/export extensions:

```text
.sid
.prg
.bin
.inc
```

The name should remain visibly linked to the project's identity as an Impulse Tracker homage.

---

# 42. Public description draft

Short form:

> **SIDpulse Tracker is a modern SID-native music tracker and an homage to Impulse Tracker, preserving its keyboard-driven workflow and pattern-editing feel while replacing the sample-centric sound engine with real SID instruments, ADSR, pulse, filter and macro control.**

Longer form:

> **SIDpulse Tracker is a modern Python/pygame-ce tracker inspired by the workflow and muscle memory of Impulse Tracker. It treats the Commodore 64 SID as the actual target synthesizer rather than emulating a sample tracker on top of three voices. Songs are authored as editable `.sidpulse` projects and can be compiled into `.sid`, `.prg`, or replay-engine/data output for real C64 hardware and emulators.**

---

# 43. First implementation target

Do not begin with:

- `.SID` packing;
- C64 assembly;
- networking;
- browser support;
- multi-SID.

Do this first:

```text
1. create Python project
2. open pygame window
3. render tracker grid
4. reproduce IT note-entry behavior
5. implement instrument number entry
6. implement note-off / note-cut
7. implement block/cursor behavior
8. connect SID emulator
9. define one SID instrument
10. add waveform + ADSR
11. keyboard-jazz it
```

Then stop and ask:

> **Does SIDpulse Tracker feel like Impulse Tracker under the fingers?**

If yes, continue.

If no, fix that before building anything more complicated.

---

# 44. Project philosophy

The core realization behind this roadmap is:

> **We do not actually need Schism Tracker's codebase. We need the feel that Schism preserves from Impulse Tracker.**

Therefore the clean architecture is:

```text
Impulse Tracker
historical UX truth
      |
      v
Schism Tracker
modern behavioral reference
      |
      v
SIDpulse Tracker
new Python/pygame-ce implementation
      |
      v
SID-native song model
      |
      v
C64 compiler/export
```

This avoids carrying around an irrelevant sample-tracker engine merely to obtain the editing interface.

---

# 45. Governing statements

> **SIDpulse Tracker is an homage to Impulse Tracker.**

> **Preserve IT muscle memory.**

> **The keyboard belongs to the tracker.**

> **Preserve behavior, not unnecessary implementation baggage.**

> **The workstation is modern.**

> **The song model is SID-native.**

> **The artifact can be C64-native.**

> **`.sidpulse` is the editable source. `.sid` is an export.**

> **If it feels like a modern synth with an IT skin, it has missed the point.**

> **If it feels like Impulse Tracker woke up and discovered the SID, we're doing it right.**

> **SIDpulse Tracker. `.SID Barrett approved.`**




## Checkpoint 0.2.1 (user-selected version)

Retain the existing tracker layout. Include separated voices in playback, native
PAL/NTSC and shared loop control, fixed post-fade audition, graphical instrument
sliders/ADSR/arp editing, real buttons and safe dialogs. Add scrollable unused slots
and Choose preset / No preset / Manual. Catalog has 39 built-in sounds in nine
categories plus a user bank. Themes/fonts are persistent machine settings; default
crimson and dark text on beige. About is framed/centred with an x and requested
blank line. No multi-SID or sample/digi importer is added. Full plus incremental
0.2.0-to-0.2.1 ZIPs are the deliverables. See INSTRUMENTS.md and APPEARANCE.md.
