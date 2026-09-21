"""Native pygame shell. All song mutations go through reversible editor commands."""
from copy import deepcopy
import logging
import time
from pathlib import Path
import pygame as pg

from sidpulse.audio.engine import AudioEngine
from sidpulse import __version__
from sidpulse.preferences import BUFFERS, THEMES, load_preferences, save_buffer, load_appearance, save_preferences, config_path, load_file_browser_dates, load_restart_on_f5
from sidpulse.commands.editor import Editor, FIELDS
from sidpulse.ui.pattern_grid import PatternGrid
from sidpulse.project.format import load, save
from sidpulse.song.model import Cell, ControlCell, Instrument, Song
from sidpulse.ui.keyboard import Command, dispatch
from sidpulse.ui.renderer import Renderer, HELP_TOPIC_NAMES
from sidpulse.ui.menus import menu_items
from sidpulse.ui.instruments import FIELDS as INSTRUMENT_FIELDS, SEQUENCES, LIMITS, display
from sidpulse.export.psid import compile_song, save_export

LOG = logging.getLogger("sidpulse.keys")


from sidpulse.ui.instrument_actions import InstrumentActions
from sidpulse.ui.media_actions import MediaActions
from sidpulse.ui.file_actions import FileActions
from sidpulse.ui.file_browser import FileBrowser
from sidpulse.ui.pulse_recording import PulseRecordingActions
from sidpulse.ui.pattern_clipboard import PatternClipboardActions


