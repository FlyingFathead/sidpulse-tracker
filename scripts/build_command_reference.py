"""Generate a reviewable Markdown lookup table from the runtime registry."""
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
data = json.loads((root / "sidpulse/assets/commands.json").read_text())
lines = ["# Command / shortcut lookup table", "", "Generated from `sidpulse/assets/commands.json`. Edit that file; restart the app to reload.", "",
         "Flags are independent: `keybind_in_use` controls dispatch, `visible_in_help` controls help listing, and `visible_in_menu` controls menu listing. Both views also respect `visible`. Implementation and applicability must both be true for execution.", "",
         "Disabled commands stay grey in F1. `NA` means the single-SID target does not support that feature. `--` means pending or manually disabled. A shortcut's context matters: Alt+S sets instruments in the pattern editor, while Info-page stereo switching is inapplicable.", "",
         "The table inventories command groups and historical bindings. Some entries such as Arrows or the physical piano row describe a family whose argument is decoded by `keyboard.py`; JSON is never evaluated as Python. The `target` column names the semantic destination. Some IDs retain their original `future.*` names for stability even after implementation; the capability flags and target determine availability.", "",
         "| ID | Context | Shortcut | Action / target | Applicable | Implemented | Binding active | Visible | Help | Menu |", "|---|---|---|---|---|---|---|---|---|---|"]
for entry in data['commands']:
    values = [entry['id'], ', '.join(entry['contexts']), ' / '.join(entry['shortcuts']) or '(menu only)',
              entry['description'] + ' → ' + entry['target']]
    values += [str(entry[k]).lower() for k in ('applicable','implemented','keybind_in_use','visible','visible_in_help','visible_in_menu')]
    lines.append('| ' + ' | '.join(v.replace('|','/').replace('\n',' ') for v in values) + ' |')
lines += ['', 'Schism reference: https://github.com/schismtracker/schismtracker/tree/84d2c46c1d3b5660edbc3eca259bf1219e59623e/helptext', '']
(root/'docs/COMMANDS.md').write_text('\n'.join(lines))
print(f"Wrote {len(data['commands'])} command records")
