"""Mouse field selection and the optional pattern clipboard controls."""
import time
import pygame as pg

from sidpulse.commands.pattern_fields import FIELDS, COLUMN_OFFSETS
from sidpulse.preferences import save_preferences


class PatternClipboardActions:
    def clipboard_feedback(self, message, error=False):
        self.clipboard_notice = (message, time.monotonic() + 2.5, error)

    def copy_fields(self, cut=False, confirmed=False):
        if cut and self.confirm_cut and not confirmed:
            from sidpulse.ui.edit_confirmation import open_dialog
            open_dialog(self, 'cut')
            return
        if self.editor.copy(cut):
            self.clipboard_feedback('Cut to clipboard' if cut else 'Copied to clipboard')
        else:
            self.clipboard_feedback(self.editor.status, True)

    def paste_fields(self, mode='overwrite', scope=None):
        if self.editor.paste(mode, scope):
            self.clipboard_feedback('Pasted from clipboard')
        else:
            self.clipboard_feedback('Clipboard is empty' if not self.editor.clipboard else 'No matching fields to paste', True)

    def open_keyboard_mapping(self):
        self.release_audition()
        self.dialog = {'kind':'keyboard_mapping', 'title':'Keyboard mapping',
            'message':f'Current: {self.keyboard_mapping.title()}. Modern: F2 Ctrl+Insert copies, Shift+Insert pastes. '
                      'F3/F4 + and - change octave; 0 resets to octave 4. '
                      'Classic keeps the existing tracker shortcuts, including Ctrl+Insert to roll. '
                      'Alt+C / Alt+O and the octave buttons work in either mode.',
            'button_focus':0 if self.keyboard_mapping == 'modern' else 1}

    def set_keyboard_mapping(self, mapping):
        if mapping not in ('modern','classic'):
            raise ValueError('Choose Modern or Classic keyboard mapping')
        save_preferences({'keyboard_mapping':mapping})
        self.release_audition()
        self.keyboard_mapping = mapping
        self.dialog = None
        self.editor.status = 'Keyboard mapping: ' + mapping.title()

    def begin_pattern_selection(self, value, pos, extend=False):
        ed = self.editor
        before = (ed.row, ed.voice, ed.column)
        self.control_focus = False
        self.follow_playback = False
        ed.row, ed.voice, ed.column = value
        if extend:
            if ed.anchor is None or len(ed.anchor) != 3:
                ed.anchor = before
            ed.selection_end = value
        else:
            ed.anchor = ed.selection_end = None
        self.pattern_drag = {'origin': ed.anchor if extend else value, 'pos': pos,
                             'start_pos': pos, 'active': extend, 'scroll_time': 0.0}

    def pattern_position(self, pos):
        grid = self.renderer.pattern_geometry
        x, y = pos
        voices = grid['voices']
        voice, left, width = min(voices, key=lambda item: max(item[1]-x, x-(item[1]+item[2]), 0))
        offset = (x-left)/self.renderer.cw
        column = min(range(len(FIELDS)), key=lambda i: abs(offset-(COLUMN_OFFSETS[i]+(.8 if i == 0 else .5))))
        row = self.renderer.top_row + int((y-grid['top'])//self.renderer.rh)
        row = max(self.renderer.top_row, min(row, grid['last_row']))
        return row, voice, column

    def update_pattern_selection(self, pos=None, scroll=False):
        drag = self.pattern_drag
        if not drag or self.page != 'pattern' or self.dialog or self.menu_path:
            return
        if pos is not None:
            drag['pos'] = pos
        pos = drag['pos']
        if not drag['active']:
            if max(abs(a-b) for a,b in zip(pos,drag['start_pos'])) < 3:
                return
            drag['active'] = True
        target = self.pattern_position(pos)
        grid = self.renderer.pattern_geometry
        if scroll and time.monotonic() - drag['scroll_time'] >= .08:
            row, voice, column = target
            if pos[1] <= grid['top']+3:
                row = max(0,self.renderer.top_row-1)
            elif pos[1] >= grid['bottom']-3:
                row = min(len(self.editor.pattern.rows)-1,grid['last_row']+1)
            if pos[0] <= grid['left']+3 and grid['voices'][0][0] > 0:
                voice,column = grid['voices'][0][0]-1,0
            elif pos[0] >= grid['right']-3 and grid['voices'][-1][0] < 2:
                voice,column = grid['voices'][-1][0]+1,len(FIELDS)-1
            target = row,voice,column
            drag['scroll_time'] = time.monotonic()
        self.editor.anchor = drag['origin']
        self.editor.selection_end = target
        self.editor.row,self.editor.voice,self.editor.column = target

    def finish_pattern_selection(self):
        if self.pattern_drag and self.pattern_drag['active']:
            self.editor.status = 'Selected ' + self.editor.selection_description()
        self.pattern_drag = None

    def open_paste_special(self):
        if not self.editor.clipboard:
            self.editor.status = 'Clipboard is empty; select fields, then Alt+C'
            self.clipboard_feedback('Clipboard is empty', True)
            return
        self.dialog = {'kind':'paste_special', 'title':'Paste Special',
                       'message':'Paste at the current row and channel. Notes changes NOTE only. Automation changes AR W and A D S R PW. '
                                 'Both combines these; IN and FX stay intact. Only fields actually copied are available. '
                                 'Ordinary Paste uses all copied fields.', 'button_focus':0}

    def toggle_pattern_clipboard_buttons(self):
        value = not self.pattern_clipboard_buttons
        save_preferences({'pattern_clipboard_buttons':value})
        self.pattern_clipboard_buttons = value
        self.editor.status = 'Pattern clipboard buttons: ' + ('ON' if value else 'OFF')

    def toggle_confirm_cut(self):
        value = not self.confirm_cut
        save_preferences({'confirm_cut': value})
        self.confirm_cut = value
        self.editor.status = 'Confirm before Cut: ' + ('ON' if value else 'OFF')

    def toggle_control_panel(self):
        value = not getattr(self.renderer, "control_visible", self.control_panel_visible if self.control_panel_visible is not None else True)
        save_preferences({"control_panel_visible":value})
        self.control_panel_visible = value
        if not value:
            self.control_focus = False
        self.editor.status = "CTRL CH / FILTER: " + ("shown" if value else "collapsed; automation keeps playing")

    def toggle_channel_visualizers(self):
        value = not self.channel_visualizers
        save_preferences({"channel_visualizers":value})
        self.channel_visualizers = value
        self.sync_audio()
        self.editor.status = "Channel visualizers: " + ("ON in playback Info" if value else "OFF; display-only SID scopes disabled")