class App(MediaActions, PatternClipboardActions, PulseRecordingActions, InstrumentActions, FileActions):
    def __init__(self, song=None, path=None, audio=True, size=(1280, 900), zoom=1.0, audio_buffer=None):
        from sidpulse.ui.window_identity import prepare, set_icon
        prepare()
        pg.display.init()
        pg.font.init()
        set_icon()
        self.screen = pg.display.set_mode(size, pg.RESIZABLE)
        pg.display.set_caption(f"SIDpulse Tracker {__version__}")
        pg.key.set_repeat(350, 55)
        self.editor = Editor(song)
        from sidpulse.preferences import load_center_selection
        self.editor.centered = load_center_selection()
        self.audio_buffer = load_preferences() if audio_buffer is None else audio_buffer
        from sidpulse.preferences import load_audio_output_device
        self.audio_output_device = load_audio_output_device()
        output_options = {'output_device': self.audio_output_device} if self.audio_output_device else {}
        self.audio = AudioEngine(self.editor.song, audio, self.audio_buffer, **output_options)
        from sidpulse.preferences import load_audio_underrun_detection
        self.audio_underrun_detection = load_audio_underrun_detection()
        self.audio_warning = ''
        self.audio_warning_until = 0.0
        self.last_audio_gaps = self.last_audio_late_callbacks = 0
        self.last_audio_revision = 0
        self.audio_configuration = (self.editor.song.sid_model,self.editor.song.clock)
        self.follow_playback = False
        self.playback_mark = None
        self.appearance = load_appearance()
        self.renderer = Renderer()
        self.page = "pattern"
        self.previous_page = "pattern"
        self.property_index = 0
        self.instrument_focus = "list"
        self.instrument_slot = 1
        self.instrument_tab = "general"
        self.instrument_button = 3
        self.instrument_drag = None
        self.instrument_clipboard = None
        self.pulse_record_armed = False
        self.pulse_record_voice = self.editor.voice
        self.pulse_record_value = 0x800
        self.automation_parameter = 'pulse_width'
        self.automation_values = {'attack':8,'decay':8,'sustain':8,'release':8,'pulse_width':0x800}
        from sidpulse.preferences import load_automation_display
        self.automation_display = load_automation_display()
        self.automation_state = {'focus': 3}
        self.pulse_record_serial = 0
        self.pulse_take = None
        self.pulse_deferred_events = []
        self.graph_field = "arpeggio"
        self.graph_step = self.graph_page = 0
        self.graph_low = -12
        self.control_focus = False
        self.sample_index = 1
        self.sample_drag = None
        from sidpulse.preferences import load_sample_auto_squeeze, load_sample_normalization
        self.sample_auto_squeeze = load_sample_auto_squeeze()
        self.sample_normalize_before, self.sample_normalize_after = load_sample_normalization()
        self.help_scroll = 0
        self.help_topic = 0
        self.helper_strip = True
        from sidpulse.preferences import load_pattern_clipboard_buttons, load_control_panel_visibility, load_channel_visualizers
        self.pattern_clipboard_buttons = load_pattern_clipboard_buttons()
        from sidpulse.preferences import load_pattern_fit_three
        self.pattern_fit_three = load_pattern_fit_three()
        from sidpulse.preferences import load_confirm_cut
        self.confirm_cut = load_confirm_cut()
        from sidpulse.preferences import load_instrument_monitor_buttons
        self.instrument_monitor_buttons = load_instrument_monitor_buttons()
        self.pattern_drag = None
        self.pattern_reset_entry = None
        self.button_press = self.button_flash = None
        self.clipboard_notice = None
        from sidpulse.preferences import load_keyboard_mapping
        self.keyboard_mapping = load_keyboard_mapping()
        self.control_panel_visible = load_control_panel_visibility()
        self.channel_visualizers = load_channel_visualizers()
        self.muted = [False, False, False]
        self.solo_voice = None
        self.muted_instruments = set()
        self.solo_instrument = None
        self.zoom = max(.5, min(3.0, zoom))
        self.path = Path(path).expanduser() if path else None
        self.running = True
        self.fullscreen = False
        self.window_size = size
        self.dialog = None
        self.settings_reset_pending = None
        self.export_jobs = []
        self.media_jobs = []
        self.intro_pending = False
        self.scopes_visible = False
        self.held = set()
        self.audition_tokens = {}
        self.editor_metadata = {}
        self.browser = FileBrowser(self.path.parent if self.path else Path.cwd())
        if self.path:
            self.browser.remember_project(self.path)
        self.file_browser_show_modified = load_file_browser_dates()
        self.restart_on_f5 = load_restart_on_f5()
        self.after_save = None
        self.menu_path = []
        self.menu_indices = []
        from sidpulse.recovery import Autosave
        self.autosave = Autosave()
        self.diagnostics = None
        self.runtime_started = False
        self.runtime_clean = True
        self.song_loop_key_held = False
        self.order_focus = "orders"
        self.bank_pattern = self.editor.pattern_id
        self.order_draft = None
        self.order_entry_index = 0

    def notice(self, title, message, return_dialog=None):
        self.dialog = {'kind':'notice', 'title':title, 'message':message,
                       'return_dialog':return_dialog}

    def show_autosave_warning(self):
        if self.autosave.warning:
            message, self.autosave.warning = self.autosave.warning, None
            self.notice('Autosave unavailable', message, return_dialog=self.dialog)

    def start_services(self):
        if self.runtime_started: return
        self.runtime_started = True
        self.autosave.start()
        candidates = self.autosave.candidates()
        if candidates:
            marker, data = candidates[0]
            self.dialog = {'title':'Recover previous autosave?', 'recover':(marker,data),
                           'return_dialog':self.dialog,
                           'message':'The previous session did not close cleanly. Load its latest autosave? '
                                     + str(data.get('title','Untitled')) + ' / ' + str(data['autosave'])}
        self.show_autosave_warning()

    def recover_autosave(self, restore):
        dialog = self.dialog
        marker, data = dialog['recover']
        try:
            if restore:
                self.open_project(data['autosave'])
                self.path = Path(data['source']) if data.get('source') else None
                if self.path:
                    self.browser.remember_project(self.path)
                else:
                    self.file_name = 'recovered.sidpulse'
                self.editor.saved = None  # recovery never marks the source as saved
                self.editor.status = 'Autosave recovered. F10 saves your project.'
            self.autosave.acknowledge(marker)
            self.dialog = None if restore else dialog.get('return_dialog')
        except (OSError,ValueError) as exc:
            self.notice('Recovery could not be loaded',str(exc),return_dialog=dialog)

    def panic(self):
        self.intro_pending = False
        self.audio.send("panic")
        self.editor.status="Stopped | F5 song | F6 pattern | F7 mark/row"
        self.held.clear()
        self.audition_tokens.clear()

    def release_audition(self):
        self.audio.send("release_audition")
        self.held.clear()
        self.audition_tokens.clear()

    def start_playback(self, mode):
        if not self.audio.ready:
            self.editor.status = self.audio.error or "Audio not ready. Check the audio status below."
            return
        if mode == 'song' and self.audio.playback.status != 'stopped' and not self.restart_on_f5:
            if not self.inline_recording_visible:self.change_page('info')
            return
        ed = self.editor
        self.release_audition()
        pattern = None
        order = row = 0
        if mode in ("pattern", "pattern_cursor"):
            pattern, order = ed.pattern_id, ed.order
            row = ed.row if mode == "pattern_cursor" else 0
            playback_mode = "pattern"
        elif mode == "order":
            order = ed.order
            playback_mode = "song"
        elif mode == "cursor":
            pattern, row = self.playback_mark or (ed.pattern_id, ed.row)
            if pattern not in ed.song.patterns:
                pattern, row = ed.pattern_id, ed.row
                self.playback_mark = None
            search = list(range(ed.order, len(ed.song.orders))) + list(range(ed.order))
            found = next((i for i in search if ed.song.orders[i] == pattern), None)
            order = ed.order if found is None else found
            playback_mode = "pattern" if found is None else "song"
        else:
            playback_mode = "song"
        self.audio.send("play", ed.song, playback_mode, order, row, pattern)
        self.last_audio_revision = ed.history.revision
        ed.status = "Playing | F8 stop | Shift+F8 pause | F2 editor | Scroll Lock follow"
        if mode in ("song", "restart") and not self.inline_recording_visible:
            self.change_page("info")

    def sync_audio(self):
        self.sync_pulse_recording()
        if self.settings_reset_pending:
            from sidpulse.ui.settings_reset import sync
            sync(self)
        if self.dialog and self.dialog.get('kind') == 'audio_buffer':
            from sidpulse.ui.audio_buffer import sync
            sync(self)
        self.update_audio_warning()
        scopes_visible = self.page == 'info' and self.channel_visualizers
        if scopes_visible != self.scopes_visible:
            self.scopes_visible = scopes_visible
            self.audio.send('scopes', scopes_visible)
        if self.intro_pending and self.dialog is None and (self.audio.ready or self.audio.error):
            self.intro_pending = False
            if self.audio.ready:
                self.start_playback('song')
            else:
                self.editor.status = self.audio.error
        ed = self.editor
        configuration=(ed.song.sid_model,ed.song.clock)
        if configuration!=self.audio_configuration:
            self.audio.configure(ed.song)
            self.audio_configuration=configuration
        if ed.history.revision != self.last_audio_revision:
            self.prune_instrument_monitor()
            self.audio.send("update_song", ed.song)
            self.last_audio_revision = ed.history.revision
        state = self.audio.playback
        if self.follow_playback and state.status == "playing" and self.page == "pattern":
            if state.pattern in ed.song.patterns:
                ed.pattern_id = state.pattern
                ed.row = min(state.row, len(ed.pattern.rows) - 1)
                ed.order = min(state.order, len(ed.song.orders) - 1)

    def monitor_mask(self):
        # Solo temporarily overrides the mute set; unsolo restores it.
        return tuple(v != self.solo_voice if self.solo_voice is not None else self.muted[v] for v in range(3))

    def preview_monitor_mask(self):
        return self.audio.muted if self.audio.ready else self.monitor_mask()

    def send_instrument_monitor(self):
        self.audio.send('instrument_monitor', tuple(sorted(self.muted_instruments)) if self.instrument_monitor_buttons else (),
                        self.solo_instrument if self.instrument_monitor_buttons else None)

    def toggle_instrument_monitor_buttons(self):
        value = not self.instrument_monitor_buttons
        save_preferences({'instrument_monitor_buttons': value})
        self.instrument_monitor_buttons = value
        self.send_instrument_monitor()
        self.editor.status = 'Instrument/sample M/S: ' + ('ON' if value else 'OFF; instrument mutes bypassed')

    def toggle_instrument_monitor(self, action, number):
        if not self.instrument_monitor_buttons or number not in self.editor.song.instruments:
            return
        if action == 'instrument_mute':
            self.muted_instruments.symmetric_difference_update({number})
        else:
            self.solo_instrument = None if self.solo_instrument == number else number
        self.send_instrument_monitor()
        self.editor.status = f'Instrument {number:02d} monitor updated | M: mute | S: solo; repeat restores mutes'

    def clear_instrument_monitor(self):
        self.pattern_reset_entry = None
        self.muted_instruments.clear()
        self.solo_instrument = None
        self.send_instrument_monitor()

    def prune_instrument_monitor(self):
        muted = self.muted_instruments.intersection(self.editor.song.instruments)
        solo = self.solo_instrument if self.solo_instrument in self.editor.song.instruments else None
        if (muted, solo) != (self.muted_instruments, self.solo_instrument):
            self.muted_instruments, self.solo_instrument = muted, solo
            self.send_instrument_monitor()

    def toggle_monitor(self, action, voice=None):
        voice = self.editor.voice if voice is None else voice
        if action == "mute":
            self.muted[voice] = not self.muted[voice]
        else:
            self.solo_voice = None if self.solo_voice == voice else voice
        self.audio.send("monitor", self.monitor_mask())
        self.editor.status = "Monitor only | Alt+F1/F2/F3 mute voices | Alt+F9 mute current | Alt+F10 solo current"

    def close(self):
        from sidpulse.ui.export_squeezer import close_analysis
        close_analysis(self)
        self.close_media_jobs()
        self.audio.close()
        pg.quit()
        self.autosave.close(clean=self.runtime_clean)

    def restore_metadata(self, data):
        self.editor_metadata = deepcopy(data)
        ed = self.editor
        ed.pattern_grid = PatternGrid.from_metadata(data.get("pattern_grid"))
        for key, lo, hi in (("row", 0, 255), ("voice", 0, 2), ("column", 0, len(FIELDS)-1), ("octave", 0, 7), ("skip", 0, 9)):
            value = data.get(key)
            if type(value) is int and lo <= value <= hi:
                if key == 'column' and data.get('pattern_columns_version', 1) == 1 and value >= 6:
                    value = min(hi, value + 1)  # W was inserted before FX in v0.2.34
                setattr(ed, key, value)
        if type(data.get("pattern_id")) is int and data["pattern_id"] in ed.song.patterns:
            ed.pattern_id = data["pattern_id"]
        if type(data.get("instrument")) is int and data["instrument"] in ed.song.instruments:
            ed.instrument = data["instrument"]
        if type(data.get("order")) is int and 0<=data["order"]<len(ed.song.orders):
            ed.order=data["order"]
        zoom = data.get("zoom")
        if type(zoom) in (float, int) and .5 <= zoom <= 3:
            self.zoom = zoom
        if type(data.get("helper_strip")) is bool:
            self.helper_strip = data["helper_strip"]
        ed.repair_cursor()
        from sidpulse.project.format import compatibility_warnings
        warnings = compatibility_warnings(ed.song)
        if warnings:
            self.notice('Project compatibility', '\n'.join(warnings))

    def metadata(self):
        result = deepcopy(self.editor_metadata)
        for key in ("row", "voice", "column", "octave", "skip", "pattern_id", "instrument", "order"):
            result[key] = getattr(self.editor, key)
        result["zoom"] = self.zoom
        result['pattern_columns_version'] = 2
        result["helper_strip"] = self.helper_strip
        result["pattern_grid"] = self.editor.pattern_grid.metadata(result.get("pattern_grid"))
        return result

    def text_dialog(self, title, initial, callback, message=""):
        self.release_audition()
        self.dialog = {"title": title, "text": str(initial), "callback": callback, "message": message, "select_all": True}
        pg.key.start_text_input()

    def update_audio_warning(self):
        # Startup/audio-disabled adapters may not have published diagnostics yet.
        gaps = getattr(self.audio, 'underruns', 0)
        late = getattr(self.audio, 'late_callbacks', 0)
        if self.audio_underrun_detection:
            if gaps > self.last_audio_gaps:
                self.audio_warning = 'Buffer underrun: configure audio with Alt+F12.'
                self.audio_warning_until = time.monotonic() + 12
            elif late > self.last_audio_late_callbacks:
                self.audio_warning = 'Late audio callback: check audio with Alt+F12.'
                self.audio_warning_until = time.monotonic() + 12
        else:
            self.audio_warning = ''
            self.audio_warning_until = 0.0
        self.last_audio_gaps, self.last_audio_late_callbacks = gaps, late

    def apply_audio_buffer(self, value, detection=None):
        if value not in BUFFERS:
            raise ValueError('Unsupported audio buffer size')
        if detection is None:
            save_buffer(value)
        else:
            if type(detection) is not bool:
                raise ValueError('Audio underrun detection must be true or false')
            save_preferences({'audio_buffer': value, 'audio_underrun_detection': detection})
            self.audio_underrun_detection = detection
            self.audio_warning = ''
            self.audio_warning_until = 0.0
            self.last_audio_gaps = self.audio.underruns
            self.last_audio_late_callbacks = self.audio.late_callbacks
        if value != self.audio_buffer:
            self.audio_buffer = value
            self.audio.send('buffer', value)
        self.editor.status = f'Audio buffer default: {value} samples ({value / 48:.2f} ms per block).'

    def save_audio_settings(self, frames, detection, device):
        from sidpulse.preferences import valid_output_device
        if frames not in BUFFERS or type(detection) is not bool or not valid_output_device(device):
            raise ValueError('Invalid audio settings')
        save_preferences({'audio_buffer': frames, 'audio_underrun_detection': detection,
                          'audio_output_device': device})
        self.audio_buffer = frames
        self.audio_output_device = device
        self.audio_underrun_detection = detection
        self.audio_warning = ''
        self.audio_warning_until = 0.0
        self.last_audio_gaps = self.audio.underruns
        self.last_audio_late_callbacks = self.audio.late_callbacks
        self.editor.status = f'Audio settings saved: {device or "System default"} / {frames} samples.'

    def confirm_discard(self, callback):
        self.release_audition()
        if not self.editor.dirty:
            callback()
        else:
            self.dialog = {"title": "Unsaved .sidpulse project", "message": "Save your edits before continuing?",
                           "hint": "S: save | D: discard | Esc: cancel", "discard": callback}

    def confirm_action(self, title, message, callback):
        self.finish_instrument_drag()
        self.release_audition()
        self.after_save = None
        self.dialog = {"title": title, "message": message + " Continue?", "yes": callback}

    def confirm_quit(self):
        self.finish_instrument_drag()
        self.release_audition()
        self.after_save = None
        self.dialog = {"title": "Quit SIDpulse Tracker?", "quit": True,
                       "message": "Quit SIDpulse Tracker?"}
        if self.editor.dirty:
            self.dialog.update(message="There are unsaved changes. Save before quitting, or discard them and quit?",
                               discard=lambda: setattr(self, "running", False))
        else:
            self.dialog["yes"] = lambda: setattr(self, "running", False)

    def clear_project_data(self, kind):
        self.panic()
        ed = self.editor
        if kind == 'clear_patterns':
            patterns = deepcopy(ed.song.patterns)
            for pattern in patterns.values():
                pattern.rows = [[Cell() for _ in range(3)] for _ in pattern.rows]
                pattern.controls.clear()
            ed.edit('Clear all pattern data', [(('patterns',), patterns)])
        else:
            ed.edit('Clear all instruments', [(('instruments',), {})])
            self.instrument_slot = ed.instrument
            self.instrument_focus = 'list'

    def save_project(self, destination=None):
        if destination is None and self.path is None:
            self.browse("save")
            return
        try:
            self.path = save(destination or self.path, self.editor.song, self.metadata())
            self.browser.remember_project(self.path)
            self.editor.mark_saved()
            self.editor.status = f"Saved {self.path.name}"
            if self.page == "files":
                self.page = self.browser.return_page
            self.sync_file_text_input()
            if self.after_save:
                callback, self.after_save = self.after_save, None
                callback()
        except (OSError, ValueError) as exc:
            self.editor.status = f"Save failed: {exc}"
            raise

    def open_project(self, path):
        song, metadata = load(path)
        self.panic()
        self.clear_instrument_monitor()
        self.pulse_record_armed = False
        self.editor = Editor(song)
        from sidpulse.preferences import load_center_selection
        self.editor.centered = load_center_selection()
        self.last_audio_revision = 0
        self.audio_configuration = (self.editor.song.sid_model,self.editor.song.clock)
        self.playback_mark = None
        self.restore_metadata(metadata)
        self.instrument_slot = self.sample_index = 1
        self.path = Path(path).expanduser()
        self.browser.remember_project(self.path)
        self.audio.configure(song)
        self.page = "pattern"
        self.editor.status = f"Loaded {self.path.name}"
        self.sync_file_text_input()

    def new_project(self):
        self.panic()
        self.clear_instrument_monitor()
        self.pulse_record_armed = False
        self.editor = Editor(Song())
        from sidpulse.preferences import load_center_selection
        self.editor.centered = load_center_selection()
        self.instrument_slot = self.sample_index = 1
        self.instrument_focus = "list"
        self.last_audio_revision = 0
        self.audio_configuration = (self.editor.song.sid_model,self.editor.song.clock)
        self.playback_mark = None
        self.editor_metadata = {}
        self.path = None
        self.browser.set_name("untitled.sidpulse")
        self.browser.export_result = None
        self.page = "pattern"
        self.sync_file_text_input()
        self.audio.configure(self.editor.song)

    def change_page(self, page):
        self.automation_state.pop('slider_keys',None)
        self.automation_state.pop('keyboard_touch',None)
        self.pattern_reset_entry = None
        self.finish_pattern_selection()
        self.button_press = self.button_flash = None
        if self.page == 'orders':
            from sidpulse.ui.orders import commit_entry
            if not commit_entry(self): return
        self.finish_instrument_drag()
        self.release_audition()
        if page == "help" and self.page != "help":
            self.previous_page = self.page
            self.help_topic = {"pattern": 1, "instrument": 2, "samples": 3, "files": 4, "orders": 4, "info": 5, "settings": 6}.get(self.page, 0)
            self.help_scroll = 0
        if page == "orders" and self.page != "orders":
            self.bank_pattern = self.editor.pattern_id
            self.order_entry_index = self.editor.order
        leaving_files = self.page == "files" and page != "files"
        self.page = page
        if leaving_files:
            if page != "help":
                self.after_save = None
                self.browser.export_result = None
            self.sync_file_text_input()
        elif page == "files":
            self.sync_file_text_input()
        self.property_index = 0
        self.instrument_focus = "list"
        # Bank navigation survives view changes, including empty slots. The
        # pattern note-entry instrument must not move the bank's highlight.
        if page == "instrument" and self.instrument_slot in self.editor.song.instruments:
            self.editor.instrument = self.instrument_slot
        self.instrument_tab = "general"
        self.instrument_button = 3
        self.instrument_drag = None
        self.graph_field = "arpeggio"
        self.graph_step = self.graph_page = 0
        self.graph_low = -12

    def open_menu(self, title="Main Menu"):
        self.pattern_reset_entry = None
        self.button_press = self.button_flash = None
        self.release_audition()
        self.menu_path = [title]
        self.menu_indices = [0]

    def activate_menu(self, index):
        items = menu_items(self.menu_path[-1])
        item = items[index]
        if not item.enabled:
            self.editor.status = f"{item.value}: not implemented yet"
            return
        if item.command == "submenu":
            self.menu_indices[-1] = index
            self.menu_path.append(item.value)
            self.menu_indices.append(0)
        else:
            self.menu_path.clear()
            self.menu_indices.clear()
            self.execute(Command(item.command, item.value))

    def menu_event(self, event):
        if event.type == pg.KEYDOWN:
            key = event.key
            if key in (pg.K_ESCAPE, pg.K_LEFT):
                self.menu_path.pop()
                self.menu_indices.pop()
            elif key in (pg.K_DOWN, pg.K_UP):
                count = len(menu_items(self.menu_path[-1]))
                self.menu_indices[-1] = (self.menu_indices[-1] + (1 if key == pg.K_DOWN else -1)) % count
            elif key in (pg.K_RETURN, pg.K_RIGHT):
                self.activate_menu(self.menu_indices[-1])
            elif key == pg.K_q:
                self.menu_path.clear()
                self.execute(Command("quit"))
            else:
                command = dispatch(event, self.page, self.editor.column, self.keyboard_mapping)
                if command and command.name in ("page", "open", "save", "quick_save", "save_as", "panic", "comments", "fullscreen", "pending", "play", "pause"):
                    self.menu_path.clear()
                    self.execute(command, event)
        elif event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
            for rect, action, value in reversed(self.renderer.hits):
                if action == "menu" and rect.collidepoint(event.pos):
                    self.activate_menu(value)
                    break

    def edit_control(self):
        ed=self.editor
        keys=("cutoff","resonance","routing","mode","volume","slide")
        control=ed.pattern.controls.get(ed.row,ControlCell())
        initial=' '.join('.' if getattr(control,k) is None else str(getattr(control,k)) if k=='slide' else f'{getattr(control,k):X}' for k in keys)
        row,pid=ed.row,ed.pattern_id
        def accept(text):
            values=text.replace(',',' ').split()
            if len(values)!=6:raise ValueError("Enter six values: cutoff res route mode volume slide")
            new=ControlCell(**{k:None if v in ('.','..','-') else int(v,10 if k=='slide' else 16) for k,v in zip(keys,values)})
            controls=deepcopy(ed.song.patterns[pid].controls)
            if new==ControlCell():controls.pop(row,None)
            else:controls[row]=new
            from sidpulse.project.format import validate
            check=deepcopy(ed.song);check.patterns[pid].controls=controls;validate(check)
            ed.edit("Edit filter row",[(("patterns",pid,"controls"),controls)])
        self.text_dialog(f"CTRL CH / FILTER row {row:03d}",initial,accept,
                         "Cutoff 000..7FF, res 0..F, route 0..7, mode 00/10/20/40, volume 0..F (hex); slide signed decimal. Dot keeps previous value.")

    def poll_export_analysis(self):
        from sidpulse.ui.export_squeezer import poll_analysis
        poll_analysis(self)

    def begin_export(self, kind='sid'):
        from sidpulse.ui.export_squeezer import open_dialog
        open_dialog(self, kind)

    def change_property(self, delta=0, direct=None):
        ed = self.editor
        if self.page=='instrument' and not self.allow_instrument_edit():return
        index = self.property_index
        if self.page=='instrument' and ed.instrument in ed.song.instruments and ed.song.instruments[ed.instrument].sample_override:
            from sidpulse.ui.instruments import PCM_FIELDS
            if index not in PCM_FIELDS:return
        if self.page == 'settings' and index == 29:
            self.open_keyboard_mapping()
            return
        if self.page == 'settings' and index == 28:
            self.toggle_channel_visualizers()
            return
        if self.page == 'settings' and index == 27:
            self.toggle_control_panel()
            return
        if self.page == 'settings' and index == 26:
            self.toggle_pattern_clipboard_buttons()
            return
        if self.page == 'settings' and index in (24, 25):
            field = 'rows_per_beat' if index == 24 else 'beats_per_bar'
            ed.pattern_grid = ed.pattern_grid.changed(field, delta=delta, direct=direct)
            grid = ed.pattern_grid
            ed.status = (f'Grid: {grid.rows_per_beat} rows/beat, {grid.rows_per_bar} rows/bar. '
                         'Display only; Ctrl+S saves it with this project.')
            return
        if self.page == 'settings' and index == 23:
            value = not self.restart_on_f5 if direct is None else str(direct).lower() in ('1','true','on','yes')
            save_preferences({'restart_on_f5': value})
            self.restart_on_f5 = value
            ed.status = 'Restart on repeated F5: ' + ('ON' if value else 'OFF') + ' | Ctrl+F5 always restarts'
            return
        if self.page == "instrument":
            fields = INSTRUMENT_FIELDS
            field = fields[index]
            value = getattr(ed.song.instruments[ed.instrument], field)
            path = ("instruments", ed.instrument, field)
            if field in SEQUENCES:
                if direct is None:
                    self.text_dialog(field, display(ed.song.instruments[ed.instrument],field), lambda text:self.change_property(direct=text),
                                     "Up to 64 values. Arp/pitch: signed decimal semitones. Waves: 10 20 40 80 hex. Empty: off.")
                    return
                text=direct.strip().replace(',', ' ')
                values=[] if text in ('','(off)') else [int(v,16 if field=='wave_sequence' else 10) for v in text.split()]
                if len(values)>64 or any((v not in (16,32,64,128)) if field=='wave_sequence' else not -48<=v<=48 for v in values):
                    raise ValueError("Use <=64 valid wave bytes or semitone offsets -48..48")
                ed.edit(f"Set {field}",[(path,values)])
                return
            if field in LIMITS:
                lo,hi=LIMITS[field]
                new=int(direct) if direct is not None else max(lo,min(hi,value+delta))
                if not lo<=new<=hi:raise ValueError(f"Use {lo}..{hi} decimal")
                ed.edit(f"Set {field}",[(path,new)])
                return
            maxval = 4095 if field == "pulse_width" else 15
            choices = [16, 32, 64, 128] if field == "waveform" else None
        else:
            fields = ("title", "author", "sid_model", "zoom", "cutoff", "resonance", "routing", "mode", "volume", "comments", "helper_strip", "speed", "tempo", "audio_buffer", "released", "export_loop", "clock", "theme", "font_size", "font_bold", "font_file", "file_browser_show_modified")
            field = fields[index]
            if field == "file_browser_show_modified":
                value = str(direct).lower() in ('1','true','on','yes') if direct is not None else not self.file_browser_show_modified
                save_preferences({'file_browser_show_modified': value})
                self.file_browser_show_modified = value
                return
            if field == "export_loop":
                ed.set_song_loop(None if direct is None else str(direct).lower() in ('on','true','1','yes'))
                return
            if field == "released":
                value=ed.song.export_config.get("released", '2026 SIDpulse')
                if direct is None:
                    self.text_dialog("PSID released",value,lambda text:self.change_property(direct=text))
                    return
                config=deepcopy(ed.song.export_config);config["released"]=direct
                ed.edit("Set export released",[(("export_config",),config)])
                return
            if field in ("theme","font_size","font_bold","font_file"):
                old=self.appearance[field]
                if field=="theme":
                    value=direct if direct is not None else THEMES[(THEMES.index(old)+(1 if delta>=0 else -1))%len(THEMES)]
                    if value not in THEMES:raise ValueError('Choose: '+', '.join(THEMES))
                elif field=="font_size":value=max(12,min(28,int(direct) if direct is not None else old+delta))
                elif field=="font_bold":value=str(direct).lower() in ('1','true','yes','on') if direct is not None else not old
                else:
                    value=direct or ''
                    if value:pg.font.Font(str(Path(value).expanduser()),16)
                self.appearance[field]=value;save_preferences(self.appearance)
                ed.status='Appearance saved: '+str(config_path())
                return
            if field == "clock":
                value = direct.upper() if direct is not None else ("NTSC" if ed.song.clock=="PAL" else "PAL")
                if value not in ("PAL","NTSC"):raise ValueError("Choose PAL or NTSC")
                self.release_audition()
                ed.edit("Set C64 timing",[(("clock",),value)])
                self.audio.configure(ed.song)
                ed.status = f"{value} timing; playback stopped. F5 restarts with the new clock."
                return
            if field == "audio_buffer":
                if direct is not None:
                    self.apply_audio_buffer(int(direct))
                else:
                    from sidpulse.ui.audio_buffer import open_dialog
                    open_dialog(self, 1 if delta > 0 else -1)
                return
            if field in ("speed", "tempo"):
                value = getattr(ed.song, field)
                lo, hi = (1, 255) if field == "speed" else (32, 255)
                value = int(direct) if direct is not None else max(lo, min(hi, value + delta))
                if not lo <= value <= hi:
                    raise ValueError(f"Use {lo}..{hi} in decimal")
                ed.edit(f"Set {field}", [((field,), value)])
                return
            if field == "helper_strip":
                self.helper_strip = str(direct).lower() in ("on", "1", "true", "yes") if direct is not None else not self.helper_strip
                return
            if field == "zoom":
                self.zoom = max(.5, min(3., float(direct) / 100 if direct is not None else self.zoom + delta * .25))
                return
            path = (field,) if index < 3 or field == "comments" else ("filter", field)
            value = getattr(ed.song, field) if len(path) == 1 else getattr(ed.song.filter, field)
            choices = ["6581", "8580"] if field == "sid_model" else ([0, 16, 32, 48, 64, 80, 96, 112] if field == "mode" else None)
            maxval = {"cutoff": 2047, "routing": 7}.get(field, 15)
        if direct is not None:
            if type(value) is bool:
                new = str(direct).lower() in ("1", "on", "true", "yes")
            elif isinstance(value, str):
                new = direct
            else:
                new = int(direct.lstrip("$"), 16)
        elif choices:
            new = choices[(choices.index(value) + (1 if delta > 0 else -1)) % len(choices)]
        elif type(value) is bool:
            new = not value
        elif isinstance(value, str):
            self.text_dialog(f"Edit {field}", value, lambda text: self.change_property(direct=text))
            return
        else:
            new = max(0, min(maxval, value + delta))
        if choices and new not in choices:
            raise ValueError(f"Choose one of: {choices}")
        if type(new) is int and not choices and not 0 <= new <= maxval:
            raise ValueError(f"Value must be 0..{maxval:X} hexadecimal")
        ed.edit(f"Set {field}", [(path, new)])
        self.audio.configure(ed.song)

    def page_key(self, event):
        ed=self.editor
        key, mod = event.key, event.mod
        shift = bool(mod & pg.KMOD_SHIFT)
        if self.page == "help":
            if pg.K_1 <= key <= pg.K_9:
                self.help_topic = key - pg.K_1
                self.help_scroll = 0
            elif key in (pg.K_LEFT, pg.K_RIGHT, pg.K_TAB):
                delta = -1 if key == pg.K_LEFT or (key == pg.K_TAB and shift) else 1
                self.help_topic = (self.help_topic + delta) % len(HELP_TOPIC_NAMES)
                self.help_scroll = 0
            else:
                self.help_scroll += {pg.K_UP: -1, pg.K_DOWN: 1, pg.K_PAGEUP: -10, pg.K_PAGEDOWN: 10}.get(key, 0)
        elif self.page == "files":
            from sidpulse.ui.file_browser_input import handle_event
            handle_event(self, event)
        elif self.page == "orders":
            from sidpulse.ui.orders import handle_key
            handle_key(self,event)
        elif self.page == "samples":
            if key == pg.K_RETURN:self.import_sample_browser();return
            if key == pg.K_SPACE:self.preview_sample();return
            if key == pg.K_DELETE:self.delete_sample();return
            if key in (pg.K_UP, pg.K_DOWN):
                self.sample_index = max(1, min(99, self.sample_index + (-1 if key == pg.K_UP else 1)))
        elif self.page in ("instrument", "settings"):
            if self.page=='instrument':self.normalize_instrument_tab()
            if self.page == 'settings' and self.property_index == 29 and key in (pg.K_RETURN,pg.K_LEFT,pg.K_RIGHT):
                self.open_keyboard_mapping()
                return
            if self.page == 'settings' and self.property_index in (24, 25) and key == pg.K_RETURN:
                field = 'rows_per_beat' if self.property_index == 24 else 'beats_per_bar'
                self.text_dialog('Pattern grid: ' + field.replace('_', ' '),
                                 getattr(ed.pattern_grid, field),
                                 lambda value: self.change_property(direct=value),
                                 'Decimal. Display only: no tempo, note or shuffle timing changes. Ctrl+S saves the grid.')
                return
            if self.page == 'settings' and self.property_index in (15, 23) and key == pg.K_RETURN:
                self.change_property()
                return
            if self.page == 'settings' and self.property_index == 22 and key in (pg.K_RETURN,pg.K_LEFT,pg.K_RIGHT):
                from sidpulse.ui.autosave_settings import open_dialog
                open_dialog(self)
                return
            if self.page == "instrument" and key == pg.K_TAB:
                choices=("list","buttons","automation" if self.inline_recording_visible else "properties")
                self.instrument_focus=choices[(choices.index(self.instrument_focus)+(-1 if shift else 1))%3]
                return
            if self.page=="instrument" and self.instrument_focus=="buttons":
                targets=self.instrument_buttons()
                self.instrument_button %= len(targets)
                if key in (pg.K_LEFT,pg.K_RIGHT,pg.K_UP,pg.K_DOWN):
                    self.instrument_button=(self.instrument_button+(-1 if key in (pg.K_LEFT,pg.K_UP) else 1))%len(targets)
                    action,value=targets[self.instrument_button]
                    if action=='toggle_program' and self.instrument_tab=='motion':
                        from sidpulse.ui.instruments import PROGRAM_ROWS
                        self.property_index=next(i for i,p in PROGRAM_ROWS.items() if p==value)
                elif key in (pg.K_RETURN,pg.K_SPACE):
                    action,value=targets[self.instrument_button]
                    self.instrument_action(action,value,None)
                elif key==pg.K_INSERT:self.add_instrument()
                elif key==pg.K_DELETE:self.confirm_delete_instrument()
                return
            if self.page == "instrument" and self.instrument_focus == "list":
                if key in (pg.K_UP, pg.K_DOWN):
                    self.select_instrument_slot(-1 if key == pg.K_UP else 1)
                elif key==pg.K_RETURN:
                    self.open_new_instrument() if self.instrument_slot not in ed.song.instruments else self.open_presets()
                elif key==pg.K_RIGHT:
                    if self.inline_recording_visible:self.instrument_focus = 'automation'
                    elif self.instrument_slot in ed.song.instruments:self.instrument_focus = "properties"
                    else:self.open_new_instrument()
                elif key == pg.K_INSERT:self.add_instrument()
                elif key == pg.K_DELETE:self.confirm_delete_instrument()
                return
            if self.page=="instrument" and self.instrument_slot not in ed.song.instruments:
                self.instrument_focus="list"
                if key==pg.K_RETURN:self.open_new_instrument()
                return
            if self.page=="instrument" and key in (pg.K_PAGEUP,pg.K_PAGEDOWN):
                self.choose_instrument_tab("general" if key==pg.K_PAGEUP else "motion")
                return
            if self.page=="instrument":
                if self.instrument_tab=="roll" and self.roll_key(event):return
                if key==pg.K_INSERT:self.add_instrument();return
                if key==pg.K_DELETE:self.confirm_delete_instrument();return
            if self.page=="instrument" and self.instrument_tab=="adsr" and key in (pg.K_UP,pg.K_DOWN):
                self.property_index=max(2,min(5,self.property_index+(-1 if key==pg.K_UP else 1)));return
            maximum = len(INSTRUMENT_FIELDS)-1 if self.page == "instrument" else 29
            if key in (pg.K_UP, pg.K_DOWN):
                if self.page=='instrument':self.move_instrument_field(-1 if key==pg.K_UP else 1);return
                lo,hi=(9,19) if self.page=="instrument" and self.instrument_tab=="motion" else (0,8) if self.page=="instrument" else (0,maximum)
                self.property_index = max(lo, min(hi, self.property_index + (-1 if key == pg.K_UP else 1)))
            elif key in (pg.K_LEFT, pg.K_RIGHT):
                delta = -1 if key == pg.K_LEFT else 1
                if shift:
                    delta *= 16
                if self.page == 'instrument' and isinstance(getattr(ed.song.instruments[ed.instrument], INSTRUMENT_FIELDS[self.property_index]), (str, list)):
                    return
                self.change_property(delta)
            elif key == pg.K_RETURN:
                if self.page == 'instrument' and not getattr(event, 'value_click', False):
                    return
                if self.page == 'settings' and self.property_index == 28:
                    self.toggle_channel_visualizers()
                    return
                if self.page == 'settings' and self.property_index == 27:
                    self.toggle_control_panel()
                    return
                if self.page == 'settings' and self.property_index == 26:
                    self.toggle_pattern_clipboard_buttons()
                    return
                if self.page == 'settings' and self.property_index == 13:
                    from sidpulse.ui.audio_buffer import open_dialog
                    open_dialog(self)
                    return
                if self.page == "instrument":
                    fields = INSTRUMENT_FIELDS
                    field=fields[self.property_index]
                    if field in SEQUENCES:
                        self.change_property()
                        return
                    value = getattr(self.editor.song.instruments[self.editor.instrument], field)
                else:
                    fields = ("title", "author", "sid_model", "zoom", "cutoff", "resonance", "routing", "mode", "volume", "comments", "helper_strip", "speed", "tempo", "audio_buffer", "released", "export_loop", "clock", "theme", "font_size", "font_bold", "font_file", "file_browser_show_modified")
                    field = fields[self.property_index]
                    value = self.file_browser_show_modified if field == "file_browser_show_modified" else self.appearance[field] if field in self.appearance else self.editor.song.export_config.get("released","2026 SIDpulse") if field=="released" else self.editor.song.export_config.get("loop",True) if field=="export_loop" else self.audio_buffer if field == "audio_buffer" else self.helper_strip if field == "helper_strip" else (round(self.zoom * 100) if field == "zoom" else getattr(self.editor.song if self.property_index < 3 or field in ("comments", "speed", "tempo", "clock") else self.editor.song.filter, field))
                initial = str(value) if type(value) is not int or (self.page=="instrument" and self.property_index>=9) or (self.page == "settings" and self.property_index in (3, 11, 12, 13, 18)) else f"{value:X}"
                self.text_dialog("Edit value", initial, lambda value: self.change_property(direct=value), "Motion parameters: decimal. SID registers: hex. Speed, tempo, buffer, zoom: decimal.")

    def execute(self, command, event=None):
        if command is None:
            return
        ed = self.editor
        name, value = command.name, command.value
        if self.media_action(name, value):return
        if name == "release":
            self.held.discard(value)
            self.audio.send("off", value)
            for token in self.audition_tokens.pop(value, []):
                self.audio.send("off", token)
        elif name == "piano":
            if self.page=="instrument" and self.instrument_slot not in ed.song.instruments:
                ed.status="Empty instrument slot. Enter: Choose preset / No preset / Manual.";return
            scan, offset, preview_only = value
            note = min(95, ed.octave * 12 + offset)
            if self.page == "samples":
                if scan not in self.held:
                    self.preview_sample(scan, note)
                    self.held.add(scan)
                return
            if self.audio.playback.status != "stopped":
                if not preview_only:ed.enter_note(note)
                ed.status="F8 stops playback so the three SID voices are available for keyboard audition."
                return
            if scan not in self.held:
                instrument = ed.song.instruments.get(ed.instrument)
                if instrument is not None:
                    if instrument.sample_override and ed.history.revision != self.last_audio_revision:
                        self.sync_audio()  # publish a newly assigned bank before its first note
                    self.audio.send("on", scan, note, instrument, ed.voice if self.page == "pattern" else None, ed.instrument)
                    self.held.add(scan)
                else:
                    ed.status = "Empty instrument slot. F4: add an instrument or choose a preset."
            if not preview_only:
                ed.enter_note(note)
        elif name == "note":
            ed.enter_note(value)
        elif name in ("audition_cell", "audition_row"):
            if ed.history.revision != self.last_audio_revision:
                self.sync_audio()
            scan = event.scancode
            if scan in self.held:
                return
            self.held.add(scan)
            cells = list(enumerate(ed.pattern.rows[ed.row])) if name == "audition_row" else [(ed.voice, ed.cell)]
            tokens = []
            for voice, cell in cells:
                if cell.note is not None and cell.note >= 0 and (cell.instrument or ed.instrument) in ed.song.instruments:
                    token = f"row-{scan}-{voice}"
                    self.audio.send("on", token, cell.note, ed.song.instruments[cell.instrument or ed.instrument], voice, cell.instrument or ed.instrument)
                    tokens.append(token)
            self.audition_tokens[scan] = tokens
        elif name == "page":
            self.change_page(value)
        elif name in ("move", "step_move"):
            dr, dc, select = value
            if select: self.follow_playback = False
            ed.move(dr * (max(1, ed.skip) if name == "step_move" else 1), dc, select)
        elif name == "channel":
            if event and event.key == pg.K_TAB and value < 0 and ed.column != 0:
                ed.column = 0
            else:
                ed.voice = max(0, min(2, ed.voice + value))
                ed.column = 0 if event and event.key == pg.K_TAB else ed.column
        elif name == "home_end":
            col, voice, row = (len(FIELDS)-1, 2, len(ed.pattern.rows) - 1) if value else (0, 0, 0)
            if ed.column != col:
                ed.column = col
            elif ed.voice != voice:
                ed.voice = voice
            else:
                ed.row = row
        elif name == "edge":
            ed.row = len(ed.pattern.rows) - 1 if value == -1 else 0
        elif name == "digit":
            ed.enter_digit(value)
        elif name in ("clear", "repeat"):
            ed.clear_field() if name == "clear" else ed.repeat_field()
        elif name == "pick":
            ed.last_cell = deepcopy(ed.cell)
            if ed.cell.instrument:
                ed.instrument = ed.cell.instrument
            ed.status = "Picked field defaults from cursor"
        elif name == "mask":
            field = FIELDS[ed.column]
            if field != "expression":
                ed.edit_mask.symmetric_difference_update({field})
                ed.status = f"Edit mask {field}: {'ON' if field in ed.edit_mask else 'OFF'}"
        elif name in ("insert_row", "delete_row"):
            ed.insert_delete(name == "delete_row", value)
        elif name == "mark":
            ed.mark(value)
        elif name == "copy":
            self.copy_fields(bool(value))
        elif name == "paste":
            self.paste_fields(value or 'overwrite')
        elif name == 'keyboard_mapping':
            self.open_keyboard_mapping()
        elif name == "paste_special":
            self.open_paste_special()
        elif name == 'reset_automation':
            from sidpulse.ui.edit_confirmation import open_dialog
            open_dialog(self, 'reset')
        elif name == 'pattern_arpeggio':
            from sidpulse.ui.pattern_arpeggio import open_dialog
            open_dialog(self,value)
        elif name == 'confirm_cut_toggle':
            self.toggle_confirm_cut()
        elif name == 'instrument_monitor_buttons':
            self.toggle_instrument_monitor_buttons()
        elif name == "channel_visualizers_toggle":
            self.toggle_channel_visualizers()
        elif name == "pattern_fit_three_toggle":
            self.toggle_pattern_fit_three()
        elif name == "control_panel_toggle":
            self.toggle_control_panel()
        elif name == "pattern_clipboard_buttons":
            self.toggle_pattern_clipboard_buttons()
        elif name in ('copy_instrument','paste_instrument'):
            getattr(self,name)()
        elif name == 'pattern_select_all':
            self.follow_playback=False
            self.control_focus=False
            ed.anchor=(0,0)
            ed.selection_end=(len(ed.pattern.rows)-1,2)
            ed.status='Selected '+ed.selection_description()
        elif name == "transpose":
            ed.transpose(value)
        elif name == "roll":
            ed.roll(value)
        elif name == "block_instrument":
            ed.set_block_instrument()
        elif name in ("undo", "redo"):
            ed.status = getattr(ed.history, name)(ed.song)
            ed.repair_cursor()
            self.instrument_slot=ed.instrument
            self.audio.configure(ed.song)
        elif name == "store_pattern":
            ed.stored_pattern = deepcopy(ed.pattern)
            ed.status = "Pattern snapshot stored; Alt+Backspace restores it"
        elif name == "restore_pattern":
            if ed.stored_pattern:
                ed.edit("Restore pattern snapshot", [(("patterns", ed.pattern_id), ed.stored_pattern)])
        elif name == "pattern":
            ed.select_pattern(ed.pattern_id + value)
        elif name == "order_pattern":
            ed.order = max(0, min(len(ed.song.orders) - 1, ed.order + value))
            ed.select_pattern(ed.song.orders[ed.order])
        elif name == "instrument":
            ed.select_instrument(value)
            self.instrument_slot=ed.instrument
        elif name == "octave":
            ed.octave = max(0, min(7, ed.octave + value))
            ed.status = f'Audition / note-entry octave: {ed.octave}'
        elif name == 'octave_reset':
            ed.octave = ed.DEFAULT_OCTAVE
            ed.status = f'Octave reset to {ed.octave}'
        elif name == "skip":
            ed.skip = value
        elif name == "center":
            value = not ed.centered
            save_preferences({'center_selection': value})
            ed.centered = value
            ed.status = 'Center pattern row: ' + ('ON' if value else 'OFF')
        elif name == "highlight":
            ed.highlight = not ed.highlight
        elif name == "pattern_length":
            from sidpulse.ui.pattern_length import open_dialog
            open_dialog(self)
        elif name == "zoom":
            self.zoom = 1.0 if value == 0 else max(.5, min(3., round(self.zoom + value * .25, 2)))
        elif name == "fullscreen":
            self.release_audition()
            if not self.fullscreen:
                self.window_size = self.screen.get_size()
                self.screen = pg.display.set_mode((0, 0), pg.FULLSCREEN)
            else:
                self.screen = pg.display.set_mode(self.window_size, pg.RESIZABLE)
            self.fullscreen = not self.fullscreen
        elif name == "panic":
            self.panic()
        elif name in ("mute", "solo"):
            self.toggle_monitor(name, value)
        elif name in ('instrument_mute', 'instrument_solo'):
            self.toggle_instrument_monitor(name, value)
        elif name == "play":
            self.start_playback(value)
        elif name == 'skip_order':
            state = self.audio.playback
            if state.status == 'playing' and state.mode == 'song':
                self.audio.send('skip_order', value)
                ed.status = ('Next' if value > 0 else 'Previous') + ' song order | F8 stop'
        elif name == "pause":
            self.audio.send("pause")
        elif name == "playback_mark":
            mark = (ed.pattern_id, ed.row)
            self.playback_mark = None if self.playback_mark == mark else mark
            ed.status = "Playback mark cleared" if self.playback_mark is None else f"F7 mark: pattern {mark[0]:02X}, row {mark[1]:03d}"
        elif name == "follow":
            self.follow_playback = not self.follow_playback
            ed.status = f"Playback tracing {'ON' if self.follow_playback else 'OFF'}"
        elif name == "appearance_settings":
            self.change_page("settings");self.property_index=value
        elif name == 'f5_restart_settings':
            self.change_page('settings');self.property_index=23
        elif name == "audio_settings":
            self.change_page("settings")
            self.property_index = 13
            from sidpulse.ui.audio_buffer import open_dialog
            open_dialog(self)
        elif name == "audio_reset_stats":
            self.audio.send("reset_stats")
            self.audio_warning = ''
            self.audio_warning_until = 0.0
            ed.status = "Audio counters reset"
        elif name == "about":
            self.dialog={"title":"About SIDpulse Tracker", "logo":True}
        elif name == "export":
            self.begin_export()
        elif name == "export_prg":
            self.begin_export('prg')
        elif name == "control_focus":
            self.change_page("pattern")
            self.control_focus = not self.control_focus
        elif name == "instrument_programs":
            self.change_page("instrument")
            self.property_index=9
            self.instrument_focus="properties"
        elif name == "pending":
            ed.status = str(value) if ":" in str(value) else f"{value}: not implemented yet"
        elif name == 'pulse_record_arm':
            self.open_automation_recording()
        elif name == 'pulse_record_disarm':
            self.disarm_pulse_recording()
        elif name == 'automation_display_toggle':
            self.automation_display = 1 if self.automation_display == 2 else 2
            save_preferences({'automation_display': self.automation_display})
        elif name == 'automation_control':
            from sidpulse.ui.automation_input import activate
            activate(self,*value)
        elif name == "helper_toggle":
            self.helper_strip = not self.helper_strip
        elif name == "comments":
            self.text_dialog("Song comments", ed.song.comments, lambda text: ed.edit("Set comments", [(("comments",), text)]), "Shift+Enter: new line. Enter: save notes. Unicode text is preserved in .sidpulse.")
            self.dialog["multiline"]=True
        elif name == 'autosave_settings':
            from sidpulse.ui.autosave_settings import open_dialog
            open_dialog(self)
        elif name == 'reset_settings':
            from sidpulse.ui.settings_reset import open_dialog
            open_dialog(self)
        elif name == "quit":
            self.confirm_quit()
        elif name == "open":
            self.confirm_discard(lambda: self.browse("open"))
        elif name == "quick_save":
            self.save_project()
        elif name in ("save", "save_as"):
            self.browse("save")
        elif name == "new":
            self.confirm_action("New project?", "All unsaved changes will be lost.", self.new_project)
        elif name in ("clear_patterns", "clear_instruments"):
            if name == "clear_patterns":
                message = "Clear notes, effects and filter rows in every pattern? Instruments, pattern lengths and the order list stay intact. This can be undone."
            else:
                message = "Delete all instruments? Patterns and their instrument numbers stay intact, but empty slots are silent. This can be undone."
            self.confirm_action("Clear all pattern data?" if name == "clear_patterns" else "Clear all instruments?",
                                message, lambda: self.clear_project_data(name))
        elif name == "escape":
            if self.page == "files":
                self.cancel_browser()
            elif self.page == "help":
                self.page = self.previous_page if self.previous_page != "help" else "pattern"
                if self.page != "files":
                    self.after_save = None
                self.sync_file_text_input()
            else:
                self.open_menu()
        elif name == "page_key":
            self.page_key(value)

    def dialog_event(self, event):
        from sidpulse.ui.dialogs import choices,focus
        dialog = self.dialog
        if dialog.get('kind') == 'sample_synthesis_batch':
            from sidpulse.ui.batch_synthesis import handle_event
            handle_event(self,event);return
        if dialog.get('kind') == 'sample_synthesis':
            from sidpulse.ui.sample_synthesis import handle_event
            handle_event(self,event);return
        if dialog.get('kind') == 'sample_volume':
            from sidpulse.ui.sample_volume import handle_event
            handle_event(self, event);return
        if dialog.get("kind") == "sample_squeeze":
            from sidpulse.ui.sample_view import squeeze_event
            squeeze_event(self,event);return
        if dialog.get("kind") == "media_job":
            from sidpulse.ui.media_actions import handle_job_event
            handle_job_event(self, event)
            return
        if dialog.get('kind') == 'automation_recording':
            from sidpulse.ui.automation_recording import handle_event
            handle_event(self, event)
            return
        if dialog.get('kind') == 'pattern_edit_confirm':
            from sidpulse.ui.edit_confirmation import handle_event
            handle_event(self, event)
            return
        if dialog.get('kind') == 'export_squeezer':
            from sidpulse.ui.export_squeezer import handle_event
            handle_event(self, event)
            return
        if dialog.get('kind') == 'pattern_length':
            from sidpulse.ui.pattern_length import handle_event
            handle_event(self,event)
            return
        if dialog.get('kind') == 'autosave_settings':
            from sidpulse.ui.autosave_settings import handle_event
            handle_event(self,event)
            return
        if dialog.get('kind') == 'welcome':
            from sidpulse.ui.welcome import handle_event
            handle_event(self, event)
            return
        if dialog.get('kind') == 'audio_buffer':
            from sidpulse.ui.audio_buffer import handle_event
            handle_event(self, event)
            return
        if not any(key in dialog for key in ('presets','confirm_instrument')):
            if event.type==pg.MOUSEBUTTONDOWN and event.button==1:
                for rect,action,value in reversed(self.renderer.hits):
                    if action=='dialog_button' and rect.collidepoint(event.pos):
                        self.dialog_event(pg.event.Event(pg.KEYDOWN,key=value,mod=0,dialog_button=True))
                        return
            if event.type==pg.KEYDOWN and not getattr(event,'dialog_button',False):
                if event.key in (pg.K_TAB,pg.K_LEFT,pg.K_RIGHT):
                    step=-1 if event.key==pg.K_LEFT or event.key==pg.K_TAB and event.mod&pg.KMOD_SHIFT else 1
                    dialog['button_focus']=(focus(dialog)+step)%len(choices(dialog));return
                if event.key==pg.K_RETURN and not event.mod&pg.KMOD_SHIFT:
                    key=choices(dialog)[focus(dialog)][1]
                    self.dialog_event(pg.event.Event(pg.KEYDOWN,key=key,mod=0,dialog_button=True));return
        if dialog.get('kind') == 'pcm_export_confirm' and event.type == pg.KEYDOWN and event.key == pg.K_s:
            from sidpulse.ui.batch_synthesis import begin
            begin(self,dialog['return_dialog']);return
        if dialog.get('kind') == 'reset_settings_pending':
            if event.type == pg.KEYDOWN and event.key == pg.K_ESCAPE:
                from sidpulse.ui.settings_reset import cancel
                cancel(self)
            return
        if dialog.get('kind') == 'keyboard_mapping':
            if event.type == pg.KEYDOWN:
                if event.key == pg.K_ESCAPE:
                    self.dialog = None
                elif event.key in (pg.K_m, pg.K_c):
                    try:
                        self.set_keyboard_mapping('modern' if event.key == pg.K_m else 'classic')
                    except OSError as exc:
                        dialog['error'] = str(exc)
            return
        if dialog.get('kind') == 'paste_special':
            if event.type == pg.KEYDOWN:
                if event.key == pg.K_ESCAPE:
                    self.dialog = None
                elif event.key in (pg.K_n, pg.K_a, pg.K_b):
                    self.paste_fields(scope={pg.K_n:'notes',pg.K_a:'automation',pg.K_b:'both'}[event.key])
                    self.dialog = None
            return
        if dialog.get('kind') == 'pattern_arpeggio':
            from sidpulse.ui.pattern_arpeggio import handle_event
            handle_event(self,event)
            return
        if dialog.get('kind') == 'notice':
            if event.type==pg.KEYDOWN and event.key in (pg.K_RETURN,pg.K_ESCAPE):
                self.dialog=dialog.get('return_dialog')
            return
        if 'recover' in dialog:
            if event.type==pg.KEYDOWN and event.key in (pg.K_y,pg.K_n,pg.K_ESCAPE):
                self.recover_autosave(event.key==pg.K_y)
            return
        if "presets" in dialog:
            self.preset_event(event);return
        if "confirm_instrument" in dialog:
            if event.type==pg.KEYDOWN:
                if event.key==pg.K_ESCAPE:self.dialog=None
                elif event.key in (pg.K_TAB,pg.K_LEFT,pg.K_RIGHT):dialog["confirm_selected"]=not dialog["confirm_selected"]
                elif event.key==pg.K_RETURN:
                    self.dialog=None
                    if dialog["confirm_selected"]:dialog["confirm_instrument"]()
            elif event.type==pg.MOUSEBUTTONDOWN and event.button==1:
                for rect,action,value in self.renderer.hits:
                    if action=="confirm_instrument" and rect.collidepoint(event.pos):
                        self.dialog=None
                        if value:dialog["confirm_instrument"]()
                        break
            return
        if event.type == pg.TEXTINPUT and "text" in dialog:
            if dialog.pop("ignore_initial_text",None)==event.text:return
            if dialog.pop("select_all", False):
                dialog["text"] = ""
            dialog["text"] += event.text.replace("\x00", "")
        elif event.type == pg.KEYDOWN:
            if event.key == pg.K_ESCAPE:
                self.dialog = dialog.get("return_dialog")
                pg.key.stop_text_input()
                if dialog.get("on_cancel"):
                    dialog["on_cancel"]()
                else:
                    self.after_save = None
                    if self.page == "files":
                        self.sync_file_text_input()
            elif "text" in dialog:
                if event.key == pg.K_BACKSPACE:
                    dialog["text"] = "" if dialog.pop("select_all", False) else dialog["text"][:-1]
                elif event.mod & pg.KMOD_CTRL and event.key == pg.K_a:
                    dialog["select_all"] = True
                elif event.key == pg.K_RETURN and event.mod & pg.KMOD_SHIFT and dialog.get("multiline"):
                    dialog["select_all"]=False
                    dialog["text"]+="\n"
                elif event.key == pg.K_RETURN:
                    self.dialog = dialog.get("return_dialog")
                    pg.key.stop_text_input()
                    try:
                        dialog["callback"](dialog["text"])
                    except (ValueError, OSError) as exc:
                        self.dialog = dialog
                        dialog["error"] = str(exc)
                        pg.key.start_text_input()
            elif "export" in dialog:
                if event.key==pg.K_s:
                    self.dialog=None
                    self.after_save=dialog["export"]
                    self.save_project()
                elif event.key==pg.K_e:
                    self.dialog=None
                    dialog["export"]()
            elif "discard" in dialog:
                if event.key == pg.K_d:
                    self.dialog = None
                    dialog["discard"]()
                elif event.key == pg.K_s:
                    self.dialog = None
                    self.after_save = dialog["discard"]
                    self.save_project()
            elif "yes" in dialog and event.key == pg.K_y:
                self.dialog = None
                dialog["yes"]()
            elif dialog.get("menu"):
                if event.key == pg.K_q:
                    self.dialog = None
                    self.confirm_quit()
                elif event.key in (pg.K_l, pg.K_s, pg.K_n):
                    self.dialog = None
                    self.execute(Command({pg.K_l: "open", pg.K_s: "save", pg.K_n: "new"}[event.key]))
                else:
                    command = dispatch(event, self.page, self.editor.column, self.keyboard_mapping)
                    if command and command.name == "page":
                        self.dialog = None
                        self.execute(command, event)
            elif event.key == pg.K_RETURN:
                self.dialog = None

    def file_event(self, event):
        from sidpulse.ui.file_browser_input import handle_event
        return handle_event(self, event)

    def handle(self, event):
        if event.type == pg.KEYUP and event.key == pg.K_l:
            self.song_loop_key_held = False
        if self.diagnostics: self.diagnostics.event(self,event)
        if event.type in (pg.KEYDOWN, pg.KEYUP):
            LOG.debug("type=%s key=%s scan=%s mods=%s page=%s", event.type, event.key, getattr(event,'scancode',0), event.mod, self.page)
        try:
            self.sync_pulse_recording()
            if self.renderer.scrollbars.handle(self, event):
                return
            from sidpulse.ui.pressable import handle_event as handle_button_event
            if handle_button_event(self, event):
                return
            if self.pattern_drag:
                if event.type == pg.MOUSEMOTION:
                    if getattr(event, 'buttons', (True,))[0]:
                        self.update_pattern_selection(event.pos)
                    else:
                        self.finish_pattern_selection()
                    return
                if event.type == pg.MOUSEBUTTONUP and event.button == 1:
                    self.update_pattern_selection(event.pos)
                    self.finish_pattern_selection()
                    return
                if event.type in (pg.KEYDOWN, pg.QUIT, pg.WINDOWFOCUSLOST, pg.VIDEORESIZE, pg.MOUSEBUTTONDOWN):
                    self.finish_pattern_selection()
            if self.pulse_take and self.pulse_take['pending']:
                if event.type != pg.MOUSEMOTION:
                    self.pulse_deferred_events.append(event)
                return
            from sidpulse.ui.pattern_automation import handle_event as handle_automation_entry
            if handle_automation_entry(self, event):
                return
            if self.sample_drag and self.sample_drag_event(event):
                return
            if event.type==pg.MOUSEMOTION and self.instrument_drag:
                self.update_instrument_drag(event.pos);return
            if event.type==pg.MOUSEBUTTONUP and event.button==1 and self.instrument_drag:
                if not self.instrument_drag.get('keyboard'):
                    self.update_instrument_drag(event.pos);self.finish_instrument_drag();return
            if event.type in (pg.KEYDOWN,pg.QUIT,pg.WINDOWFOCUSLOST,pg.VIDEORESIZE):
                repeating_slider_key = (event.type == pg.KEYDOWN and event.key in (pg.K_LEFT,pg.K_RIGHT)
                                        and self.instrument_drag and self.instrument_drag.get('keyboard'))
                if not repeating_slider_key:
                    self.finish_instrument_drag(cancel=event.type==pg.KEYDOWN and event.key==pg.K_ESCAPE)
                if self.pulse_take and self.pulse_take['pending']:
                    if not (event.type == pg.KEYDOWN and event.key == pg.K_ESCAPE):
                        self.pulse_deferred_events.append(event)
                    return
            if event.type == pg.QUIT:
                self.confirm_quit()
            elif event.type == pg.WINDOWFOCUSLOST:
                self.song_loop_key_held = False
                self.automation_state.pop('slider_keys',None)
                self.automation_state.pop('keyboard_touch',None)
                self.release_audition()
                if self.dialog and self.dialog.get('kind') in ('audio_buffer','pattern_length','sample_volume','sample_synthesis'):
                    self.dialog['drag_rect'] = None
            elif event.type == pg.VIDEORESIZE and not self.fullscreen:
                self.screen = pg.display.set_mode((max(480, event.w), max(360, event.h)), pg.RESIZABLE)
                if self.dialog and self.dialog.get('kind') in ('audio_buffer','pattern_length','sample_volume','sample_synthesis'):
                    self.dialog['drag_rect'] = None
            elif self.dialog:
                self.dialog_event(event)
            elif self.menu_path:
                self.menu_event(event)
            elif self.inline_recording_visible and self.automation_event(event):
                pass
            elif self.page == "files" and self.file_event(event):
                pass
            elif event.type==pg.KEYDOWN and self.page=="pattern" and self.control_focus and not event.mod & (pg.KMOD_ALT|pg.KMOD_CTRL):
                if event.key in (pg.K_UP,pg.K_DOWN,pg.K_PAGEUP,pg.K_PAGEDOWN):
                    self.editor.move(rows={pg.K_UP:-1,pg.K_DOWN:1,pg.K_PAGEUP:-16,pg.K_PAGEDOWN:16}[event.key])
                elif event.key==pg.K_RETURN:self.edit_control()
                elif event.key==pg.K_DELETE:
                    values=deepcopy(self.editor.pattern.controls);values.pop(self.editor.row,None)
                    self.editor.edit("Clear filter row",[(("patterns",self.editor.pattern_id,"controls"),values)])
                elif event.key==pg.K_TAB:self.control_focus=False
                elif event.key>=pg.K_F1 or event.key==pg.K_ESCAPE:
                    self.execute(dispatch(event,self.page,self.editor.column,self.keyboard_mapping),event)
            elif event.type in (pg.KEYDOWN, pg.KEYUP):
                if self.page == 'orders' and event.type == pg.KEYDOWN:
                    from sidpulse.ui.orders import entry_key
                    if entry_key(self,event): return
                self.execute(dispatch(event, self.page, self.editor.column, self.keyboard_mapping), event)
            elif event.type == pg.DROPFILE:
                self.confirm_discard(lambda: self.open_project(event.file))
            elif event.type == pg.MOUSEWHEEL:
                if pg.key.get_mods() & pg.KMOD_CTRL:
                    self.execute(Command("zoom", 1 if event.y > 0 else -1))
                elif self.page == "pattern":
                    self.editor.move(rows=-event.y * 3)
                elif self.page == "orders":
                    from sidpulse.ui.orders import move
                    move(self,-event.y*3)
                elif self.page == "help":
                    self.help_scroll -= event.y * 3
                elif self.page == "samples":
                    self.sample_index = max(1, min(99, self.sample_index - event.y))
                elif self.page == "instrument":
                    x=pg.mouse.get_pos()[0]/max(1,self.renderer.cw)
                    if x<32:
                        self.select_instrument_slot(-event.y);self.instrument_focus="list"
                    elif self.instrument_tab in ('general','motion','adsr'):
                        self.move_instrument_field(-event.y);self.instrument_focus='properties'
                elif self.page == 'settings':self.property_index=max(0,min(29,self.property_index-event.y))
            elif event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
                for rect, action, value in reversed(self.renderer.hits):
                    if not rect.collidepoint(event.pos):
                        continue
                    if action == 'activity_indicator':
                        continue  # hover feedback must not steal the row's click
                    if action == "sample_marker":
                        self.begin_sample_drag(value,event.pos);break
                    if self.media_action(action,value):
                        break
                    if self.instrument_action(action,value,event.pos):
                        pass
                    elif action == 'song_title_settings':
                        self.change_page('settings')
                        if self.page == 'settings':
                            self.renderer.scrollbars.states.get('settings',{}).pop('token',None)
                    elif action == 'header_instrument':
                        self.change_page('instrument')
                        if self.page == 'instrument':
                            self.select_instrument_slot(number=value)
                            self.renderer.scrollbars.states.get('instruments',{}).pop('token',None)
                    elif action in ('copy_instrument','paste_instrument'):
                        from sidpulse.ui.pressable import begin
                        begin(self, rect, Command(action), event.pos)
                    elif action == "page":
                        self.change_page(value)
                    elif action in ("mute", "solo"):
                        self.toggle_monitor(action, value)
                    elif action == "control":
                        self.control_focus=True
                        self.editor.row=value
                        self.edit_control()
                    elif action == "control_focus":
                        self.control_focus=not self.control_focus
                    elif action == "control_panel_toggle":
                        self.toggle_control_panel()
                    elif action == "cell":
                        self.begin_pattern_selection(value, event.pos, bool(pg.key.get_mods() & pg.KMOD_SHIFT))
                    elif action == "pattern_grid":
                        self.begin_pattern_selection(self.pattern_position(event.pos), event.pos, bool(pg.key.get_mods() & pg.KMOD_SHIFT))
                    elif action == "select_field":
                        self.control_focus = False
                        self.follow_playback = False
                        self.editor.select_field(*value)
                    elif action in ('pattern_cut', 'pattern_copy'):
                        from sidpulse.ui.pressable import begin
                        begin(self, rect, Command('copy', action == 'pattern_cut'), event.pos)
                    elif action == "pattern_paste":
                        from sidpulse.ui.pressable import begin
                        begin(self, rect, Command('paste', 'overwrite'), event.pos)
                    elif action == "paste_special":
                        from sidpulse.ui.pressable import begin
                        begin(self, rect, Command('paste_special'), event.pos)
                    elif action in ('octave','octave_reset','instrument_mute','instrument_solo','reset_automation','pulse_record_arm','pulse_record_disarm','pattern_arpeggio','pattern_select_all','skip_order'):
                        from sidpulse.ui.pressable import begin
                        begin(self, rect, Command(action, value), event.pos)
                    elif action == 'bank_monitor_disabled':
                        self.editor.status = ('Use the assigned instrument M/S controls to monitor this sample.'
                                              if value[0] == 'sample' else 'Empty instrument slot: nothing to mute or solo.')
                    elif action == 'choose_sample':
                        self.sample_index = value
                    elif action == "choose_instrument":
                        self.select_instrument_slot(number=value)
                        self.instrument_focus="list"
                    elif action == "setting_edit":
                        self.property_index=value
                        if value in (2,10,15,16,17,19,21,23,26,27,28,29):self.change_property(1)
                        else:self.page_key(pg.event.Event(pg.KEYDOWN,key=pg.K_RETURN,mod=0))
                    elif action == "property":
                        self.property_index = value
                        self.instrument_focus = "properties"
                    elif action == "waveform":
                        if not self.allow_instrument_edit():break
                        self.editor.edit("Set oscillator waveform", [(("instruments", self.editor.instrument, "waveform"), value)])
                        self.property_index = 1
                        self.instrument_focus = "properties"
                    elif action == 'song_loop':
                        from sidpulse.ui.orders import toggle_loop
                        toggle_loop(self)
                    elif action in ('order_focus','bank_pattern','bank_open','order','order_value'):
                        from sidpulse.ui.orders import commit_entry, begin_entry, open_pattern
                        if not commit_entry(self): break
                        if action == 'order_value': begin_entry(self,value)
                        elif action == 'order_focus': self.order_focus = value
                        elif action == 'bank_open': open_pattern(self)
                        elif action == 'bank_pattern':
                            self.order_focus = 'bank'
                            self.bank_pattern = value
                            if getattr(event,'clicks',1)>=2: open_pattern(self)
                        else:
                            self.order_focus = 'orders'
                            self.order_entry_index = value
                            self.editor.order = value
                            self.editor.select_pattern(self.editor.song.orders[value])
                    elif action == "file":
                        if self.file_index == value:
                            self.select_file()
                        else:
                            self.file_index = value
                    elif action == "filename":
                        self.prompt_filename()
                    elif action == "help_topic":
                        self.help_topic = value
                        self.help_scroll = 0
                    break
        except (ValueError, OSError) as exc:
            self.editor.status = str(exc)

    def run(self, frames=None, screenshot=None):
        self.start_services()
        clock = pg.time.Clock()
        count = 0
        last_draw = 0
        while self.running and (frames is None or count < frames):
            if self.diagnostics: self.diagnostics.heartbeat(self)
            events = pg.event.get()
            for event in events:
                self.handle(event)
            self.sync_audio()
            self.update_pattern_selection(scroll=True)
            # Snapshot only when due; file serialization/fsync run off the UI thread.
            self.autosave.tick(self.editor, self.metadata, self.path)
            if self.autosave.warning and self.dialog is None:self.show_autosave_warning()
            now = pg.time.get_ticks()
            # Poll input/services at full rate; redraw a settled, unchanged
            # window only five times a second (caret/status refresh). Events
            # and active work retain immediate 60 Hz drawing.
            dynamic = (not self.audio.idle or self.audio.test_active or
                       self.media_jobs or self.export_jobs or self.button_press or
                       self.pattern_drag or self.instrument_drag or self.sample_drag or
                       (self.button_flash and time.monotonic() < self.button_flash[2]))
            if events or dynamic or not count or now - last_draw >= 200:
                self.renderer.render(self)
                pg.display.flip()
                last_draw = now
            self.poll_export_analysis()
            if self.media_jobs:self.poll_media_jobs()
            if self.audio.error:
                self.editor.status = self.audio.error
            count += 1
            clock.tick(60)
        if screenshot:
            pg.image.save(self.screen, str(screenshot))
