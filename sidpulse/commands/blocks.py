"""Field-aware pattern selection and undoable clipboard operations.

Two-part anchors retain legacy whole-voice blocks. Three-part anchors include
cursor columns; whole musical fields are copied, never individual hex digits.
"""
from copy import deepcopy
from dataclasses import replace

from sidpulse.song.model import Cell
from sidpulse.commands.pattern_fields import FIELDS, FIELD_GROUPS, AUTOMATION_FIELDS, group_for_column


class BlockEditing:
    def bounds(self):
        a = self.anchor or (self.row, self.voice)
        b = self.selection_end or (self.row, self.voice)
        last = len(self.pattern.rows)-1
        return min(last,min(a[0], b[0])), min(last,max(a[0], b[0])), min(a[1], b[1]), max(a[1], b[1])

    def selected_fields(self, voice):
        if self.anchor is None or len(self.anchor) == 2:
            return None  # all cell data, including future extension fields
        a = self.anchor
        b = self.selection_end or (self.row, self.voice, self.column)
        if len(b) == 2:
            return None
        lo, hi = sorted((a[1]*len(FIELDS)+a[2], b[1]*len(FIELDS)+b[2]))
        return frozenset(field for _, columns, fields in FIELD_GROUPS
                         if any(lo <= voice*len(FIELDS)+column <= hi for column in columns)
                         for field in fields)

    def selection_description(self):
        if self.anchor is None:
            return 'No selection'
        r0, r1, v0, v1 = self.bounds()
        parts = []
        for voice in range(v0, v1+1):
            fields = self.selected_fields(voice)
            label = 'all fields' if fields is None else ' '.join(
                name for name, _, group in FIELD_GROUPS if set(group) & fields) or 'EX (reserved)'
            parts.append(f'CH {voice+1}: {label}')
        return f'{r1-r0+1} rows | ' + ' / '.join(parts)

    def select_field(self, voice, column):
        columns = group_for_column(column)[1]
        self.anchor = (0, voice, columns[0])
        self.selection_end = (len(self.pattern.rows)-1, voice, columns[-1])
        self.voice, self.column = voice, column
        self.status = 'Selected ' + self.selection_description()

    def mark(self, kind):
        if kind == 'start':
            self.anchor = self.selection_end = (self.row, self.voice)
        elif kind == 'end':
            self.anchor = self.anchor[:2] if self.anchor else (self.row, self.voice)
            self.selection_end = (self.row, self.voice)
        elif kind == 'all':
            if (self.anchor is not None and len(self.anchor) == 2 and
                    self.bounds() == (0, len(self.pattern.rows)-1, self.voice, self.voice)):
                self.anchor, self.selection_end = (0, 0), (len(self.pattern.rows)-1, 2)
            else:
                self.anchor, self.selection_end = (0, self.voice), (len(self.pattern.rows)-1, self.voice)
        elif kind == 'clear':
            self.anchor = self.selection_end = self.clipboard = self.clipboard_fields = None

    def copy(self, cut=False):
        r0, r1, v0, v1 = self.bounds()
        masks = tuple(self.selected_fields(v) for v in range(v0, v1+1))
        if not any(mask is None or mask for mask in masks):
            self.status = 'EX is reserved; nothing copied'
            return False
        self.clipboard_fields = masks
        self.clipboard = []
        updates = []
        for row in range(r0, r1+1):
            copied = []
            for voice, mask in zip(range(v0, v1+1), masks):
                source = self.pattern.rows[row][voice]
                cell = deepcopy(source) if mask is None else Cell(**{
                    name: deepcopy(getattr(source, name)) for name in mask})
                copied.append(cell)
                if cut:
                    cleared = Cell() if mask is None else replace(source, **{
                        name: deepcopy(getattr(Cell(), name)) for name in mask})
                    updates.append((self.cell_path(row, voice), cleared))
            self.clipboard.append(copied)
        if cut:
            self.edit('Cut selected fields', updates)
        label = self.selection_description() if self.anchor is not None else 'current cell (all fields)'
        self.status = ('Cut ' if cut else 'Copied ') + label
        return True

    def paste(self, mode='overwrite', scope=None):
        if not self.clipboard:
            self.status = 'Clipboard is empty; select fields, then Alt+C'
            return False
        if mode not in ('overwrite', 'insert', 'mix'):
            raise ValueError('Unknown paste mode')
        automation = AUTOMATION_FIELDS | {'arp_mode'}
        scopes = {None: None, 'notes': frozenset(('note',)), 'automation': automation,
                  'both': automation | {'note'}}
        if scope not in scopes:
            raise ValueError('Unknown paste scope')
        masks = self.clipboard_fields or (None,)*len(self.clipboard[0])
        if scopes[scope] is not None:
            masks = tuple(scopes[scope] if mask is None else mask & scopes[scope] for mask in masks)
        if not any(mask is None or mask for mask in masks[:3-self.voice]):
            self.status = 'The clipboard has no fields matching that paste choice'
            return False
        rows = deepcopy(self.pattern.rows)
        if mode == 'insert':
            count = len(self.clipboard)
            for dv, mask in enumerate(masks[:3-self.voice]):
                voice = self.voice+dv
                for r in range(len(rows)-1, self.row-1, -1):
                    source = self.pattern.rows[r-count][voice] if r-count >= self.row else Cell()
                    if mask is None:
                        rows[r][voice] = deepcopy(source)
                    else:
                        for field in mask:
                            setattr(rows[r][voice], field, deepcopy(getattr(source, field)))
        empty = Cell()
        for dr, row in enumerate(self.clipboard):
            for dv, source in enumerate(row):
                r, v = self.row+dr, self.voice+dv
                if r >= len(rows) or v >= 3:
                    continue
                target, mask = rows[r][v], masks[dv]
                if mask is None:
                    if mode != 'mix' or target == empty:
                        rows[r][v] = deepcopy(source)
                else:
                    for _, _, fields in FIELD_GROUPS:
                        selected = set(fields) & mask
                        if selected and (mode != 'mix' or all(getattr(target, f) == getattr(empty, f) for f in fields)):
                            for field in selected:
                                setattr(target, field, deepcopy(getattr(source, field)))
        self.edit(f'Paste {scope or "selected fields"} ({mode})', [(("patterns", self.pattern_id, "rows"), rows)])
        return True

    def transpose(self, amount):
        r0, r1, v0, v1 = self.bounds()
        updates = []
        for r in range(r0, r1+1):
            for v in range(v0, v1+1):
                fields = self.selected_fields(v)
                cell = self.pattern.rows[r][v]
                if (fields is None or 'note' in fields) and cell.note is not None and cell.note >= 0:
                    updates.append((self.cell_path(r,v), replace(cell, note=max(0,min(95,cell.note+amount)))))
        self.edit('Transpose block', updates)

    def roll(self, amount):
        r0, r1, v0, v1 = self.bounds()
        rows = deepcopy(self.pattern.rows)
        for v in range(v0, v1+1):
            mask = self.selected_fields(v)
            lane = deepcopy([rows[r][v] for r in range(r0,r1+1)])
            lane = lane[-1:]+lane[:-1] if amount > 0 else lane[1:]+lane[:1]
            for r, source in zip(range(r0,r1+1), lane):
                if mask is None:
                    rows[r][v] = source
                else:
                    for field in mask:
                        setattr(rows[r][v], field, deepcopy(getattr(source,field)))
        self.edit('Roll selected fields', [(("patterns",self.pattern_id,"rows"),rows)])

    def set_block_instrument(self):
        r0,r1,v0,v1 = self.bounds()
        self.edit('Set block instrument', [(self.cell_path(r,v), replace(self.pattern.rows[r][v], instrument=self.instrument))
                  for r in range(r0,r1+1) for v in range(v0,v1+1)
                  if self.selected_fields(v) is None or 'instrument' in self.selected_fields(v)])
