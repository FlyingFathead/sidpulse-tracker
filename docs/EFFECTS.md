# Effects: single-SID capability reference

Edit `sidpulse/assets/effects.json`; F1 topic 9 and the bottom effect helper read that catalog. Restart the app after changes. Run this script to refresh this document.

**Playback and export execute A/B/C/T, E/F/G/H/J, Q0y, SCx, SDx and SID macros Z10/Z11/Z1F/Z20/Z21/Z2F.** See PSID_EXPORT.md for finite order traversal and target limits.

`implemented` = host playback; `partial` = stated subset only; `planned` = relevant future replay effect; `mapping` = SID semantics require a decision; `future_digi` = sample-player work; `not_applicable` = outside the initial single-SID architecture. Live entries are green, pending entries grey and inapplicable entries red in help. The JSON separately records editability, preview implementation, PSID implementation, visibility and help visibility.

The SID has a shared programmable filter. Its cutoff, resonance, routing and mode already work in F12; the blue-grey CTRL CH / FILTER area edits working row automation. The fourth area is not another oscillator. Oscillator waveform is selected in F4 or automated using the W pattern column. W is separate from FX Wxx global-volume slides and from vibrato modulation shape.

Schism's reference help marks S0x/S1x/S2x with static `#` prefixes. Its current effect switch has no S0x implementation, includes S1x, and labels S2x as no longer implemented. Therefore a red help label alone is not a reliable test of an individual MOD's capabilities. SIDpulse will use its own capability table. PSID carries replay code/data; it does not itself implement these effect letters.

