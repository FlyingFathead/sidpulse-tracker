from sidpulse.ui.instrument_graphs import button, button_frame, draw_adsr, draw_envelope, draw_roll, draw_fields
from sidpulse.ui.pressable import pressed
from sidpulse.ui.instruments import FIELDS as INSTRUMENT_FIELDS, LABELS as INSTRUMENT_LABELS, display
"""The tracker draws its own cells, panels, selections and dialogs.

Fonts are rasterized at the requested size. No fixed framebuffer is enlarged.
"""
from dataclasses import dataclass
from collections import OrderedDict
from pathlib import Path
import textwrap
import time
import pygame as pg

from sidpulse import __version__
from sidpulse.song.model import note_name, ENVELOPE_FIELDS
from sidpulse.ui.menus import menu_items
from sidpulse.ui.registry import help_entries, available, reason
from sidpulse.ui.effects import STATUS, visible_effects, lookup_effect
from sidpulse.commands.pattern_fields import COLUMN_OFFSETS, CURSOR_HINTS, FIELDS as PATTERN_FIELDS, FIELD_GROUPS, group_span
from sidpulse.song.model import WAVEFORM_LABELS

BG = (176, 146, 119)
PANEL = (176, 146, 119)
EDGE = (113, 82, 64)
TEXT = (12, 10, 8)
DIM = (100, 75, 55)
ACCENT = (50, 145, 58)
YELLOW = (245, 244, 80)
CYAN = (20, 16, 12)
PURPLE = (184, 123, 197)
CURSOR = (234, 234, 198)
SELECT = (86, 64, 58)
WELL = (0, 0, 0)
CREAM = (233, 232, 200)
WAVES = {16: "TRIANGLE", 32: "SAW", 64: "PULSE", 128: "NOISE"}

HELP_TOPIC_NAMES = ("All", "Patterns", "Instruments", "Samples", "Files", "Audio", "Display", "Shortcuts", "Effects")


@dataclass
class Layout:
    width: int
    height: int
    zoom: float

    def __post_init__(self):
        fit = min(1.0, self.width / 1000, self.height / 640)
        self.font_size = max(10, round(16 * fit * self.zoom))


