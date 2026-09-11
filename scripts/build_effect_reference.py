"""Generate the effect review table from the runtime help catalog."""
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
data = json.loads((root / "sidpulse/assets/effects.json").read_text())
lines = ["# Effects: single-SID capability reference", "",
         "Edit `sidpulse/assets/effects.json`; F1 topic 9 and the bottom effect helper read that catalog. Restart the app after changes. Run this script to refresh this document.", "",
         "**v0.2.0 executes A/B/C/T, E/F/G/H/J, Q0y, SCx and SDx and compiles them to PSID.** See PSID_EXPORT.md for finite order traversal and target limits.", "",
         "`implemented` = host playback; `partial` = stated subset only; `planned` = relevant future replay effect; `mapping` = SID semantics require a decision; `future_digi` = sample-player work; `not_applicable` = outside the initial single-SID architecture. Live entries are green, pending entries grey and inapplicable entries red in help. The JSON separately records editability, preview implementation, PSID implementation, visibility and help visibility.", "",
         "The SID has a shared programmable filter. Its cutoff, resonance, routing and mode already work in F12; the blue-grey CTRL CH / FILTER area edits working row automation. The fourth area is not another oscillator. Oscillator waveform is selected in F4, separately from a vibrato modulation shape.", "",
         "Schism's reference help marks S0x/S1x/S2x with static `#` prefixes. Its current effect switch has no S0x implementation, includes S1x, and labels S2x as no longer implemented. Therefore a red help label alone is not a reliable test of an individual MOD's capabilities. SIDpulse will use its own capability table. PSID carries replay code/data; it does not itself implement these effect letters.", "",
         "| Code | IT/Schism reference | SID status | Decision / limitation |",
         "|---|---|---|---|"]
for e in data["effects"]:
    lines.append("| " + " | ".join(str(e[k]).replace("|", "/") for k in ("code", "description", "status", "reason")) + " |")
lines += ["", "Qxy reference volume modifiers: 0 keeps volume; 1/2/3/4/5 subtract 1/2/4/8/16; 6 multiplies by 2/3; 7 by 1/2; 8 is unused; 9/A/B/C/D add 1/2/4/8/16; E multiplies by 3/2; F doubles it. These PCM operations are not silently applied to SID sustain. Q0y now retriggers gate and instrument program; other volume modifiers remain unsupported.", "",
          "The EX column remains reserved. The legacy volume-column shorthand Ax/Bx/Cx/Dx, Ex/Fx, Gx and Hx is not executable or separately stored there in v0.2.0. Their main-effect counterparts remain available for source entry. FT2/XM translations are outside this initial IT/SID vocabulary.", "",
          "References: [Schism help](https://github.com/schismtracker/schismtracker/blob/84d2c46c1d3b5660edbc3eca259bf1219e59623e/helptext/pattern-editor), [Schism effect dispatch](https://github.com/schismtracker/schismtracker/blob/84d2c46c1d3b5660edbc3eca259bf1219e59623e/player/effects.c). SID-specific decisions follow the supplied v4 roadmap and the 2026-09-10 design discussion.", ""]
(root / "docs/EFFECTS.md").write_text("\n".join(lines))
print(f"Wrote {len(data['effects'])} effect entries")
