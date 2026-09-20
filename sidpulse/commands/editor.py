"""Editor semantics; physical keyboard details never enter this module."""
from copy import deepcopy
from dataclasses import replace
import time

from sidpulse.commands.history import History
from sidpulse.song.model import Cell, Instrument, Pattern, Song, ENVELOPE_FIELDS
from sidpulse.playback.voices import supported
from sidpulse.ui.pattern_grid import PatternGrid

from sidpulse.commands.pattern_fields import FIELDS, COLUMN_OFFSETS, CURSOR_HINTS
from sidpulse.commands.blocks import BlockEditing


class Editor(BlockEditing):
    DEFAULT_OCTAVE = 4
    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, value):
        self.status_time = time.monotonic()
        self._status = value

    def __init__(self, song=None):
        self.song = song or Song()
        self.saved = deepcopy(self.song)
        self.history = History()
        self.pattern_id = self.song.orders[0]
        self.order = self.row = self.voice = self.column = 0
        self.octave = self.DEFAULT_OCTAVE
        self.instrument = min(self.song.instruments, default=1)
        self.skip = 1
        self.anchor = None
        self.selection_end = None
        self.clipboard = None
        self.clipboard_fields = None
        self.last_cell = Cell(48, 1)
        self.stored_pattern = None
        self.centered = True
        self.highlight = True
        self.pattern_grid = PatternGrid()
        self.edit_mask = {"note", "instrument"}
        self.status = "Ready. F1 help | Caps Lock: audition without writing"

    def set_song_loop(self, enabled=None):
        """One undoable project flag shared by preview and SID/PRG export."""
        current = self.song.export_config.get("loop", True)
        if enabled is not None and type(enabled) is not bool:
            raise ValueError("Song loop must be true or false")
        value = not current if enabled is None else enabled
        if value != current:
            config = deepcopy(self.song.export_config)
            config["loop"] = value
            self.edit("Enable song loop" if value else "Disable song loop",
                      [(("export_config",), config)])
        self.status = ("Song loop ON: restart at order 000 when the playlist ends."
                       if value else "Song loop OFF: stop after the last playlist entry.")
        return value

    @property
    def pattern(self):
        return self.song.patterns[self.pattern_id]

    @property
    def dirty(self):
        return self.song != self.saved

    @property
    def cell(self):
        return self.pattern.rows[self.row][self.voice]

    def cell_path(self, row=None, voice=None):
        return ("patterns", self.pattern_id, "rows", self.row if row is None else row, self.voice if voice is None else voice)

    def mark_saved(self):
        self.saved = deepcopy(self.song)

    def repair_cursor(self):
        if self.pattern_id not in self.song.patterns:
            self.pattern_id = min(self.song.patterns)
        self.row = min(self.row, len(self.pattern.rows) - 1)
        self.order = min(self.order, len(self.song.orders) - 1)
        if self.instrument not in self.song.instruments:
            self.instrument = min(self.song.instruments, default=1)

    def edit(self, name, updates):
        changed = self.history.apply(self.song, name, updates)
        if changed:
            self.status = name
        self.repair_cursor()
        return changed

    def move(self, rows=0, columns=0, select=False):
        if select and (self.anchor is None or len(self.anchor) != 3):
            self.anchor = (self.row, self.voice, self.column)
        self.row = max(0, min(len(self.pattern.rows) - 1, self.row + rows))
        position = max(0, min(3 * len(FIELDS) - 1, self.voice * len(FIELDS) + self.column + columns))
        self.voice, self.column = divmod(position, len(FIELDS))
        if select:
            self.selection_end = (self.row, self.voice, self.column)

    def advance(self):
        self.row = (self.row + self.skip) % len(self.pattern.rows)

    def enter_note(self, note):
        cell = replace(self.cell, note=note)
        if note >= 0 and "instrument" in self.edit_mask:
            cell.instrument = self.instrument
        if note >= 0 and "effect" in self.edit_mask:
            cell.effect, cell.parameter = self.last_cell.effect, self.last_cell.parameter
        if note >= 0 and "pulse_width" in self.edit_mask:
            cell.pulse_width = self.last_cell.pulse_width
        for field in (*ENVELOPE_FIELDS, 'arp_mode', 'waveform'):
            if note >= 0 and field in self.edit_mask:
                setattr(cell, field, getattr(self.last_cell, field))
        self.edit("Set note", [(self.cell_path(), cell)])
        self.last_cell = deepcopy(cell)
        self.advance()

    @staticmethod
    def effect_edit_label(kind, cell):
        code = f"{cell.effect}{cell.parameter or 0:02X}" if cell.effect else "(no effect)"
        state = "" if supported(cell.effect, cell.parameter or 0) else " (stored; unsupported in playback/export)"
        return f"Set {kind} {code}{state}"

    def reset_automation(self, selection=False):
        r0, r1, v0, v1 = self.bounds() if selection else (self.row, self.row, self.voice, self.voice)
        updates = [(self.cell_path(row, voice) + (field,), -1)
                   for row in range(r0, r1+1) for voice in range(v0, v1+1)
                   for field in (*ENVELOPE_FIELDS, 'pulse_width')]
        self.edit('Reset all A D S R PW to instrument defaults', updates)
        if not selection:
            self.last_cell = deepcopy(self.cell)
        self.status = f'Reset all A D S R PW: {r1-r0+1} row(s), CH {v0+1}' + (f'..{v1+1}' if v1 != v0 else '')

    def enter_digit(self, char):
        field = FIELDS[self.column]
        cell = deepcopy(self.cell)
        if field == 'waveform':
            from sidpulse.song.model import WAVEFORM_KEYS, WAVEFORM_LABELS
            value = WAVEFORM_KEYS.get(char.upper())
            if value is not None:
                cell.waveform = value
                self.edit('Set row waveform ' + WAVEFORM_LABELS[value], [(self.cell_path(), cell)])
                self.last_cell = deepcopy(cell)
                self.advance()
        elif field == 'arp_mode':
            if len(char)==1 and char.upper() in '01R':
                cell.arp_mode={'0':0,'1':1,'R':-1}[char.upper()]
                label={0:'OFF',1:'ON',-1:'instrument setting'}[cell.arp_mode]
                self.edit('Set row arpeggio '+label,[(self.cell_path(),cell)])
                self.last_cell=deepcopy(cell)
                self.advance()
        elif field == "pulse_width" and len(char) == 1 and char.upper() in "0123456789ABCDEFR":
            if char.upper() == 'R':
                cell.pulse_width = -1
            else:
                shift = (FIELDS.index("pulse_width") + 2 - self.column) * 4
                old = max(0, cell.pulse_width or 0)
                cell.pulse_width = (old & ~(15 << shift)) | (int(char, 16) << shift)
            self.edit("Set row pulse width", [(self.cell_path(), cell)])
            self.last_cell = deepcopy(cell)
            if char.upper() == 'R' or self.column == FIELDS.index('pulse_width') + 2:
                self.column = FIELDS.index('pulse_width')
                self.advance()
            else:
                self.column += 1
        elif field in ENVELOPE_FIELDS and len(char) == 1 and char.upper() in '0123456789ABCDEFR':
            setattr(cell, field, -1 if char.upper() == 'R' else int(char, 16))
            self.edit('Set row ' + field, [(self.cell_path(), cell)])
            self.last_cell = deepcopy(cell)
            self.advance()
        elif self.column == 1 and len(char) == 1 and char in "0123456789":
            if char not in "01234567":
                self.status = "Note octave must be 0..7; note unchanged"
            elif cell.note is None or cell.note < 0:
                self.status = "Enter a pitched note before changing its octave"
            else:
                cell.note = cell.note % 12 + 12 * int(char)
                self.edit("Set note octave", [(self.cell_path(), cell)])
                self.last_cell = deepcopy(cell)
                self.advance()
        elif field == "instrument" and char in "0123456789" and char:
            old = cell.instrument or 0
            number = int(char) * 10 + old % 10 if self.column == 2 else old // 10 * 10 + int(char)
            updates = []
            if number and number not in self.song.instruments:
                instruments = deepcopy(self.song.instruments)
                instruments[number] = Instrument(name=f"Instrument {number:02d}")
                updates.append((("instruments",), instruments))
            cell.instrument = number or None
            updates.append((self.cell_path(), cell))
            self.edit("Set instrument number", updates)
            if number:
                self.instrument = number
            if self.column == 2:
                self.column = 3
            else:
                self.column = 2
                self.advance()
        elif field == "parameter" and char and char.upper() in "0123456789ABCDEF":
            old = cell.parameter or 0
            nibble = int(char, 16)
            first = FIELDS.index('parameter')
            cell.parameter = nibble * 16 + (old & 15) if self.column == first else (old & 240) + nibble
            self.edit(self.effect_edit_label("effect parameter", cell), [(self.cell_path(), cell)])
            if self.column == first:
                self.column += 1
            else:
                self.column = first
                self.advance()
        elif field == "effect" and len(char) == 1 and "A" <= char.upper() <= "Z":
            cell.effect = char.upper()
            self.edit(self.effect_edit_label("effect", cell), [(self.cell_path(), cell)])
            self.advance()

    def clear_field(self):
        field = FIELDS[self.column]
        if field == "expression":
            return
        cell = replace(self.cell, **{field: "" if field == "effect" else None})
        self.edit("Clear field", [(self.cell_path(), cell)])
        self.advance()

    def repeat_field(self):
        field = FIELDS[self.column]
        if field == "expression":
            return
        value = self.instrument if field == "instrument" else getattr(self.last_cell, field)
        self.edit("Repeat last field", [(self.cell_path(), replace(self.cell, **{field: value}))])
        self.advance()

    def insert_delete(self, delete=False, entire=False):
        rows = deepcopy(self.pattern.rows)
        for voice in range(3) if entire else (self.voice,):
            lane = [row[voice] for row in rows]
            if delete:
                lane.pop(self.row)
                lane.append(Cell())
            else:
                lane.insert(self.row, Cell())
                lane.pop()
            for i, cell in enumerate(lane):
                rows[i][voice] = cell
        updates=[(("patterns", self.pattern_id, "rows"), rows)]
        if entire:
            controls={}
            for r,c in self.pattern.controls.items():
                if delete and r==self.row:continue
                dest=r+(-1 if delete else 1) if r>=self.row else r
                if dest<len(rows):controls[dest]=deepcopy(c)
            updates.append((("patterns",self.pattern_id,"controls"),controls))
        self.edit("Delete row" if delete else "Insert row", updates)

    def select_pattern(self, number):
        number = max(0, min(255, number))
        if number not in self.song.patterns:
            patterns = deepcopy(self.song.patterns)
            patterns[number] = Pattern()
            self.edit("Create pattern", [(("patterns",), patterns)])
        self.pattern_id = number
        self.row = min(self.row, len(self.pattern.rows) - 1)
        self.anchor = self.selection_end = None

    def select_instrument(self, delta):
        numbers = sorted(self.song.instruments)
        self.instrument = numbers[max(0, min(len(numbers) - 1, numbers.index(self.instrument) + delta))]

    def order_edit(self, action, number=None):
        orders = self.song.orders.copy()
        updates = []
        if action in ("insert", "new", "clone"):
            if len(orders) == 256:
                self.status = "Order limit: 256"
                return
            if action in ("new", "clone"):
                free = next((i for i in range(256) if i not in self.song.patterns), None)
                if free is None:
                    self.status = "Pattern limit: 256"
                    return
                patterns = deepcopy(self.song.patterns)
                patterns[free] = deepcopy(self.song.patterns[orders[self.order]]) if action == "clone" else Pattern()
                updates.append((("patterns",), patterns))
                number = free
            orders.insert(self.order, self.pattern_id if number is None else number)
        elif action == "delete" and len(orders) > 1:
            orders.pop(self.order)
        elif action == "set":
            if number not in self.song.patterns:
                patterns = deepcopy(self.song.patterns)
                patterns[number] = Pattern()
                updates.append((("patterns",), patterns))
            orders[self.order] = number
        updates.append((("orders",), orders))
        self.edit(f"Order {action}", updates)
        self.select_pattern(orders[self.order])