| Code | IT/Schism reference | SID status | Decision / limitation |
|---|---|---|---|
| Axx | Song speed | implemented | Ticks per row 01..FF; A00 keeps speed. Preview and PSID. |
| Bxx | Order jump | partial | Order jump after row. Preview supports loops. PSID compiles finite traversals; use export_config.loop for whole-song repeat. |
| Cxx | Pattern break | implemented | Break to hexadecimal row of next order (or Bxx order). Out-of-range row becomes zero. |
| Dxx | Volume slides | mapping | D0x/Dx0 and fine DFx/DxF require a documented SID amplitude policy; no independent voice-volume register. |
| Exx | Pitch slide down | implemented | SID pitch slide down: xx*4 frequency units on later ticks. EFx fine x*4 and EEx extra-fine x on tick 0. E00 recalls memory. |
| Fxx | Pitch slide up | implemented | SID pitch slide up: xx*4 frequency units on later ticks. FFx fine x*4 and FEx extra-fine x on tick 0. F00 recalls memory. |
| Gxx | Tone portamento | implemented | Gate-preserving slide to target note, xx*4 SID frequency units per later tick. G00 recalls memory; no instrument restart. |
| Hxy | Vibrato | implemented | Sine vibrato: speed x (phase step x*4/256), depth y/16 semitone. Each zero nibble recalls its value. |
| Ixy | Tremor | mapping | Gate or waveform switching needs an explicit policy because SID retriggers affect ADSR. |
| Jxy | Arpeggio | implemented | Three-tick arpeggio: base, +x, +y semitones. Replaces instrument arp for this row. J00 recalls memory. |
| Kxx | Vibrato plus volume slide | mapping | Pitch motion is feasible; the Dxx amplitude mapping remains undecided. |
| Lxx | Portamento plus volume slide | mapping | Portamento is feasible; the Dxx amplitude mapping remains undecided. |
| Mxx | Channel volume | mapping | A SID voice has ADSR sustain, not a freely scalable PCM channel gain. |
| Nxx | Channel-volume slides | mapping | N0x/Nx0/NFx/NxF depend on the same per-voice amplitude policy. |
| Oxx | Sample offset | future_digi | Reserved for a future digi player, not SID oscillator sample memory. |
| Pxx | Panning slides | not_applicable | The initial single-SID output is mono. |
| Qxy | Note retrigger | partial | Q0y gate retriggers every y later ticks; Q00 recalls memory. Other x volume modifiers are unsupported for SID. |
| Rxy | Tremolo | mapping | Amplitude modulation requires a SID-native policy, not a fake per-voice mixer gain. |
| Sxx | Special commands | mapping | Subcommands are inventoried below. Do not silently reinterpret IT meanings. |
| Txx | Tempo and tempo slides | partial | Absolute tempo 20..FF hex, tick = 2.5/BPM seconds. T0x/T1x slides remain unsupported. |
| Uxy | Fine vibrato | planned | Finer pitch modulation; specify alongside Hxy. |
| Vxx | Global volume | mapping | IT global volume needs a defined quantization to the shared 4-bit SID master volume. |
| Wxx | Global-volume slides | mapping | W0x/Wx0/WFx/WxF use the same shared-volume mapping. |
| Xxx | Panning position | not_applicable | Single-SID mono target. |
| Yxy | Panbrello | not_applicable | Single-SID mono target. |
| Zxx | MIDI macro / SID macro proposal | partial | SID macros: Z10/11/1F sync off/on/default; Z20/21/2F ring off/on/default. Other values remain reserved and are not executed. |
| S0x | Legacy set-filter command | mapping | Not automatically the SID filter command. F12 already edits the actual shared SID filter; pattern encoding remains to be specified. |
| S1x | Glissando | planned | Pitch quantization can be implemented in the replay engine. |
| S2x | Finetune | mapping | Historical meaning needs an explicit pitch-unit mapping. |
| S3x | Vibrato shape | planned | IT shapes: 0 sine, 1 descending ramp, 2 square, 3 random; distinct from oscillator waveform. |
| S4x | Tremolo shape | mapping | Depends on the SID amplitude-modulation policy. |
| S5x | Panbrello shape | not_applicable | Single-SID mono target. |
| S6x | Tick delay | planned | Extend timing by ticks. |
| S70 | Cut past notes | not_applicable | No IT virtual past-note voices in the initial three-voice architecture. |
| S71 | Release past notes | not_applicable | No IT virtual past-note voices. |
| S72 | Fade past notes | not_applicable | No IT virtual past-note voices. |
| S73 | New-note action: cut | mapping | Define physical-voice gate/retrigger policy on the instrument side. |
| S74 | New-note action: continue | not_applicable | Keeping an old voice plus a new note requires extra voice allocation; not the initial fixed three lanes. |
| S75 | New-note action: release | mapping | SID release and voice reuse need explicit policy. |
| S76 | New-note action: fade | mapping | No independent PCM fade channel; a SID-specific behavior must be defined. |
| S77 | Disable volume envelope | mapping | Hardware ADSR cannot simply be bypassed like an IT volume envelope. |
| S78 | Enable volume envelope | mapping | Hardware ADSR and a future software macro are different things. |
| S79 | Disable panning envelope | not_applicable | Single-SID mono target. |
| S7A | Enable panning envelope | not_applicable | Single-SID mono target. |
| S7B | Disable pitch envelope | planned | Candidate control for future pitch macros. |
| S7C | Enable pitch envelope | planned | Candidate control for future pitch macros. |
| S8x | Panning position | not_applicable | Single-SID mono target. |
| S90 | Disable surround | not_applicable | Single-SID mono target. |
| S91 | Enable surround | not_applicable | Single-SID mono target. |
| S9E | Sample forward direction | future_digi | Requires a future digi player. |
| S9F | Sample reverse direction | future_digi | Requires a future digi player. |
| SAy | High sample-offset bits | future_digi | Requires a future digi player. |
| SB0 | Pattern loop start | planned | Mark the loop start. |
| SBx | Pattern loop repeat | planned | Replay from the loop mark x times. |
| SCx | Delayed note cut | implemented | Cut current voice on tick x; x outside row duration does nothing. |
| SDx | Delayed note start | implemented | Delay note/instrument trigger to tick x. SD0 is immediate; x outside row duration does nothing. |
| SEx | Row delay | planned | Extend timing by rows. |
| SFx | Select MIDI macro | mapping | External MIDI is later; any SID macro reinterpretation must be explicitly documented. |
| Z10 | Sync off | implemented | Persistent on this tracker channel, including held notes. Does not retrigger gate or edit the instrument. SID oscillators only; ring is audible with triangle and a running source oscillator. |
| Z11 | Sync on | implemented | Persistent on this tracker channel, including held notes. Does not retrigger gate or edit the instrument. SID oscillators only; ring is audible with triangle and a running source oscillator. |
| Z1F | Sync from instrument | implemented | Persistent on this tracker channel, including held notes. Does not retrigger gate or edit the instrument. SID oscillators only; ring is audible with triangle and a running source oscillator. |
| Z20 | Ring modulation off | implemented | Persistent on this tracker channel, including held notes. Does not retrigger gate or edit the instrument. SID oscillators only; ring is audible with triangle and a running source oscillator. |
| Z21 | Ring modulation on | implemented | Persistent on this tracker channel, including held notes. Does not retrigger gate or edit the instrument. SID oscillators only; ring is audible with triangle and a running source oscillator. |
| Z2F | Ring modulation from instrument | implemented | Persistent on this tracker channel, including held notes. Does not retrigger gate or edit the instrument. SID oscillators only; ring is audible with triangle and a running source oscillator. |

Qxy reference volume modifiers: 0 keeps volume; 1/2/3/4/5 subtract 1/2/4/8/16; 6 multiplies by 2/3; 7 by 1/2; 8 is unused; 9/A/B/C/D add 1/2/4/8/16; E multiplies by 3/2; F doubles it. These PCM operations are not silently applied to SID sustain. Q0y now retriggers gate and instrument program; other volume modifiers remain unsupported.

In v0.2.32 the unused EX column becomes AR: native arpeggio 0 OFF, 1 ON, R instrument, . hold. Existing FX codes are unchanged; AR OFF also suppresses Jxy. The legacy volume-column shorthand Ax/Bx/Cx/Dx, Ex/Fx, Gx and Hx is not executable or separately stored there in v0.2.0. Their main-effect counterparts remain available for source entry. FT2/XM translations are outside this initial IT/SID vocabulary.

References: [Schism help](https://github.com/schismtracker/schismtracker/blob/84d2c46c1d3b5660edbc3eca259bf1219e59623e/helptext/pattern-editor), [Schism effect dispatch](https://github.com/schismtracker/schismtracker/blob/84d2c46c1d3b5660edbc3eca259bf1219e59623e/player/effects.c). SID-specific decisions follow the supplied v4 roadmap and the 2026-09-10 design discussion.