class Renderer:
    def __init__(self):
        self.signature = None
        self.font = None
        self.hits = []
        self.text_cache = OrderedDict()
        self.cell_cache = OrderedDict()
        self.bank_button_cache = OrderedDict()
        self.button_cache = OrderedDict()
        self.pattern_hit_cache = None
        self.dirty_display_cache = None
        self.page_layout_cache = None
        self.logo_cache = {}
        self.welcome_font_cache = {}
        from sidpulse.ui.scrollbar import Scrollbars
        self.scrollbars = Scrollbars()
        self.top_row = 0
        self.first_voice = 0
        from sidpulse.ui.activity import ActivityLights
        self.activity_lights = ActivityLights()
        self.instrument_levels = {}

    def configure(self, screen, zoom, appearance=None):
        from sidpulse.preferences import APPEARANCE
        self.appearance=appearance or APPEARANCE
        from sidpulse.ui.themes import palette
        from sidpulse.ui import instrument_graphs
        colors=palette(self.appearance);globals().update(colors)
        instrument_graphs.apply_palette(colors)
        self.slider_color=colors['SLIDER'];self.scope_color=colors['SCOPE']
        signature = (*screen.get_size(), zoom, repr(self.appearance))
        if self.signature != signature:
            self.signature = signature
            self.text_cache.clear()
            self.cell_cache.clear()
            self.bank_button_cache.clear()
            self.button_cache.clear()
            self.logo_cache.clear()
            self.welcome_font_cache.clear()
            self.layout = Layout(*screen.get_size(), zoom*self.appearance["font_size"]/16)
            from sidpulse.ui.fonts import default_font_path
            font_path = default_font_path()
            custom=self.appearance.get('font_file')
            if custom:
                try:pg.font.Font(str(Path(custom).expanduser()),16);font_path=str(Path(custom).expanduser())
                except (OSError,pg.error):pass
            self.font = pg.font.Font(font_path, self.layout.font_size)
            self.font.set_bold(self.appearance['font_bold'])
            self.small_font = pg.font.Font(font_path, max(12, round(self.layout.font_size * .8)))
            self.small_font.set_bold(self.appearance['font_bold'])
            self.cw = self.font.size("M")[0]
            self.rh = self.font.get_linesize() + max(2, self.layout.font_size // 5)
        self.screen = screen
        self.cols = max(1, screen.get_width() // self.cw)
        self.lines = max(1, screen.get_height() // self.rh)
        self.hits = []

    def text(self, x, y, value, color=None, maxchars=None):
        color=TEXT if color is None else color
        value = str(value)
        available = max(0, self.cols - int(x)) if maxchars is None else max(0, int(maxchars))
        if len(value) > available:
            value = value[:max(0, available - 1)] + ("…" if available else "")
        if value:
            key = (value, color)
            surface = self.text_cache.get(key)
            if surface is None:
                surface = self.font.render(value, True, color)
                self.text_cache[key] = surface
                if len(self.text_cache) > 1024:
                    self.text_cache.popitem(last=False)
            else:
                self.text_cache.move_to_end(key)
            self.screen.blit(surface, (round(x * self.cw), round(y * self.rh)))

    def rect(self, x, y, w, h, color, outline=False):
        rect = pg.Rect(round(x * self.cw), round(y * self.rh), round(w * self.cw), round(h * self.rh))
        pg.draw.rect(self.screen, color, rect, 1 if outline else 0)
        return rect

    def control_text(self, rect, value, color, align="center", padding=None):
        """Center visible glyphs in a control, excluding font baseline padding."""
        padding = max(3, self.cw // 2) if padding is None else padding
        padding = max(2, padding)
        available = max(0, rect.width - 2 * padding)
        value = str(value)
        if self.font.size(value)[0] > available:
            while value and self.font.size(value + '…')[0] > available:
                value = value[:-1]
            value = value + '…' if value else ''
        if not value:
            return
        key = ('control', value, color)
        glyph = self.text_cache.get(key)
        if glyph is None:
            rendered = self.font.render(value, True, color)
            glyph = rendered.subsurface(rendered.get_bounding_rect()).copy()
            self.text_cache[key] = glyph
            if len(self.text_cache) > 1024:
                self.text_cache.popitem(last=False)
        else:
            self.text_cache.move_to_end(key)
        clip = self.screen.get_clip()
        self.screen.set_clip(clip.clip(rect.inflate(-4, -4)))
        target = glyph.get_rect(center=rect.center)
        if align == "left":
            target.left = rect.left + padding
        self.screen.blit(glyph, target)
        self.screen.set_clip(clip)

    def panel(self, x, y, w, h, title=""):
        self.rect(x, y, w, h, PANEL)
        self.rect(x, y, w, h, EDGE, True)
        if title:
            self.text(x + 1, y, title, CYAN, w - 2)

    def header_field(self, x, y, w, value, color, centered=False):
        rect = self.well(x, y, w, 1)
        self.control_text(rect, value, color, align="center" if centered else "left",
                          padding=max(4, round(self.cw * .65)))

    def horizontal_rule(self, row):
        y = round(row * self.rh)
        pg.draw.line(self.screen, EDGE, (self.cw, y), (self.screen.get_width() - self.cw, y))
        pg.draw.line(self.screen, CREAM, (self.cw, y + 1), (self.screen.get_width() - self.cw, y + 1))

    def well(self, x, y, w, h):
        rect = self.rect(x, y, w, h, WELL)
        pg.draw.line(self.screen, EDGE, rect.topleft, rect.topright, 2)
        pg.draw.line(self.screen, EDGE, rect.topleft, rect.bottomleft, 2)
        pg.draw.line(self.screen, CREAM, rect.bottomleft, rect.bottomright, 2)
        pg.draw.line(self.screen, CREAM, rect.topright, rect.bottomright, 2)
        return rect

    def meter(self, audio, x, y, w, h):
        rect = self.well(x, y, w, h)
        inner = rect.inflate(-6, -6)
        old_clip = self.screen.get_clip()
        self.screen.set_clip(inner)
        waveform = audio.waveform
        mid = inner.centery - inner.height * .1
        points = [(inner.x + i * inner.width / max(1, len(waveform) - 1), mid - sample * inner.height * .7) for i, sample in enumerate(waveform)]
        if len(points) > 1:
            pg.draw.lines(self.screen, self.scope_color, False, points, 1)
        bar = pg.Rect(inner.x, inner.bottom - 4, int(inner.width * audio.rms * 2), 3)
        pg.draw.rect(self.screen, ACCENT if audio.peak < .95 else (220, 50, 45), bar)
        self.screen.set_clip(old_clip)

    def hit(self, x, y, w, h, action, value=None):
        self.hits.append((pg.Rect(round(x * self.cw), round(y * self.rh), round(w * self.cw), round(h * self.rh)), action, value))

    def configure_page(self, app):
        key = (app.screen.get_size(), app.zoom, repr(app.appearance), app.page,
               app.control_panel_visible, app.control_focus if app.page == 'pattern' else False,
               app.inline_recording_visible)
        if self.page_layout_cache and self.page_layout_cache[0] == key:
            _, zoom, self.control_visible = self.page_layout_cache
            self.configure(app.screen, zoom, app.appearance)
            return
        self.configure(app.screen, app.zoom, app.appearance)
        # File fields/buttons must remain reachable even at large tracker zoom.
        # Fit this page only; do not mutate the saved zoom or audio/song state.
        if app.page == "files" and (self.cols < 64 or self.lines < 24):
            fit = min(1.0, self.cols / 64, self.lines / 24) * .92
            self.configure(app.screen, app.zoom * fit, app.appearance)
        if app.page in ('instrument','samples') and (self.cols < 40 or self.lines < 18):
            fit = min(1.0, self.cols / 40, self.lines / 18) * .92
            self.configure(app.screen, app.zoom * fit, app.appearance)
        if app.page=='samples' and self.lines<38:
            self.configure(app.screen,self.signature[2]*self.lines/38*.92,app.appearance)
        if app.inline_recording_visible:
            # Fit the complete control pane above the footer at high zoom.
            # A smaller font can cross into the full-header layout, so recalc.
            for _ in range(3):
                required = 28 if self.cols >= 80 else 21
                if self.lines >= required:break
                self.configure(app.screen,self.signature[2]*self.lines/required*.92,app.appearance)
        self.control_visible = (app.control_panel_visible if app.control_panel_visible is not None else self.cols >= 116)
        if app.page == 'pattern' and app.control_focus:
            self.control_visible = True
        if app.page in ("pattern", "info"):
            # Keep the requested font size when at least one voice fits.
            # The grid already follows the selected voice horizontally; fitting
            # extra voices here shrinks the entire UI on entry to F2/F5.
            # Retain only the minimum-size fallback for a complete voice.
            overhead = 32 if self.control_visible else 12
            minimum = overhead + 30
            for _ in range(3):
                fit = min(1.0, self.cols / minimum, self.lines / 18)
                if fit >= 1:break
                self.configure(app.screen, self.signature[2] * fit * .96, app.appearance)
        self.page_layout_cache = (key, self.signature[2], self.control_visible)

    def render(self, app):
        self.configure_page(app)
        self.scrollbars.begin(self.scrollbars.context_for(app))
        ed, audio = app.editor, app.audio
        # This is only the title's asterisk. Save/quit/recovery still use the
        # exact Editor.dirty comparison. Commands and drags update revision;
        # the one-second fallback also catches out-of-history model changes.
        dirty_key = (id(ed), id(ed.song), id(ed.saved), ed.history.revision)
        now = time.monotonic()
        if (self.dirty_display_cache is None or self.dirty_display_cache[0] != dirty_key
                or now >= self.dirty_display_cache[2]):
            self.dirty_display_cache = (dirty_key, ed.dirty, now + 1.0)
        display_dirty = self.dirty_display_cache[1]
        playback = audio.playback
        from sidpulse.audio.activity import ActivitySnapshot
        snapshot = getattr(audio, 'activity', ActivitySnapshot()) if audio.ready else ActivitySnapshot()
        self.instrument_levels = self.activity_lights.levels(snapshot)
        self.screen.fill(BG)
        title = f"SIDpulse Tracker {__version__}"
        self.text(max(1, (self.cols - len(title)) / 2), .3, title, TEXT)
        if self.lines < 16:
            self.text(1, 1, f"P{ed.pattern_id:02X} R{ed.row:03d} I{ed.instrument:02d}", TEXT, self.cols - 10)
            self.meter(audio, max(1, self.cols - 9), 0, 8, 2)
            top = 4
        elif (self.cols >= 80 and (app.page != "files" or self.lines >= 32)
              and (app.page != 'samples' or self.lines >= 44)
              and (not app.inline_recording_visible or self.lines >= 28)):
            right = self.cols // 2 + 1
            self.text(2, 2, "Song Name")
            self.header_field(12, 2, right - 14, f"{'*' if display_dirty else ''}{ed.song.title}", YELLOW)
            self.hit(2, 2, right - 4, 1, 'song_title_settings', None)
            self.text(2, 3, "File Name")
            self.header_field(12, 3, right - 14, app.path.name if app.path else "(not saved)", CREAM)
            self.text(6, 4, "Order")
            self.text(6, 5, "Pattern")
            self.text(6, 6, "Row")
            for row, label in [(4, f"{ed.order:03d}/{len(ed.song.orders) - 1:03d}"), (5, f"{ed.pattern_id:03d}/{max(ed.song.patterns):03d}"), (6, f"{ed.row:03d}/{len(ed.pattern.rows)-1:03d}")]:
                self.header_field(14, row, 9, label, YELLOW, centered=True)
            self.text(25, 5, "F1..Help  F9..Load", TEXT, right - 26)
            self.text(25, 6, "Esc.Main  F10.Save", TEXT, right - 26)
            inst = ed.song.instruments.get(ed.instrument)
            self.text(right, 2, "Instrument")
            self.header_field(right + 11, 2, self.cols - right - 13,
                              f"{app.instrument_slot:02d} (empty slot)" if app.page=="instrument" and app.instrument_slot not in ed.song.instruments else f"{ed.instrument:02d} {inst.name}" if inst else "(empty instrument bank)", YELLOW)
            self.hit(right, 2, self.cols - right - 2, 1, 'header_instrument',
                     app.instrument_slot if app.page == 'instrument' else ed.instrument)
            self.text(right, 3, f"Speed/Tempo {playback.speed if playback.status != 'stopped' else ed.song.speed:03d}/{playback.tempo if playback.status != 'stopped' else ed.song.tempo:03d}   SID {ed.song.sid_model} {ed.song.clock}")
            self.octave_controls(app, right, 4)
            self.text(right + 25, 4, f"Skip {ed.skip}")
            self.text(right, 5, f"UI zoom    {app.zoom:.0%}")
            self.meter(audio, self.cols - 22, 5, 20, 2.5)
            status = (f"{playback.status.title()} {playback.mode}  Order {playback.order:03d}  Pattern {playback.pattern:02X}  Row {playback.row:03d}  Tick {playback.tick:02d}"
                      if playback.status != "stopped" else ("Keyboard jazz" if audio.active else "Stopped"))
            self.order_skip_buttons(app, 2, 7.9)
            if playback.status != 'stopped' and len(status) > self.cols - 34:
                status = (f'{playback.status.title()} {playback.mode}  O{playback.order:03d} '
                          f'P{playback.pattern:02X} R{playback.row:03d} T{playback.tick:02d}')
            self.text(9, 8, status, TEXT, self.cols - 34)
            self.text(self.cols - 23, 8, f"Time {playback.frames / 48000:7.2f}s", DIM)
            top = 12
        else:
            self.text(1, 2, f"{'*' if display_dirty else ''}{ed.song.title}", TEXT, self.cols - 14)
            self.hit(1, 2, self.cols - 14, 1, 'song_title_settings', None)
            self.text(1, 3, f"P{ed.pattern_id:02X} R{ed.row:03d} I{ed.instrument:02d} O{ed.octave}", TEXT, self.cols - 14)
            self.hit(10, 3, 3, 1, 'header_instrument', ed.instrument)
            self.octave_controls(app, 1, 4.3)
            self.order_skip_buttons(app, self.cols - 9, 4.3)
            self.meter(audio, max(1, self.cols - 13), 2, 12, 2)
            top = 8
        self.footer_rows = 4 if app.helper_strip else 2
        bottom = self.lines - self.footer_rows
        titles = {"pattern": "Pattern Editor (F2)", "samples": "Sample List (F3)", "instrument": "Instrument List (F4)",
                  "info": "Info Page", "orders": "Order List / Pattern Bank (F11)", "settings": "Song Variables (F12)", "help": "Help", "files": "File Browser"}
        if app.page == "files":
            from sidpulse.ui.file_browser import TITLES
            titles["files"] = TITLES[app.file_mode]
        label = titles.get(app.page, app.page)
        self.rect(1, top - 2, self.cols - 2, .03, EDGE)
        self.rect(max(0, (self.cols - len(label)) / 2 - 1), top - 2.4, len(label) + 2, 1.2, BG)
        self.text(max(1, (self.cols - len(label)) / 2), top - 2.4, label)
        if app.page == "pattern":
            self.pattern(app, top, bottom)
        elif app.page == "instrument":
            self.instrument(app, top, bottom)
            if app.instrument_focus=="buttons":
                targets=app.instrument_buttons()
                app.instrument_button %= len(targets)
                action,value=targets[app.instrument_button]
                for rect,a,v in self.hits:
                    if (a,v)==(action,value):pg.draw.rect(self.screen,YELLOW,rect.inflate(-4,-4),max(1,self.cw//6))
        elif app.page == "orders":
            self.orders(app, top, bottom)
        elif app.page == "settings":
            self.settings(app, top, bottom)
        elif app.page == "samples":
            self.samples(app, top, bottom)
        elif app.page == "files":
            self.files(app, top, bottom)
        elif app.page == "info":
            self.info(app, top, bottom)
        else:
            self.help(app, top, bottom)
        self.rect(0, bottom, self.cols, self.footer_rows, PANEL)
        self.horizontal_rule(bottom)
        notice = app.clipboard_notice
        notice = notice if notice and time.monotonic() < notice[1] else None
        notice_width = min(self.cols - 4, len(notice[0]) + 2) if notice else 0
        notice_x = self.cols - 2 - notice_width
        self.text(1, bottom, self.context_status(app), TEXT, max(0,notice_x-2) if notice else self.cols-2)
        if notice:
            self.rect(notice_x, bottom, notice_width, 1, SELECT)
            self.text(notice_x+1, bottom, notice[0], CREAM, notice_width-2)
        warning = app.audio_underrun_detection and app.audio_warning and time.monotonic() < app.audio_warning_until
        if warning:
            message = app.audio_warning
            if self.cols < 80:
                message = ('Buffer underrun' if message.startswith('Buffer') else 'Late callback') + ' | Alt+F12: audio'
            color = (215, 92, 103) if sum(PANEL) < 384 else (150, 25, 40)
            self.text(1, bottom + 1, message, color, self.cols - 2)
        else:
            self.text(1, bottom + 1, audio.description + (f" | gaps {audio.underruns} | render {audio.render_load:.0%}" if audio.ready else ""), TEXT if audio.ready else DIM, self.cols - 17)
        if self.cols > 40 and not warning:
            self.text(self.cols - 15, bottom + 1, "F8: SILENCE", DIM)
        if app.helper_strip:
            self.horizontal_rule(bottom + 2)
            self.helper(app, bottom + 2)
        if app.dialog:
            self.dialog(app)
        elif app.menu_path:
            self.menu(app)

    def scroll_start(self, key, default, token, total, visible):
        return self.scrollbars.offset(key, default, token, total, visible)

    def scroll_bar(self, key, x, y, height, total, visible):
        width = max(10, min(14, self.cw + 4))
        track = pg.Rect(round(x*self.cw), round(y*self.rh), width, round(height*self.rh))
        self.scrollbars.draw(self, key, track, total, visible, globals())

    def menu(self, app):
        self.hits = []
        self.scrollbars.visible.clear()
        shade = pg.Surface(self.screen.get_size(), pg.SRCALPHA)
        shade.fill((0, 0, 0, 75))
        self.screen.blit(shade, (0, 0))
        # Render the parent and active menu side by side when the viewport permits.
        paths = app.menu_path[-2:] if self.cols >= 88 else app.menu_path[-1:]
        for depth, title in enumerate(paths):
            items = menu_items(title)
            active = depth == len(paths) - 1
            selected = app.menu_indices[-1] if active else app.menu_indices[-2]
            w = min(40, self.cols - 4)
            visible = max(1, min(len(items), int((self.lines - 6) / 1.55)))
            start = max(0, min(selected - visible + 1, len(items) - visible))
            key = 'menu:' + title
            if active:
                start = self.scroll_start(key,start,selected,len(items),visible)
            h = visible * 1.55 + 4
            x = 3 + depth * (w + 2) if len(paths) > 1 else max(1, (self.cols - w) // 2)
            y = max(1, (self.lines - h) // 2)
            self.panel(x, y, w, h, title)
            for i in range(start, start + visible):
                item = items[i]
                iy = y + 2 + (i - start) * 1.55
                color = TEXT if item.enabled else (129, 123, 113)
                # Keep the parent submenu's button latched while its child is open.
                pressed = i == selected
                rect = pg.Rect(round((x+1)*self.cw), round(iy*self.rh),
                               round((w-(4 if len(items)>visible else 2))*self.cw), round(1.3*self.rh))
                button_frame(self, rect, pressed)
                if pressed:
                    color = CREAM if item.enabled else (156, 145, 128)
                label = item.label
                if item.command == 'automation_display_toggle':
                    label = f'Automation display: {app.automation_display} (' + ('inline)' if app.automation_display == 2 else 'window)')
                toggle = {'pattern_clipboard_buttons':app.pattern_clipboard_buttons,
                          'center':app.editor.centered,
                          'instrument_monitor_buttons':app.instrument_monitor_buttons,
                          'confirm_cut_toggle':app.confirm_cut,
                          'channel_visualizers_toggle':app.channel_visualizers,
                          'helper_toggle':app.helper_strip}.get(item.command)
                if toggle is not None:
                    label = label.replace('on / off', 'ON' if toggle else 'OFF')
                self.control_text(rect, label, color)
                if active:
                    self.hits.append((rect, "menu", i))
            if active:
                self.scroll_bar(key,x+w-2.5,y+2,visible*1.55,len(items),visible)
            self.text(x + 2, y + h - 1, "Enter: choose   Esc: back", DIM, w - 4)

    def pattern(self, app, top, bottom):
        ed = app.editor
        compact = self.cols < 76
        controls = []
        if app.pattern_clipboard_buttons:
            controls = [(6,'Cut','pattern_cut','copy',True),
                        (7 if compact else 8,'Copy','pattern_copy','copy',False),
                        (8,'Paste','pattern_paste','paste','overwrite'),
                        (10 if compact else 16,'Special' if compact else 'Paste Special','paste_special','paste_special',None)]
        controls += [(12,'Select all','pattern_select_all','pattern_select_all',None),
                     (12 if compact else 22,'Reset all' if compact else 'Reset all automation','reset_automation','reset_automation',None)]
        wrapped = 7 + sum(w+1 for w,_,_,_,_ in controls) > self.cols-2
        if wrapped:top+=2
        sidebar = 23 if self.control_visible else 3
        grid_end = self.cols - sidebar - 2
        available = max(1, grid_end - 7)
        count = max(1, min(3, available // 30))
        channel_w = max(29, available // count)
        self.first_voice = min(self.first_voice, 3 - count)
        if ed.voice < self.first_voice:
            self.first_voice = ed.voice
        elif ed.voice >= self.first_voice + count:
            self.first_voice = ed.voice - count + 1
        rows_visible = max(1, bottom - top - 2)
        self.top_row = min(self.top_row, max(0, len(ed.pattern.rows) - rows_visible))
        if ed.centered:
            self.top_row = max(0, min(len(ed.pattern.rows) - rows_visible, ed.row - rows_visible // 2))
        elif ed.row < self.top_row:
            self.top_row = ed.row
        elif ed.row >= self.top_row + rows_visible:
            self.top_row = ed.row - rows_visible + 1
        self.top_row = self.scroll_start('pattern',self.top_row,(ed.pattern_id,ed.row),len(ed.pattern.rows),rows_visible)
        self.pattern_geometry = {
            'left':7*self.cw, 'right':grid_end*self.cw,
            'top':(top+2)*self.rh, 'bottom':bottom*self.rh,
            'last_row':min(len(ed.pattern.rows)-1,self.top_row+rows_visible-1),
            'voices':[(self.first_voice+view,(7+view*channel_w)*self.cw,channel_w*self.cw) for view in range(count)]}
        reset_x = 7
        toolbar_y=top-1.25-(2 if wrapped else 0)
        for w,label,action,name,value in controls:
            if reset_x+w>self.cols-2:
                reset_x=7;toolbar_y+=2
            button(self,reset_x,toolbar_y,w,label,action,selected=pressed(app,name,value))
            reset_x+=w+1
        description_x = reset_x + 1
        if self.cols >= description_x + 23:
            button(self,description_x,top-1.25,22,'Record automation','pulse_record_arm',
                   selected=app.pulse_record_armed,fill=REC_ARM if app.pulse_record_armed else None)
            description_x += 24
        if grid_end > description_x + 4:
            self.text(description_x,top-1.15,ed.selection_description(),DIM,grid_end-description_x-1)
        self.well(5, top + 1, grid_end - 5, bottom - top - 1)
        self.hit(7,top+2,grid_end-7,rows_visible,'pattern_grid',None)
        self.text(1, top, "ROW", DIM)
        for view in range(count):
            voice = self.first_voice + view
            x = 7 + view * channel_w
            self.rect(x - .5, top, channel_w - 1, 1, SELECT)
            armed = app.pulse_record_armed and app.pulse_record_voice == voice
            self.text(x, top, f"CH {voice + 1}" + (' (A)' if armed else ''), REC_ARM if armed else CREAM)
            self.monitor_buttons(app, voice, x + 10, top)
            mode=ed.pattern.rows[ed.row][voice].arp_mode
            button(self,x+18,top,8,'Arp '+{None:'..',0:'OFF',1:'ON',-1:'IN'}[mode],
                   'pattern_arpeggio',voice,selected=pressed(app,'pattern_arpeggio',voice),height=1)
            for label, columns, fields in FIELD_GROUPS:
                offset,width = group_span(columns)
                self.text(x+offset, top+1, label, AUTOMATION if label in ('A','D','S','R','PW','AR','W') else ACCENT)
                self.hit(x+offset,top+1,max(width,len(label)),1,'select_field',(voice,columns[0]))
        offsets = COLUMN_OFFSETS
        r0, r1, v0, v1 = ed.bounds()
        selected_fields = {v: ed.selected_fields(v) for v in range(v0, v1+1)} if ed.anchor is not None else {}
        hit_key = (self.cw,self.rh,top,rows_visible,self.top_row,self.first_voice,count,channel_w,len(ed.pattern.rows))
        rebuild_hits = self.pattern_hit_cache is None or self.pattern_hit_cache[0] != hit_key
        cell_hits = [] if rebuild_hits else self.pattern_hit_cache[1]
        for index in range(rows_visible):
            rownum = self.top_row + index
            if rownum >= len(ed.pattern.rows):
                break
            y = top + 2 + index
            grid_level = ed.pattern_grid.level(rownum)
            rowcolor = (WELL, (36, 36, 36), (55, 55, 55))[grid_level]
            if ed.highlight and rownum == ed.row:
                rowcolor = (82, 60, 56)
            self.rect(5.3, y, grid_end - 5.6, 1, rowcolor)
            playing_row = app.audio.playback.status != "stopped" and app.audio.playback.pattern == ed.pattern_id and app.audio.playback.row == rownum
            if playing_row:
                self.rect(5.3, y, grid_end - 5.6, 1, (42, 71, 49))
            self.text(0, y, ">" if playing_row else ("*" if app.playback_mark == (ed.pattern_id, rownum) else ""), TEXT)
            self.text(1, y, f"{rownum:03d}", TEXT)
            for view in range(count):
                voice = self.first_voice + view
                x = 7 + view * channel_w
                cell = ed.pattern.rows[rownum][voice]
                if ed.anchor is not None and r0 <= rownum <= r1 and v0 <= voice <= v1:
                    selected = selected_fields[voice]
                    if selected is None:
                        self.rect(x-.3,y,channel_w-1,1,SELECT)
                    else:
                        for _, columns, fields in FIELD_GROUPS:
                            if set(fields) & selected:
                                off,width = group_span(columns)
                                self.rect(x+off-.1,y,width+.2,1,SELECT)
                self.cached_voice_cell(cell, x, y)
                if ed.row == rownum and ed.voice == voice:
                    from sidpulse.ui.pattern_automation import prefix
                    pending = prefix(app)
                    if pending:
                        self.rect(x+25,y,3,1,SELECT)
                        self.text(x+25,y,pending.ljust(3,'.'),YELLOW)
                if ed.row == rownum and ed.voice == voice and not app.control_focus:
                    off = 25 + len(pending) if pending else offsets[ed.column]
                    width = 2 if ed.column == 0 else 1
                    self.rect(x + off, y + .86, width, .12, CURSOR)
                    self.rect(x + off, y, width, 1, CURSOR, True)
                if rebuild_hits:
                    for col, off in enumerate(offsets):
                        cell_hits.append((pg.Rect(round((x+off)*self.cw),round(y*self.rh),
                                                  (2 if col == 0 else 1)*self.cw,self.rh),
                                          'cell',(rownum,voice,col)))
        self.pattern_hit_cache = (hit_key, cell_hits)
        self.hits.extend(cell_hits)
        # Bevelled gutters separate every voice, including through row highlights.
        # Cell geometry follows the scaled font metrics, so the columns and
        # their mouse targets stay aligned at every zoom level.
        for view in range(1,count):
            gx=7+view*channel_w-1.5
            gutter=self.rect(gx,top+1,1,bottom-top-1,BG)
            edge=max(1,round(self.cw/8))
            pg.draw.line(self.screen,CREAM,gutter.topleft,gutter.bottomleft,edge)
            pg.draw.line(self.screen,EDGE,gutter.topright,gutter.bottomright,edge)
        self.control_toggle(grid_end+1, top, bottom)
        if self.control_visible:
            x = grid_end + 1
            self.rect(x, top, sidebar - 1, 1, (63, 79, 97))
            self.text(x + 1, top, "CTRL CH / FILTER", CREAM, sidebar - 6)
            self.well(x, top + 1, sidebar - 1, bottom - top - 1)
            self.text(x + 1, top + 1, "CUT RES RT MD V SL", (143, 178, 202), sidebar - 2)
            for index in range(rows_visible):
                rownum=self.top_row+index
                if rownum>=len(ed.pattern.rows):break
                y=top+2+index
                self.rect(x+.3,y,sidebar-1.6,1,(32,61,80) if app.control_focus and rownum==ed.row else ((22,30,39),(39,51,63),(52,66,80))[ed.pattern_grid.level(rownum)])
                control=ed.pattern.controls.get(rownum)
                if control:
                    val=lambda k,n: '.'*n if getattr(control,k) is None else f'{getattr(control,k):0{n}X}'
                    line=f"{val('cutoff',3)} {val('resonance',1)} {val('routing',1)} {val('mode',2)} {val('volume',1)}"
                    line+=' '+('.' if control.slide is None else f'{control.slide:+d}')
                else:line='... . . .. . .'
                self.text(x+1,y,line,(158,193,219),sidebar-2)
                if app.control_focus and rownum==ed.row:self.rect(x+.5,y,sidebar-2,1,CYAN,True)
                self.hit(x,y,sidebar-1,1,"control",rownum)
            self.hit(x,top,sidebar-5,1,"control_focus",None)
            self.control_toggle(x,top,bottom)

        self.scroll_bar('pattern',self.cols-2.5,top+2,rows_visible,len(ed.pattern.rows),rows_visible)

    def control_toggle(self, x, top, bottom):
        if not self.control_visible:
            self.rect(x,top,2.6,max(1,bottom-top),(39,51,63))
        bx = x+19 if self.control_visible else x
        rect = self.rect(bx,top,2.6,1,(63,79,97))
        button_frame(self,rect,False,(63,79,97))
        cx,cy = rect.center
        half = max(3,min(rect.width,rect.height)//4)
        direction = 1 if self.control_visible else -1
        pg.draw.polygon(self.screen,CREAM,[(cx+direction*half,cy),(cx-direction*half,cy-half),(cx-direction*half,cy+half)])
        self.hit(bx,top,2.6,1,'control_panel_toggle',None)

    def cached_voice_cell(self, cell, x, y, maxchars=28):
        key = (cell.note,cell.instrument,cell.effect,cell.parameter,cell.attack,
               cell.decay,cell.sustain,cell.release,cell.pulse_width,cell.arp_mode,cell.waveform,maxchars)
        surface = self.cell_cache.get(key)
        if surface is None:
            surface = pg.Surface((maxchars*self.cw, self.font.get_height()), pg.SRCALPHA)
            screen = self.screen
            try:
                self.screen = surface
                self.voice_cell(cell, 0, 0, maxchars)
            finally:
                self.screen = screen
            self.cell_cache[key] = surface
            if len(self.cell_cache) > 512:
                self.cell_cache.popitem(last=False)
        else:
            self.cell_cache.move_to_end(key)
        self.screen.blit(surface, (round(x*self.cw),round(y*self.rh)))

    def voice_cell(self, cell, x, y, maxchars=28):
        columns = [(0, note_name(cell.note), CREAM if cell.note is not None else ACCENT),
                   (5, '..' if cell.instrument is None else f'{cell.instrument:02d}', YELLOW if cell.instrument else ACCENT),
                   (8, {None:'..',0:'OF',1:'ON',-1:'IN'}[cell.arp_mode], AUTOMATION_DIM if cell.arp_mode is None else AUTOMATION),
                   (11, WAVEFORM_LABELS[cell.waveform], AUTOMATION_DIM if cell.waveform is None else AUTOMATION),
                   (13, cell.effect or '.', PURPLE if cell.effect else ACCENT),
                   (14, '..' if cell.parameter is None else f'{cell.parameter:02X}', PURPLE if cell.parameter is not None else ACCENT)]
        for offset, field in zip((17, 19, 21, 23), ENVELOPE_FIELDS):
            value = getattr(cell, field)
            columns.append((offset, '.' if value is None else 'R' if value == -1 else f'{value:X}',
                            AUTOMATION_DIM if value is None else AUTOMATION))
        all_reset = all(getattr(cell, field) == -1 for field in ENVELOPE_FIELDS)
        pw = '...' if cell.pulse_width is None else ('RAL' if all_reset else 'R..') if cell.pulse_width == -1 else f'{cell.pulse_width:03X}'
        columns.append((25, pw, AUTOMATION_DIM if cell.pulse_width is None else AUTOMATION))
        for offset, value, color in columns:
            if offset + len(value) <= maxchars:
                self.text(x+offset, y, value, color, maxchars-offset)

    def list_page(self, app, title, entries, top, bottom, left=1, start_index=0):
        self.text(left, top, title, CYAN)
        visible = max(1, bottom - top - 2)
        start = max(start_index, app.property_index - visible + 1)
        for i, (label, value) in enumerate(entries[start:start + visible], start):
            y = top + 2 + i - start
            if i == app.property_index:
                self.rect(left, y, self.cols - left - 1, 1, SELECT)
            # Two columns collapse to a single readable line in narrow viewports.
            self.text(left + 1, y, f"{label:18s} {value}", CREAM if i == app.property_index else TEXT)
            self.hit(left, y, self.cols - left - 1, 1, "property", i)

    def activity_dot(self, x, y, level, kind, number):
        radius = max(2, round(min(self.cw, self.rh)*.28))
        center = (round(x*self.cw), round((y+.55)*self.rh))
        idle = (66, 76, 62)
        bright = (142, 248, 104)
        level = max(0., min(1., level))
        color = tuple(round(a+(b-a)*level) for a,b in zip(idle,bright))
        pg.draw.circle(self.screen, color, center, radius)
        rect = pg.Rect(center[0]-radius-2,center[1]-radius-2,2*radius+4,2*radius+4)
        self.hits.append((rect,'activity_indicator',(kind,number)))

    def instrument(self, app, top, bottom):
        inst = app.editor.song.instruments.get(app.editor.instrument)
        left = 33 if self.cols >= 84 else 1
        if left > 1:
            button(self,1,top,29,"Add instrument","add_instrument")
            button(self,1,top+1.5,29,"Delete instrument","delete_instrument")
            button(self,1,top+3,29,"Choose from presets","choose_presets")
            extra = 2 if app.pulse_record_armed else 0
            if extra:
                self.disarm_button(app,1,top+4.5,29)
            count=max(1,int(bottom-top-8-extra))
            list_top = top + 5 + extra
            list_bottom = list_top + count
            self.well(4, list_top, 26, count)
            self.rect(1,list_bottom+.15,29,max(0,bottom-list_bottom-.3),PANEL)
            button(self,1,list_bottom+.5,29,'Save user preset','save_user_preset')
            # Bank lists always center, independently of F2's cursor setting.
            start=max(1,min(100-count,app.instrument_slot-count//2))
            start=1+self.scroll_start('instruments',start-1,app.instrument_slot,99,count)
            for i, number in enumerate(range(start,min(100,start+count))):
                y=list_top+i;selected=number==app.instrument_slot;item=app.editor.song.instruments.get(number)
                if selected:self.rect(4.2,y+.1,25.6,1,CREAM if app.instrument_focus=='list' else SELECT)
                self.text(1,y,f'{number:02d}',TEXT)
                color=TEXT if selected and app.instrument_focus=='list' else YELLOW if item else (150,150,140)
                self.text(4.5,y,item.name if item else '(empty)',color,18)
                self.hit(1,y,29,1,'choose_instrument',number)
                self.activity_dot(23.8,y,self.instrument_levels.get(number,0.) if item else 0.,'instrument',number)
                self.bank_monitor_buttons(app, 'instrument', number, 25, y, item is not None)
            self.scroll_bar('instruments',30.4,list_top,count,99,count)
            button(self,left,top-1.25,20,'Copy instrument','copy_instrument',selected=pressed(app,'copy_instrument'))
            button(self,left+21,top-1.25,21,'Paste instrument','paste_instrument',selected=pressed(app,'paste_instrument'))
        if left==1 and app.inline_recording_visible:
            button(self,1,top,27,'Record automation','pulse_record_arm',selected=True)
            button(self,29,top,min(29,self.cols-31),f'Instrument {app.instrument_slot:02d}',
                   'instrument_tab','general')
            button(self,1,top+1.5,20,'Copy instrument','copy_instrument',selected=pressed(app,'copy_instrument'))
            button(self,22,top+1.5,21,'Paste instrument','paste_instrument',selected=pressed(app,'paste_instrument'))
            if app.pulse_record_armed:self.disarm_button(app,1,top+3,29)
            from sidpulse.ui.automation_inline import draw
            draw(self,app,1,top+(4.5 if app.pulse_record_armed else 3.5),bottom)
            return
        if left==1:
            button(self,1,top,18,"Add instrument","add_instrument")
            button(self,20,top,20,"Delete instrument","delete_instrument")
            button(self,1,top+1.5,25,"Choose from presets","choose_presets")
            self.activity_dot(28,top+1.5,self.instrument_levels.get(app.instrument_slot,0.),'instrument',app.instrument_slot)
            self.bank_monitor_buttons(app, 'instrument', app.instrument_slot, 30, top+1.5,
                                      app.instrument_slot in app.editor.song.instruments)
            button(self,1,top+3,20,'Copy instrument','copy_instrument',selected=pressed(app,'copy_instrument'))
            button(self,22,top+3,21,'Paste instrument','paste_instrument',selected=pressed(app,'paste_instrument'))
            if app.pulse_record_armed:
                self.disarm_button(app,1,top+4.5,29)
                top+=2
            top+=4.5
        if app.instrument_slot not in app.editor.song.instruments and not app.inline_recording_visible:
            button(self,left,top,min(27,self.cols-left-2),'Record automation','pulse_record_arm')
            top+=1.5
            self.text(left,top+1,f'Instrument {app.instrument_slot:02d} is empty.',TEXT)
            self.text(left,top+3,'Enter opens Choose preset / No preset / Manual.',TEXT,self.cols-left-2)
            for i,(label,mode) in enumerate((('Choose preset','presets'),('No preset','blank'),('Manual','manual'))):
                button(self,left+i*17,top+6,16,label,'new_instrument_mode',mode)
            return
        app.normalize_instrument_tab()
        from sidpulse.ui.sample_synthesis import draw_protection
        top, protected = draw_protection(self,app,left,top,bottom)
        if protected:return
        mapped=inst.sample_override
        if mapped:
            sample=app.editor.song.samples.get(str(inst.sample_slot),app.editor.song.samples.get(inst.sample_slot))
            name=sample.get('name','Stored sample') if sample else '(empty slot)'
            self.text(left,top,f'Using sample {inst.sample_slot:02d}: {name}',TEXT,self.cols-left-2)
            top+=1.5
        motion=app.instrument_tab=="motion"
        tabs=(((0,14,"Sample","sample"),(15,19,"PCM programs","motion"),(35,14,"Arp / pitch","roll")) if mapped else
              ((0,10,"General","general"),(11,19,"Motion / tables","motion"),(31,14,"Arp / pitch","roll"),(46,8,"ADSR","adsr"),(55,9,"PCM","sample")))
        for i,(x,w,label,tab) in enumerate(tabs):
            wrapped=self.cols-left<66 and i>=2
            button(self,left+(x-31 if wrapped else x),top+(1.5 if wrapped else 0),w,label,"instrument_tab",tab,app.instrument_tab==tab)
        if self.cols-left<66:top+=2
        if app.inline_recording_visible:
            button(self,left,top+2,min(27,self.cols-left-2),'Record automation','pulse_record_arm',selected=True)
            from sidpulse.ui.automation_inline import draw
            draw(self,app,left,top+4,bottom)
            return
        if app.instrument_tab=="sample":
            from sidpulse.ui.sample_view import instrument
            instrument(self,app,left,top+2,bottom);return
        if app.instrument_tab=="adsr":
            draw_adsr(self,app,left,top+2,bottom);return
        if app.instrument_tab=="roll":
            draw_roll(self,app,left,top+2,bottom);return
        if not motion:
            button(self, left, top+2, min(27,self.cols-left-2),
                   'Record automation (A)' if app.pulse_record_armed else 'Record automation',
                   'pulse_record_arm', selected=app.pulse_record_armed,
                   fill=REC_ARM if app.pulse_record_armed else None)
        self.text(left,top+(2 if motion else 3.5),"PCM pitch / gate / retrigger programs" if mapped else "Tick programs / decimal values" if motion else "SID synthesis / hex values",TEXT)
        full_wave=not motion and bottom-top>=23 and self.cols-left>=55
        side_envelope = full_wave and self.cols-left >= 74
        fields_right = left + max(43, int((self.cols-left-2)*.55)) if side_envelope else None
        draw_fields(self,app,left,top+(4 if motion else 5),bottom-7.5 if full_wave else bottom-3,motion,full_wave,right=fields_right)
        if side_envelope:
            draw_envelope(self,app,fields_right+2,top+4,self.cols-fields_right-4,bottom-top-12)
        if full_wave:self.wave_buttons(inst.waveform,left,bottom-7,min(65,self.cols-left-2))

        if bottom - top >= 17 and not full_wave:
            self.text(left, bottom - 2, "Drag slider | Click yellow value: type | Wheel: scroll", DIM)
            self.text(left, bottom - 1, "Tab: bank / buttons / fields | Note keys: audition", DIM)

    def disarm_button(self, app, x, y, w):
        button(self,x,y,w,f'Disarm CH {app.pulse_record_voice+1} (A)',
               'pulse_record_disarm',selected=pressed(app,'pulse_record_disarm'),fill=REC_ARM)

    def wave_buttons(self, selected, x, y, w):
        self.panel(x, y, w, 6.5, "Oscillator waveform")
        shapes = {
            16: [(0, .9), (.25, .1), (.5, .9), (.75, .1), (1, .9)],
            32: [(0, .9), (.45, .1), (.45, .9), (.9, .1), (.9, .9), (1, .7)],
            64: [(0, .9), (0, .1), (.3, .1), (.3, .9), (.6, .9), (.6, .1), (.9, .1), (.9, .9), (1, .9)],
            128: [(0, .5), (.1, .1), (.2, .8), (.3, .35), (.4, .9), (.5, .1), (.6, .6), (.7, .2), (.8, .9), (.9, .4), (1, .65)]}
        bw = (w - 6) / 2
        for i, (wave, points) in enumerate(shapes.items()):
            bx, by = x + 2 + (i % 2) * (bw + 2), y + 2 + (i // 2) * 2
            rect = self.rect(bx, by, bw, 1.5, SELECT if wave == selected else BG)
            button_frame(self,rect,wave==selected)
            label=WAVES[wave].title()
            label_width=self.font.size(label)[0]+self.cw
            group_width=self.cw*5+label_width
            shape_rect = pg.Rect(rect.centerx-group_width//2,rect.y+5,self.cw*4,rect.height-10)
            color = CREAM if wave == selected else TEXT
            pg.draw.lines(self.screen, color, False, [(shape_rect.x + a * shape_rect.width, shape_rect.y + b * shape_rect.height) for a, b in points], 1)
            self.control_text(pg.Rect(shape_rect.right+self.cw,rect.y,label_width,rect.height),label,color)
            self.hit(bx, by, bw, 1.5, "waveform", wave)

    def settings(self, app, top, bottom):
        song = app.editor.song
        filt = song.filter
        entries = [("Song title", song.title), ("Author", song.author or "(empty)"), ("SID model", song.sid_model),
                   ("UI zoom", f"{app.zoom:.0%}"), ("Filter cutoff", f"${filt.cutoff:03X}"),
                   ("Resonance", f"{filt.resonance:X}"), ("Routing bits 321", f"{filt.routing:03b}"),
                   ("Mode LP/BP/HP", f"${filt.mode:02X}"), ("Master volume", f"{filt.volume:X}"),
                   ("Comments", (song.comments.splitlines()[0]+" ...") if "\n" in song.comments else song.comments or "(empty)"), ("Bottom helper", "ON" if app.helper_strip else "OFF"),
                   ("Speed (ticks)", str(song.speed)), ("Tempo", str(song.tempo)),
                   ("Audio buffer", f"{app.audio_buffer} samples / {app.audio_buffer / 48:.1f} ms per block"),
                   ("PSID released",song.export_config.get("released","2026 SIDpulse")),
                   ("Loop song at end", "ON" if song.export_config.get("loop",True) else "OFF"),
                   ("C64 timing",song.clock), ("Colour theme",app.appearance['theme']),
                   ("Font size",str(app.appearance['font_size'])), ("Bold font",'ON' if app.appearance['font_bold'] else 'OFF'),
                   ("Font file",app.appearance['font_file'] or 'Bundled DejaVu Sans Mono'),
                   ("File timestamps", "ON" if app.file_browser_show_modified else "OFF"),
                   ("Autosave settings",('ON' if app.autosave.enabled else 'OFF')+f' / {app.autosave.minutes} minutes / folder...'),
                   ("Restart on repeated F5",'ON' if app.restart_on_f5 else 'OFF'),
                   ("Grid: rows per beat",str(app.editor.pattern_grid.rows_per_beat)),
                   ("Grid: beats per bar",f"{app.editor.pattern_grid.beats_per_bar} ({app.editor.pattern_grid.rows_per_bar} rows/bar)"),
                   ("Clipboard buttons", "ON" if app.pattern_clipboard_buttons else "OFF"),
                   ("Control/filter column", "AUTO" if app.control_panel_visible is None else "SHOWN" if app.control_panel_visible else "HIDDEN"),
                   ("Channel visualizers", "ON" if app.channel_visualizers else "OFF (scope processing disabled)"),
                   ("Keyboard mapping", app.keyboard_mapping.title() + '...')]
        self.text(1,top,"SONG / DISPLAY / SHARED SID FILTER | Click value / arrows / Enter",TEXT)
        count=max(1,int((bottom-top-2)/1.35));start=max(0,app.property_index-count+1)
        start=self.scroll_start('settings',start,app.property_index,len(entries),count)
        for i,(label,value) in enumerate(entries[start:start+count],start):
            y=top+2+(i-start)*1.35
            if app.property_index==i:self.rect(1.5,y,24.5,1,SELECT)
            self.text(2,y,label,CREAM if app.property_index==i else TEXT,24)
            button(self,27,y,max(8,self.cols-31),value,'setting_edit',i,app.property_index==i)
        self.scroll_bar('settings',self.cols-2.5,top+2,count*1.35,len(entries),count)

    def orders(self, app, top, bottom):
        from sidpulse.ui.orders import draw
        draw(self, app, top, bottom)

    def octave_controls(self, app, x, y):
        self.text(x,y,f'Oct: {app.editor.octave}',TEXT)
        for offset,label,action,value in ((8,'+1','octave',1),(13,'0','octave_reset',None),(18,'-1','octave',-1)):
            button(self,x+offset,y-.05,4,label,action,value,pressed(app,action,value),height=.95)

    def samples(self, app, top, bottom):
        from sidpulse.ui.sample_view import experimental_warning
        top = experimental_warning(self, top)
        left = 34 if self.cols >= 80 else 2
        if left > 2:
            self.well(4, top, 26, bottom - top)
            samples = app.editor.song.samples
            count = max(1, int(bottom - top - 1))
            start = max(1,min(100-count,app.sample_index-count//2))
            start = 1+self.scroll_start('samples',start-1,app.sample_index,99,count)
            for i, number in enumerate(range(start, min(100, start + count))):
                self.text(1, top + i, f"{number:02d}")
                sample = samples.get(str(number), samples.get(number))
                label = sample.get("name", "Stored sample") if isinstance(sample, dict) else ""
                if number == app.sample_index:
                    self.rect(4.2, top + i + .1, 25.6, 1, CREAM)
                self.text(4.5, top + i, label, TEXT if number == app.sample_index else YELLOW, 18)
                self.hit(1,top+i,29,1,'choose_sample',number)
                self.activity_dot(23.8,top+i,0.,'sample',number)
                self.bank_monitor_buttons(app, 'sample', number, 25, top+i, False)
            self.scroll_bar('samples',30.4,top,count,99,count)
        else:
            self.bank_monitor_buttons(app, 'sample', app.sample_index, 30, top, False)
        from sidpulse.ui.sample_view import details
        details(self, app, left, top, bottom)

    def files(self, app, top, bottom):
        from sidpulse.ui.file_browser_view import draw
        draw(self, app, top, bottom)

    def info(self, app, top, bottom):
        state = app.audio.playback
        control_x = self.cols - (24 if self.control_visible else 4)
        body_right = control_x - 2
        width = max(9, (body_right - 7) // 3 - 1)
        panel_h = min(7, max(4, bottom - top - 6))
        for voice in range(3):
            x = 7 + voice * (width + 1)
            self.well(x, top, width, panel_h)
            text_width = min(15, width - 2)
            armed = app.pulse_record_armed and app.pulse_record_voice == voice
            rows = [(f"CH {voice + 1} (A)" if armed else f"SID VOICE {voice + 1}", REC_ARM if armed else CREAM), (None, None),
                    (note_name(state.notes[voice]), YELLOW)]
            if panel_h >= 6:
                rows.extend([(f"Instrument {state.instruments[voice]:02d}", ACCENT),
                             ("MUTED" if app.preview_monitor_mask()[voice] else "MONITOR ON", CREAM)])
            stacked_scope = app.channel_visualizers and width < 32
            first_y = top + .1 if stacked_scope else top + (panel_h - len(rows)) / 2
            for i, (label, color) in enumerate(rows):
                if label is None:
                    self.monitor_buttons(app, voice, x + 1, first_y + i)
                else:
                    rect = pg.Rect(round((x + 1) * self.cw), round((first_y + i) * self.rh),
                                   round(text_width * self.cw), self.rh)
                    self.control_text(rect, label, color, align='left', padding=0)
            if app.channel_visualizers:
                if stacked_scope:
                    scope = pg.Rect(round((x+1)*self.cw), round((top+len(rows)+.3)*self.rh),
                                    round((width-2)*self.cw), max(5,round((panel_h-len(rows)-.6)*self.rh)))
                else:
                    scope = pg.Rect(round((x+17)*self.cw), round((top+.7)*self.rh),
                                    round((width-18)*self.cw), round((panel_h-1.4)*self.rh))
                pg.draw.line(self.screen, EDGE, (scope.left, scope.centery), (scope.right, scope.centery))
                values = app.audio.voice_waveforms[voice]
                if app.preview_monitor_mask()[voice] or state.status == 'stopped' and not app.audio.active:
                    values = (0.,) * len(values)
                points = [(scope.left + i * (scope.width - 1) / max(1, len(values) - 1),
                           scope.centery - value * scope.height * .45) for i, value in enumerate(values)]
                if len(points) > 1:
                    pg.draw.lines(self.screen, self.scope_color, False, points, max(1, self.cw // 6))
                self.hit(scope.x / self.cw, scope.y / self.rh, scope.w / self.cw, scope.h / self.rh, 'voice_scope', voice)
        song = app.editor.song
        pat = song.patterns.get(state.pattern)
        y = top + panel_h + 1
        if pat is not None:
            visible = max(0, bottom - y - 3)
            start = max(0, min(len(pat.rows) - visible, state.row - visible // 2))
            self.well(2, y, body_right - 2, visible)
            for i in range(visible):
                row = start + i
                if row >= len(pat.rows):
                    break
                if row == state.row:
                    self.rect(2.2, y + i, body_right - 2.4, 1, (42, 71, 49))
                self.text(3, y + i, f"{row:03d}", CREAM)
                for voice, cell in enumerate(pat.rows[row]):
                    x = 7 + voice * (width + 1)
                    self.cached_voice_cell(cell, x, y+i, width)
            for voice in (1,2):
                gutter=self.rect(7+voice*(width+1)-1,y,1,visible,BG)
                pg.draw.line(self.screen,CREAM,gutter.topleft,gutter.bottomleft,max(1,self.cw//8))
                pg.draw.line(self.screen,EDGE,gutter.topright,gutter.bottomright,max(1,self.cw//8))
        if self.control_visible:
            self.playback_control(app, control_x, top, bottom-3, pat,
                                  start if pat is not None else 0, y)
        self.control_toggle(control_x,top,bottom-3)
        if bottom > top + 4:
            self.horizontal_rule(bottom - 2.25)
            self.text(2, bottom - 2, state.warning or "-/+: previous/next order | F2: edit | F8: stop | Shift+F8: pause", TEXT)
            self.text(2, bottom - 1, f"Audio gaps {app.audio.underruns} | late wakes {app.audio.late_wakes} | render peak {app.audio.peak_render_load:.0%} | over budget {app.audio.over_budget}", DIM)

    def order_skip_buttons(self, app, x, y):
        from sidpulse.ui.pressable import pressed
        state = app.audio.playback
        playing = state.status == 'playing' and state.mode == 'song'
        for i, direction in enumerate((-1, 1)):
            available = playing and 0 <= state.order + direction < len(app.editor.song.orders)
            rect = button(self, x + i * 3, y, 2.5, '', 'skip_order', direction,
                          selected=available and pressed(app, 'skip_order', direction))
            if not available:
                self.hits.pop()  # disabled controls have no click target
            dx, dy = max(2, rect.width // 6), max(3, rect.height // 4)
            cx, cy = rect.center
            pg.draw.polygon(self.screen, TEXT if available else EDGE,
                            [(cx + direction * dx, cy),
                             (cx - direction * dx, cy - dy),
                             (cx - direction * dx, cy + dy)])

    @staticmethod
    def filter_row_text(control):
        if control is None:
            return '... . . .. . .'
        val = lambda key, digits: '.'*digits if getattr(control, key) is None else f'{getattr(control, key):0{digits}X}'
        return (f"{val('cutoff', 3)} {val('resonance', 1)} {val('routing', 1)} {val('mode', 2)} {val('volume', 1)} "
                + ('.' if control.slide is None else f'{control.slide:+d}'))

    def playback_control(self, app, x, top, bottom, pattern, start, rows_top):
        width = 22
        self.well(x, top, width, max(1, bottom-top))
        self.rect(x, top, width, 1, (63, 79, 97))
        self.text(x+1, top, 'CTRL CH / FILTER', CREAM, width-5)
        self.hit(x, top, width, 1, 'playback_control', None)
        state = app.audio.playback
        values = state.filter_values
        if values is None:
            filt = app.editor.song.filter
            values = (filt.cutoff, filt.resonance, filt.routing, filt.mode, filt.volume, 0)
        if bottom-top >= 5:
            self.text(x+1, top+1, 'LIVE CUT RES RT MD V', (143, 178, 202), width-2)
            cutoff, res, route, mode, volume, slide = values
            self.text(x+1, top+2, f'{cutoff:03X} {res:X} {route:X} {mode:02X} {volume:X}', (158, 193, 219), width-2)
            self.text(x+1, top+3, f'Slide {slide:+d} / tick', (158, 193, 219), width-2)
        if pattern is not None:
            self.text(x+1, rows_top-1, 'CUT RES RT MD V SL', (143, 178, 202), width-2)
            for index in range(max(0, int(bottom-rows_top))):
                row = start + index
                if row >= len(pattern.rows):
                    break
                self.rect(x+.3, rows_top+index, width-.6, 1,
                          (32, 72, 96) if row == state.row else (22, 30, 39))
                self.text(x+1, rows_top+index, self.filter_row_text(pattern.controls.get(row)),
                          (158, 193, 219), width-2)

    def bank_monitor_buttons(self, app, kind, number, x, y, available):
        if not app.instrument_monitor_buttons:
            return
        for offset, suffix, label in ((0, 'mute', 'M'), (2.5, 'solo', 'S')):
            action = 'instrument_' + suffix
            active = available and (number in app.muted_instruments if suffix == 'mute'
                                    else app.solo_instrument == number)
            down = active or available and pressed(app, action, number)
            fill = ((128,63,49) if suffix == 'mute' else (49,112,64)) if active else BG
            rect = pg.Rect(round((x+offset)*self.cw),round((y+.05)*self.rh),round(2.2*self.cw),round(.9*self.rh))
            color = CREAM if active else TEXT if available else (115,115,105)
            key = (rect.size,label,down,fill,color)
            surface = self.bank_button_cache.get(key)
            if surface is None:
                surface = pg.Surface(rect.size)
                screen = self.screen
                try:
                    self.screen = surface
                    button_frame(self,surface.get_rect(),down,fill)
                    self.control_text(surface.get_rect(),label,color)
                finally:
                    self.screen = screen
                self.bank_button_cache[key] = surface
                if len(self.bank_button_cache) > 64:
                    self.bank_button_cache.popitem(last=False)
            else:
                self.bank_button_cache.move_to_end(key)
            self.screen.blit(surface,rect)
            self.hits.append((rect, action if available else 'bank_monitor_disabled',
                              number if available else (kind,number)))

    def monitor_buttons(self, app, voice, x, y):
        for action,label,enabled,offset in (("mute","M",app.muted[voice],0),
                                            ("solo","S",app.solo_voice==voice,3.3)):
            fill=((128,63,49) if action=="mute" else (49,112,64)) if enabled else BG
            button=self.rect(x+offset,y,2.6,1,fill)
            button_frame(self,button,enabled,fill)
            color=CREAM if enabled else TEXT
            self.control_text(button,label,color)
            self.hit(x+offset,y,2.6,1,action,voice)

    def help(self, app, top, bottom):
        self.well(1, top, self.cols - 2, bottom - top)
        x, menu_y = 2, top
        if self.cols < 50 or bottom - top < 7:
            self.text(2, menu_y, f"{app.help_topic + 1}: {HELP_TOPIC_NAMES[app.help_topic]}  < > topics", CREAM)
        else:
            for i, title in enumerate(HELP_TOPIC_NAMES):
                label = f"{i + 1} {title}"
                if x + len(label) + 1 >= self.cols - 2:
                    x = 2
                    menu_y += 1
                if i == app.help_topic:
                    self.rect(x, menu_y, len(label) + 1, 1, SELECT)
                self.text(x, menu_y, label, CREAM if i == app.help_topic else ACCENT)
                self.hit(x, menu_y, len(label) + 1, 1, "help_topic", i)
                x += len(label) + 2
        from sidpulse.ui.help_layout import layout
        body_top = menu_y + 2
        key_width = min(32, max(10, (self.cols-10)//3))
        description_x = 4 + key_width + 3
        description_width = max(8,self.cols-description_x-5)
        lines = layout(app.help_topic,key_width,description_width)
        visible = max(0,int(bottom-body_top))
        app.help_scroll = max(0,min(app.help_scroll,max(0,len(lines)-visible)))
        app.help_scroll = self.scroll_start('help',app.help_scroll,(app.help_topic,app.help_scroll),len(lines),visible)
        area = pg.Rect(self.cw,top*self.rh,(self.cols-2)*self.cw,(bottom-top)*self.rh)
        old = self.screen.get_clip();self.screen.set_clip(old.clip(area.inflate(-4,-4)))
        for y,(kind,key,description) in enumerate(lines[app.help_scroll:app.help_scroll+visible],body_top):
            if kind == 'rule':
                pg.draw.line(self.screen,CREAM,(3*self.cw,round((y+.5)*self.rh)),
                             ((self.cols-3)*self.cw,round((y+.5)*self.rh)))
            elif kind == 'heading':self.text(3,y,key,CREAM,self.cols-6)
            elif kind == 'entry':
                self.text(4,y,key,YELLOW,key_width)
                self.text(description_x,y,description,ACCENT,description_width)
        self.screen.set_clip(old)
        self.scroll_bar('help',self.cols-2.5,body_top,visible,len(lines),visible)

    def context_status(self, app):
        ed = app.editor
        if app.pulse_take:
            take = app.pulse_take
            from sidpulse.playback.automation_parameters import PARAMETERS
            code = PARAMETERS[take.get('field','pulse_width')][1]
            return (f"{'Finishing' if take['pending'] else 'Recording'} {code} on CH {take['voice']+1}: {take['value']:X}"
                    ' | Row steps | Release: keep | Esc: cancel')
        if app.instrument_drag and app.instrument_drag.get('automation_preview'):
            return f'Adjust recording {app.recording_info[1]}: {app.pulse_record_value:X} | Arm and play to write rows'
        if app.page == 'pattern':
            if app.control_focus:
                return 'Edit shared SID filter | Enter: edit this row | Tab: voice columns'
            from sidpulse.ui.pattern_automation import prefix
            pending = prefix(app)
            if pending:
                return f'PW reset entry: {pending} | Finish RAL: reset all | R then Enter: PW only | Esc: cancel'
            return CURSOR_HINTS[ed.column] + (f' | REC {app.recording_info[1]} armed: CH {app.pulse_record_voice+1}' if app.pulse_record_armed else '')
        if app.page == 'instrument':
            if app.inline_recording_visible and app.instrument_focus == 'automation':
                return f'Record channel {app.recording_info[1]} | Arrows: adjust | Shift: coarse | Ctrl: fine | F5/F6: play | F8: stop'
            if app.instrument_slot not in ed.song.instruments:
                return f'Empty instrument {app.instrument_slot:02d} | Enter: create'
            drag = app.instrument_drag
            if drag:
                field = drag['field']
                inst = ed.song.instruments[drag['instrument']]
                value = f"{inst.pulse_width:03X}" if field == "pulse_width" else display(inst, field)
                return f"Adjusting instrument {drag['instrument']:02d} {field.replace('_', ' ')}: {value}"
            if app.instrument_focus == 'list':
                return f'Select instrument | {app.instrument_slot:02d} | Enter: edit | Ins: add | Del: delete'
            if app.instrument_focus == 'buttons':
                return 'Select instrument control | Arrows: choose | Enter: activate'
            field = INSTRUMENT_FIELDS[app.property_index]
            return f'Instrument {ed.instrument:02d} | {INSTRUMENT_LABELS[app.property_index]} | Edit instrument value'
        return ed.status

    def helper(self, app, y):
        ed = app.editor
        if app.menu_path:
            item = menu_items(app.menu_path[-1])[app.menu_indices[-1]]
            first = item.label + (" | Not available yet" if not item.enabled else "")
            second = "Arrows: select | Enter: choose | Escape: back"
        elif app.page == "pattern":
            descriptions = list(CURSOR_HINTS)
            for index in (13, 14, 15):
                descriptions[index] = 'PW: 000..FFF; blank holds; RAL resets A D S R PW; R then Enter resets only PW.'
            first = descriptions[ed.column]
            effect = lookup_effect(ed.cell.effect, ed.cell.parameter) if ed.cell.effect else None
            if PATTERN_FIELDS[ed.column] in ('effect', 'parameter') and effect:
                first = f"{effect['code']} {effect['description']} [{STATUS[effect['status']]}] | {effect['reason']}"
            second = ("Ctrl+Insert copy | Shift+Insert paste | " if app.keyboard_mapping=='modern' else "Alt+C copy | Alt+O paste | ") + "Shift+arrows: select | Ctrl+Shift+V special"
            if app.control_focus:
                first="CTRL CH / FILTER: one shared filter. Click a row or Enter to edit cutoff, route, mode and sweep."
                second="Up/Down: row | Enter: edit | Delete: clear control row | Tab: voice grid | Ctrl+Shift+F2: toggle"
        elif app.page == "instrument":
            fields = INSTRUMENT_LABELS
            first = f"Instrument {ed.instrument:02d}: {fields[app.property_index]}. This bank defines SID synthesis, separate from PCM samples."
            inst=ed.song.instruments.get(ed.instrument)
            if inst and inst.sample_override:
                first = f"Instrument {ed.instrument:02d}: PCM sample {inst.sample_slot:02d}. Pitch/gate programs apply; SID settings are stored."
            second = "Tab: bank/buttons/properties | Ins: add | Del: delete | F8 then note keys: audition | F1 help"
            if app.keyboard_mapping == 'modern':
                second = 'Octave: + / - / 0 reset to 4 | Tab: focus | F8 then note keys: audition | F1 help'
            if app.instrument_tab=="roll":first="Piano grid: draw relative semitone steps. Arpeggio repeats; pitch sequence holds its last step."
            if app.instrument_tab=="sample":first="PCM override: assign a sample slot, preserve SID settings, export host audio."
            if app.instrument_tab=="adsr":first="Drag ADSR handles or sliders. SID rate settings: 00..0F. Sustain is a level, not a duration."
            if app.instrument_slot not in ed.song.instruments:
                first = f"Empty instrument slot {app.instrument_slot:02d}. Enter: Choose preset / No preset / Manual."
            if app.inline_recording_visible and app.instrument_focus=='automation':
                first = 'Choose a parameter and channel. The blue slider records channel overrides; instrument definitions stay intact.'
                second = '1/2/3: channel | Space: arm/disarm | Tab: focus | Arrows: value | Release: keep | Esc: cancel take'
        elif app.page == "files":
            first = "One browser for Load, Save As, SID and PRG. Filename edits do not alter notes or the project title."
            second = "Tab: field | Left/Right/Home/End: caret | Shift: select | Ctrl+L: directory | Ctrl+A: select all"
        elif app.page == "help":
            first = "Quick help: choose a topic above. Inactive legacy bindings are grey in the shortcut registry."
            second = "1..9 or Left/Right/Tab: topic | Up/Down/PgUp/PgDn: scroll | Escape: return to editor"
        else:
            first = {"samples": "PCM sample bank: import audio, assign to instrument, preview. WAV/MP3 includes samples.",
                     "orders": "L: loop song at playlist end. Tab: orders/bank. N: new. Shift+N: duplicate. Bank Enter: edit.",
                     "settings": "F12: shared SID filter, speed/tempo, helper and audio buffer. Bigger buffers trade latency for more scheduling headroom.",
                     "info": "Three hardware SID voices. This panel follows playback and audition."}.get(app.page, "SIDpulse Tracker")
            second = "F1: help | F2: pattern | F4: instruments | F9: open | F10: save | Ctrl+Alt +/-: zoom"
        mouse = pg.mouse.get_pos()
        for rect, action, value in reversed(self.hits):
            if rect.collidepoint(mouse):
                if action == "activity_indicator":
                    first = ("Instrument activity: bright on note triggers, lit while gated; short visual decay after attacks."
                             if value[0] == 'instrument' else
                             "Sample slots map to instruments; instrument activity includes PCM triggers.")
                    second = "Indicators follow playback and audition, not the selected row. They are not loudness meters."
                if action == "waveform":
                    first = f"{WAVES[value].title()}: select the SID oscillator waveform for this instrument."
                elif action in ("mute", "solo"):
                    first = f"{action.title()} SID voice {value + 1}. Preview monitor only; your pattern data stays intact."
                    second = "Alt+F1/F2/F3: mute voices 1/2/3 | Alt+F9: mute current | Alt+F10: solo current; repeat restores mutes"
                elif action in ('instrument_mute','instrument_solo'):
                    first = f"{action.split('_')[1].title()} instrument {value:02d} across all three voices. Preview only."
                    second = 'Repeat S to restore instrument mutes. Channel M/S still applies. Song and exports stay unchanged.'
                elif action == 'bank_monitor_disabled':
                    first = ('Use the assigned instrument M/S controls to monitor this sample.' if value[0]=='sample'
                             else f'Instrument {value[1]:02d} is empty: nothing to mute or solo.')
                elif action == 'choose_sample':
                    first = f'Select sample slot {value:02d}. Import PCM, then assign it to an instrument.'
                elif action == "help_topic":
                    first = f"Open quick help for {HELP_TOPIC_NAMES[value]}."
                elif action == "choose_instrument":
                    instrument = ed.song.instruments.get(value)
                    first = (f"Select instrument {value:02d}: {instrument.name}." if instrument is not None else
                             f"Empty instrument slot {value:02d}. Enter: Choose preset / No preset / Manual.")
                elif action == "toggle_program":
                    first = "Click or Enter toggles this instrument program. Off keeps its values and drawn steps."
                elif action == 'song_title_settings':
                    first = 'Open F12 Song Variables with Song title selected.'
                elif action == 'header_instrument':
                    first = f'Open instrument {value:02d} in the F4 instrument editor.'
                elif action in ('copy_instrument','paste_instrument'):
                    first = ('Copy the complete instrument and its assigned sample.' if action=='copy_instrument' else
                             'Paste into the selected instrument slot. Occupied slots require confirmation; undo is available.')
                elif action == 'control_panel_toggle':
                    first = ('Collapse' if self.control_visible else 'Expand') + ' CTRL CH / FILTER. Display only; filter automation keeps playing.'
                elif action == 'select_field':
                    first = 'Select this field across all rows. Drag cells or use Shift+arrows for a smaller block.'
                elif action == 'pattern_arpeggio':
                    first = f'Write an arpeggio command at row {ed.row:03d}, CH {value+1}: OFF / ON / instrument / hold.'
                    second = 'AR column: 0 OFF, 1 ON, R instrument, . hold. OFF also suppresses Jxy; other pitch programs stay active.'
                elif action == 'pattern_select_all':
                    first = 'Select every row, channel and field in the current pattern.'
                elif action == 'reset_automation':
                    first = 'Reset all A D S R PW to instrument defaults at this cell, or across selected rows/channels.'
                    second = 'Writes reset commands; keeps notes, instruments and FX. Ctrl+Backspace undoes the entire action.'
                elif action in ('pattern_cut','pattern_copy','pattern_paste','paste_special'):
                    first = {'pattern_cut':'Cut selected fields (Alt+Z). Confirmation is on by default. Ctrl+Backspace: undo.',
                             'pattern_copy':'Copy selected fields (Alt+C). No selection copies the whole current cell.',
                             'pattern_paste':'Paste copied fields at this row/channel (Alt+O); field names stay the same.',
                             'paste_special':'Paste notes, automation, or both (Ctrl+Shift+V). Only copied fields are available.'}[action]
                elif action in ('octave','octave_reset'):
                    first = ('Reset audition / note-entry octave to 4.' if action=='octave_reset' else
                             ('Raise' if value>0 else 'Lower') + ' audition / note-entry octave by one. Range: 0..7.')
                    second = 'Current octave is shown beside the buttons. Existing notes and instruments stay unchanged.'
                elif action == 'pulse_record_arm':
                    first = 'Record A, D, S, R or PW: choose one channel, arm, and adjust the slider during playback.'
                elif action == 'pulse_record_target':
                    first = 'Choose which of the three channels receives the automation recording.'
                break
        if app.page in ('pattern', 'instrument') and time.monotonic() - ed.status_time < 4:
            second = 'Last action: ' + ed.status
        max_width = self.screen.get_width() - 2 * self.cw
        for i, line in enumerate((first, second)):
            while line and self.small_font.size(line)[0] > max_width:
                line = line[:-2]
            self.screen.blit(self.small_font.render(line, True, TEXT if i == 0 else DIM),
                             (self.cw, round(y * self.rh) + i * self.small_font.get_linesize()))

    def preset_dialog(self,app):
        from types import SimpleNamespace
        d=app.dialog;self.hits=[]
        shade=pg.Surface(self.screen.get_size(),pg.SRCALPHA);shade.fill((0,0,0,175));self.screen.blit(shade,(0,0))
        w=min(94,self.cols-4);h=min(12 if d['mode']=='choice' else 25,self.lines-3)
        x=(self.cols-w)//2;y=(self.lines-h)//2
        self.panel(x,y,w,h,'Add SID instrument')
        button(self,x+w-4,y+.1,3,'x','preset_cancel')
        if d['mode']=='choice':
            target=d.get('target_slot')
            self.text(x+2,y+3,f'Create instrument {target:02d}' if target else 'Create a new SID instrument',TEXT,w-4)
            self.text(x+2,y+5,'Choose a preset, start blank, or enter parameters manually.',TEXT,w-4)
            for i,label in enumerate(('Choose preset','No preset','Manual')):
                button(self,x+2+i*19,y+h-3,18,label,'new_choice',i,d['choice_index']==i)
            return
        button(self,x+2,y+1,16,'Presets','chooser_mode','presets',d['mode']=='presets')
        button(self,x+19,y+1,23,'Manual parameters','chooser_mode','manual',d['mode']=='manual')
        self.text(x+2,y+3,'Left/Right: Presets / Manual | Tab: list / choices / buttons',TEXT,w-4)
        if d['mode']=='presets':
            button(self,x+2,y+5,16,'Built-in','chooser_source','builtin',d['source']=='builtin')
            button(self,x+19,y+5,16,'User presets','chooser_source','user',d['source']=='user')
            categories=list(dict.fromkeys(category for category,_ in d['presets']))
            current=d['presets'][d['preset_index']][0] if d['presets'] else None
            category_step = min(1.5, (h - 10) / max(1, len(categories)))
            for i,category in enumerate(categories):
                caption = 'Wavetable drums' if category == '[Wavetable] Drums & Percussion' else category
                button(self,x+2,y+7+i*category_step,18,caption,'preset_category',category,current==category,
                       height=min(1.25, category_step))
            listing=[];previous=None
            for i,(category,inst) in enumerate(d['presets']):
                if category!=previous:listing.append((None,category));previous=category
                listing.append((i,inst.name))
            count=max(1,h-10)
            selected_row=next((row for row,(i,_) in enumerate(listing) if i==d['preset_index']),0)
            start=max(0,selected_row-count+1)
            start=self.scroll_start('presets',start,(d['source'],d['preset_index']),len(listing),count)
            self.well(x+22,y+7,w-24,count)
            if not listing:self.text(x+23,y+8,'No user presets. Save one from the bank.',CREAM,w-26)
            for row,(i,label) in enumerate(listing[start:start+count]):
                yy=y+7+row
                if i is None:
                    self.rect(x+22.2,yy,w-24.4,1,SELECT)
                    self.text(x+23,yy,label.upper(),CREAM,w-28)
                else:
                    selected=i==d['preset_index']
                    if selected:self.rect(x+22.2,yy,w-24.4,1,SELECT)
                    self.text(x+24,yy,label,YELLOW if selected else CREAM,w-29)
                    self.hit(x+22,yy,w-24,1,'preset_select',i)
            self.scroll_bar('presets',x+w-3.5,y+7,count,len(listing),count)
        else:
            proxy=SimpleNamespace(editor=SimpleNamespace(song=SimpleNamespace(instruments={1:d['manual']}),instrument=1),
                                  property_index=d['manual_index'],instrument_focus='properties')
            draw_fields(self,proxy,x+2,y+5,y+h-4,False,right=x+w-2)
            button(self,x+w-19,y+1,17,'Blank instrument','manual_blank')
        button(self,x+2,y+h-2,17,'Add instrument','preset_add',selected=d['chooser_focus']=='buttons' and d['chooser_button']==0)
        button(self,x+21,y+h-2,10,'Cancel','preset_cancel',selected=d['chooser_focus']=='buttons' and d['chooser_button']==1)
        self.text(x+33,y+h-2,'F8: stop | Note keys: audition',TEXT,w-35)
        if d['chooser_focus']=='catalog':
            catalog=([('chooser_source','builtin'),('chooser_source','user')]+[('preset_category',c) for c in dict.fromkeys(c for c,_ in d['presets'])]) if d['mode']=='presets' else [('manual_blank',None)]
            target=catalog[d['catalog_button']%len(catalog)]
            for rect,action,value in self.hits:
                if (action,value)==target:pg.draw.rect(self.screen,YELLOW,rect.inflate(-4,-4),2)


    def dialog(self, app):
        self.scrollbars.visible.clear()
        dialog = app.dialog
        minimum_lines = 26 if dialog.get('kind') in ('sample_synthesis','sample_synthesis_batch','pcm_export_confirm') else 23 if dialog.get('kind') == 'audio_buffer' else 22 if dialog.get('kind') in ('automation_recording','sample_squeeze') else 18
        if self.cols < 54 or self.lines < minimum_lines:
            fit = min(self.cols / 54, self.lines / minimum_lines) * .9
            # These dimensions already include the page's minimum-fit fallback.
            # Applying their ratio to the requested zoom can enlarge the dialog.
            self.configure(app.screen, self.signature[2] * fit, app.appearance)
        if dialog.get('kind') == 'pcm_export_confirm':
            from sidpulse.ui.batch_synthesis import draw_confirm
            draw_confirm(self,app);return
        if dialog.get('kind') == 'sample_synthesis_batch':
            from sidpulse.ui.batch_synthesis import draw
            draw(self,app);return
        if dialog.get('kind') == 'sample_volume':
            from sidpulse.ui.sample_volume import draw
            draw(self, app);return
        if dialog.get('kind') == 'sample_synthesis':
            from sidpulse.ui.sample_synthesis import draw
            draw(self, app);return
        if dialog.get('kind') == 'sample_squeeze':
            from sidpulse.ui.sample_view import draw_squeeze
            draw_squeeze(self,app);return
        if dialog.get('kind') == 'media_job':
            from sidpulse.ui.media_actions import draw_job
            draw_job(self,app);return
        if dialog.get('kind') == 'automation_recording':
            from sidpulse.ui.automation_recording import draw
            draw(self, app)
            return
        if dialog.get('kind') == 'export_squeezer':
            from sidpulse.ui.export_squeezer import draw
            draw(self, app)
            return
        if dialog.get('kind') == 'welcome':
            from sidpulse.ui.welcome import draw
            draw(self, app)
            return
        if dialog.get('kind') == 'autosave_settings':
            from sidpulse.ui.autosave_settings import draw
            draw(self,app)
            return
        if dialog.get('kind') == 'pattern_length':
            from sidpulse.ui.pattern_length import draw
            draw(self,app)
            return
        if dialog.get('kind') == 'audio_buffer':
            from sidpulse.ui.audio_buffer import draw
            draw(self, app)
            return
        if "presets" in dialog:
            self.preset_dialog(app);return
        self.hits=[]
        shade = pg.Surface(self.screen.get_size(), pg.SRCALPHA)
        shade.fill((0, 0, 0, 175))
        self.screen.blit(shade, (0, 0))
        w = max(12, min(86, self.cols - 4))
        height=min(21,self.lines-2) if dialog.get("multiline") else 15 if dialog.get("logo") else 11 if "confirm_instrument" in dialog else 12 if any(k in dialog for k in ("yes","discard")) or dialog.get("kind") in ("paste_special","keyboard_mapping","pattern_arpeggio") else 10
        if dialog.get('kind') == 'pattern_edit_confirm':
            height = 14
        x, y = max(0, (self.cols - w) // 2), max(0, (self.lines - height) // 2)
        self.panel(x, y, w, height, dialog["title"])
        if dialog.get("logo"):
            width=max(1,min(round(427*app.zoom),round((w-4)*self.cw),round(self.rh*5*427/105)))
            size=(width,max(1,round(width*105/427)))
            if size not in self.logo_cache:
                path=Path(__file__).resolve().parents[1]/"assets/sidpulse-tracker-logo.svg"
                self.logo_cache[size]=pg.image.load_sized_svg(str(path),size)
            self.screen.blit(self.logo_cache[size],(round((self.screen.get_width()-width)/2),round((y+1.3)*self.rh)))
            frame=pg.Rect(round(x*self.cw),round(y*self.rh),round(w*self.cw),round(height*self.rh))
            pg.draw.rect(self.screen,CREAM,frame,2)
            pg.draw.rect(self.screen,EDGE,frame.inflate(-6,-6),2)
            button(self,x+w-4,y+.1,3,'x','dialog_button',pg.K_ESCAPE)
            self.rect(x+.5,y+.1,w-5,1,BG)
            self.text(x+(w-len(dialog['title']))/2,y+.1,dialog['title'],TEXT,w-8)
            for i,line in enumerate((f"SIDpulse Tracker {__version__}","Harry Horsperg / FlyingFathead", "An homage to Impulse Tracker", "Single SID / three voices / one shared filter", "", "Enter / Esc: close")):
                self.text(x+(w-len(line))/2,y+7+i,line,TEXT,w-4)
            return
        message = dialog.get("message", "")
        message_lines = textwrap.wrap(message, max(10, w - 6))
        message_visible = 3 if 'text' in dialog else max(3,height-6)
        message_start = self.scroll_start('message',0,message,len(message_lines),message_visible)
        for i, line in enumerate(message_lines[message_start:message_start+message_visible]):
            self.text(x + 2, y + 1 + i, line, TEXT, w - 6)
        self.scroll_bar('message',x+w-3.5,y+1,message_visible,len(message_lines),message_visible)
        if "confirm_instrument" in dialog:
            button(self,x+2,y+7,10,"OK","confirm_instrument",True,dialog["confirm_selected"])
            button(self,x+14,y+7,12,"Cancel","confirm_instrument",False,not dialog["confirm_selected"])
            self.text(x+2,y+9,"Tab / arrows: choose | Enter: accept | Esc: cancel",TEXT,w-4)
            return
        if "text" in dialog:
            self.well(x + 2, y + 4, w - 4, height-7)
            value = dialog["text"]
            if dialog.get("multiline"):
                lines=[part for line in (value+"_").split('\n') for part in (textwrap.wrap(line,max(1,w-7)) or [''])]
                count=max(1,height-7)
                start=self.scroll_start('comments',max(0,len(lines)-count),value,len(lines),count)
                for i,line in enumerate(lines[start:start+count]):self.text(x+2,y+4+i,line,YELLOW,w-6)
                self.scroll_bar('comments',x+w-3.5,y+4,count,len(lines),count)
            else:self.text(x + 2, y + 4, value[-max(1, w - 5):] + "_", YELLOW, w - 4)
            hint = "Enter: accept | Esc: cancel | Ctrl+A: replace"
        else:
            hint = dialog.get("hint", "Enter / Esc: close")
        from sidpulse.ui.dialogs import choices,focus
        if dialog.get('kind') == 'pattern_edit_confirm' and dialog['operation'] == 'cut':
            label = ('[x]' if dialog['skip_next_time'] else '[ ]') + " Don't show this again"
            self.text(x+2,y+height-5,label,TEXT,w-4)
            checkbox = pg.Rect((x+2)*self.cw,(y+height-5)*self.rh,(w-4)*self.cw,self.rh)
            self.hits.append((checkbox,'cut_confirmation_checkbox',None))
            if dialog['button_focus'] == 2:
                pg.draw.rect(self.screen,SELECT,checkbox,1)
        bx=x+2
        for i,(label,key) in enumerate(choices(dialog)):
            width=len(label)+4
            button(self,bx,y+height-3,width,label,'dialog_button',key,i==focus(dialog))
            bx+=width+1
        self.text(x+2,y+height-1.5,dialog.get('error','Tab / arrows: choose | Enter: activate | Esc: cancel'),TEXT,w-4)
