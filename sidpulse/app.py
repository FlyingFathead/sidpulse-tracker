"""Native pygame shell. All song mutations go through reversible editor commands."""
from copy import deepcopy
import logging
from pathlib import Path
import pygame as pg

from sidpulse.audio.engine import AudioEngine
from sidpulse import __version__
from sidpulse.preferences import BUFFERS, THEMES, load_preferences, save_buffer, load_appearance, save_preferences, config_path, load_file_browser_dates, load_restart_on_f5
from sidpulse.commands.editor import Editor, FIELDS
from sidpulse.project.format import load, save
from sidpulse.song.model import Cell, ControlCell, Instrument, Song
from sidpulse.ui.keyboard import Command, dispatch
from sidpulse.ui.renderer import Renderer, HELP_TOPIC_NAMES
from sidpulse.ui.menus import menu_items
from sidpulse.ui.instruments import FIELDS as INSTRUMENT_FIELDS, SEQUENCES, LIMITS, display
from sidpulse.export.psid import compile_song, save_export

LOG = logging.getLogger("sidpulse.keys")


from sidpulse.ui.instrument_actions import InstrumentActions


class App(InstrumentActions):
    def __init__(self, song=None, path=None, audio=True, size=(1280, 900), zoom=1.0, audio_buffer=None):
        pg.display.init()
        pg.font.init()
        self.screen = pg.display.set_mode(size, pg.RESIZABLE)
        pg.display.set_caption(f"SIDpulse Tracker {__version__}")
        pg.key.set_repeat(350, 55)
        self.editor = Editor(song)
        self.audio_buffer = load_preferences() if audio_buffer is None else audio_buffer
        self.audio = AudioEngine(self.editor.song, audio, self.audio_buffer)
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
        self.instrument_slot = self.editor.instrument
        self.instrument_tab = "general"
        self.instrument_button = 3
        self.instrument_drag = None
        self.graph_field = "arpeggio"
        self.graph_step = self.graph_page = 0
        self.graph_low = -12
        self.control_focus = False
        self.sample_index = 1
        self.help_scroll = 0
        self.help_topic = 0
        self.helper_strip = True
        self.muted = [False, False, False]
        self.solo_voice = None
        self.zoom = max(.5, min(3.0, zoom))
        self.path = Path(path).expanduser() if path else None
        self.running = True
        self.fullscreen = False
        self.window_size = size
        self.dialog = None
        self.intro_pending = False
        self.scopes_visible = False
        self.held = set()
        self.audition_tokens = {}
        self.editor_metadata = {}
        self.file_mode = "open"
        self.file_dir = self.path.parent if self.path else Path.cwd()
        self.file_entries = []
        self.file_modified = {}
        self.file_browser_show_modified = load_file_browser_dates()
        self.restart_on_f5 = load_restart_on_f5()
        self.file_index = 0
        self.file_name = self.path.name if self.path else "untitled.sidpulse"
        self.after_save = None
        self.menu_path = []
        self.menu_indices = []
        from sidpulse.recovery import Autosave
        self.autosave = Autosave()
        self.diagnostics = None
        self.runtime_started = False
        self.runtime_clean = True
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
                self.file_name = self.path.name if self.path else 'recovered.sidpulse'
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
            self.change_page('info')
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
        if mode in ("song", "restart"):
            self.change_page("info")

    def sync_audio(self):
        scopes_visible = self.page == 'info'
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

    def toggle_monitor(self, action, voice=None):
        voice = self.editor.voice if voice is None else voice
        if action == "mute":
            self.muted[voice] = not self.muted[voice]
        else:
            self.solo_voice = None if self.solo_voice == voice else voice
        self.audio.send("monitor", self.monitor_mask())
        self.editor.status = "Monitor only | Alt+F1/F2/F3 mute voices | Alt+F9 mute current | Alt+F10 solo current"

    def close(self):
        self.audio.close()
        pg.quit()
        self.autosave.close(clean=self.runtime_clean)

    def restore_metadata(self, data):
        self.editor_metadata = deepcopy(data)
        ed = self.editor
        for key, lo, hi in (("row", 0, 255), ("voice", 0, 2), ("column", 0, 8), ("octave", 0, 7), ("skip", 0, 9)):
            value = data.get(key)
            if type(value) is int and lo <= value <= hi:
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
        self.instrument_slot=ed.instrument

    def metadata(self):
        result = deepcopy(self.editor_metadata)
        for key in ("row", "voice", "column", "octave", "skip", "pattern_id", "instrument", "order"):
            result[key] = getattr(self.editor, key)
        result["zoom"] = self.zoom
        result["helper_strip"] = self.helper_strip
        return result

    def text_dialog(self, title, initial, callback, message=""):
        self.release_audition()
        self.dialog = {"title": title, "text": str(initial), "callback": callback, "message": message, "select_all": True}
        pg.key.start_text_input()

    def apply_audio_buffer(self, value):
        save_buffer(value)
        if value != self.audio_buffer:
            self.audio_buffer = value
            self.audio.send('buffer', value)
        self.editor.status = f'Audio buffer default: {value} samples ({value / 48:.2f} ms per block).'

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
            self.editor.mark_saved()
            self.editor.status = f"Saved {self.path.name}"
            self.page = self.previous_page if self.previous_page != "files" else "pattern"
            if self.after_save:
                callback, self.after_save = self.after_save, None
                callback()
        except (OSError, ValueError) as exc:
            self.editor.status = f"Save failed: {exc}"
            raise

    def open_project(self, path):
        song, metadata = load(path)
        self.panic()
        self.editor = Editor(song)
        self.last_audio_revision = 0
        self.audio_configuration = (self.editor.song.sid_model,self.editor.song.clock)
        self.playback_mark = None
        self.restore_metadata(metadata)
        self.path = Path(path).expanduser()
        self.audio.configure(song)
        self.page = "pattern"
        self.editor.status = f"Loaded {self.path.name}"

    def new_project(self):
        self.panic()
        self.editor = Editor(Song())
        self.instrument_slot = self.editor.instrument
        self.instrument_focus = "list"
        self.last_audio_revision = 0
        self.audio_configuration = (self.editor.song.sid_model,self.editor.song.clock)
        self.playback_mark = None
        self.editor_metadata = {}
        self.path = None
        self.page = "pattern"
        self.audio.configure(self.editor.song)

    def browse(self, mode):
        self.release_audition()
        if self.page != "files":
            self.previous_page = self.page
        self.page = "files"
        self.file_mode = mode
        if mode == "save":
            self.file_name = self.path.name if self.path else "untitled.sidpulse"
        self.refresh_files()

    def refresh_files(self):
        try:
            entries = sorted(self.file_dir.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
            self.file_entries = [self.file_dir.parent] + [p for p in entries if not p.name.startswith(".") and (p.is_dir() or p.suffix.lower() == ".sidpulse")]
            from datetime import datetime
            self.file_modified = {}
            for path in self.file_entries[1:]:
                try:
                    self.file_modified[path] = datetime.fromtimestamp(path.stat().st_mtime).strftime('%Y-%m-%d %H:%M')
                except (OSError, ValueError, OverflowError):
                    self.file_modified[path] = 'Unavailable'
            self.file_index = 0
            self.editor.status = "Arrows: choose | Enter: open | Tab: filename | Backspace: parent"
        except OSError as exc:
            self.file_entries = []
            self.editor.status = str(exc)

    def select_file(self):
        if not self.file_entries:
            return
        path = self.file_entries[self.file_index]
        if path.is_dir():
            self.file_dir = path
            self.refresh_files()
        elif self.file_mode == "open":
            self.open_project(path)
        else:
            self.file_name = path.name
            self.prompt_filename()

    def prompt_filename(self):
        def accept(value):
            target = Path(value).expanduser()
            if not target.is_absolute():
                target = self.file_dir / target
            if self.file_mode == "open":
                self.open_project(target)
                return
            if not value.strip():
                raise ValueError("Enter a filename")
            target = target.with_suffix(".sidpulse")
            if target.exists() and (self.path is None or target.resolve() != self.path.resolve()):
                self.dialog = {"title": "Overwrite project?", "message": f"Replace {target.name}? The previous bytes will be kept as .bak.",
                               "hint": "Y: overwrite | Esc: cancel", "yes": lambda: self.save_project(target)}
            else:
                self.save_project(target)
        self.text_dialog("Save .sidpulse" if self.file_mode == "save" else "Open .sidpulse", self.file_name, accept,
                         "Relative to the displayed directory. You may enter an absolute path.")

    def change_page(self, page):
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
        self.page = page
        self.property_index = 0
        self.instrument_focus = "list"
        self.instrument_slot = self.editor.instrument
        self.instrument_tab = "general"
        self.instrument_button = 3
        self.instrument_drag = None
        self.graph_field = "arpeggio"
        self.graph_step = self.graph_page = 0
        self.graph_low = -12

    def open_menu(self, title="Main Menu"):
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
                command = dispatch(event, self.page, self.editor.column)
                if command and command.name in ("page", "open", "save", "save_as", "panic", "comments", "fullscreen", "pending", "play", "pause"):
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

    def begin_export(self, kind='sid'):
        from sidpulse.export.prg import compile_prg
        result=compile_prg(self.editor.song) if kind=='prg' else compile_song(self.editor.song)
        label='PRG' if kind=='prg' else 'PSID'
        self.release_audition()
        self.dialog={"title":f"Export {label} / keep your project", "message":
                     f"Ready: {len(result.data):,} bytes, {result.seconds:.2f} seconds. Save an editable .sidpulse with all instruments and song notes before exporting?",
                     "hint":"S: save project + export | E: export only | Esc: cancel",
                     "export":lambda:self.prompt_export(result,kind)}

    def prompt_export(self,result,kind='sid'):
        from sidpulse.export.prg import save_prg
        suffix='.prg' if kind=='prg' else '.sid'
        label='PRG' if kind=='prg' else 'PSID'
        default=self.path.with_suffix(suffix) if self.path else self.file_dir/('untitled'+suffix)
        def accept(text):
            if not text.strip():raise ValueError("Enter an export filename")
            target=Path(text).expanduser().with_suffix(suffix)
            if not target.is_absolute():target=self.file_dir/target
            def write():
                path=save_prg(target,result) if kind=='prg' else save_export(target,result)
                self.editor.status=f"Exported {path.name}: {len(result.data):,} bytes / {result.seconds:.2f}s"
                self.dialog={"title":f"{label} exported", "message":self.editor.status+' '+(' '.join(result.warnings) or 'Editable project and song notes remain intact.'),"hint":"Enter / Esc: close"}
            if target.exists():
                self.dialog={"title":f"Overwrite {label} export?","message":f"Replace {target.name}? Previous export will be kept as {suffix}.bak.","hint":"Y: overwrite | Esc: cancel","yes":write}
            else:write()
        self.text_dialog("Export .prg (C64 program)" if kind=='prg' else "Export .sid (PSID v2NG)",str(default),accept,
                         "C64 PRG: LOAD then RUN on the selected PAL/NTSC machine. RUN/STOP exits. Your editable project is unchanged." if kind=='prg' else
                         "One PAL/NTSC SID, native 6510 player. This does not change your .sidpulse project or its saved/unsaved status.")

    def change_property(self, delta=0, direct=None):
        ed = self.editor
        index = self.property_index
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
            if field in ("released","export_loop"):
                key="loop" if field=="export_loop" else field
                value=ed.song.export_config.get(key,True if key=='loop' else '2026 SIDpulse')
                if key=='released' and direct is None:
                    self.text_dialog("PSID released",value,lambda text:self.change_property(direct=text))
                    return
                new=str(direct).lower() in ('on','true','1','yes') if key=='loop' and direct is not None else not value if key=='loop' else direct
                config=deepcopy(ed.song.export_config);config[key]=new
                ed.edit("Set export "+key,[(("export_config",),config)])
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
            if key in (pg.K_UP, pg.K_DOWN, pg.K_PAGEUP, pg.K_PAGEDOWN):
                self.file_index = max(0, min(len(self.file_entries) - 1, self.file_index + {pg.K_UP: -1, pg.K_DOWN: 1, pg.K_PAGEUP: -12, pg.K_PAGEDOWN: 12}[key]))
            elif key == pg.K_RETURN:
                self.select_file()
            elif key == pg.K_BACKSPACE:
                self.file_dir = self.file_dir.parent
                self.refresh_files()
            elif key == pg.K_TAB:
                self.prompt_filename()
        elif self.page == "orders":
            from sidpulse.ui.orders import handle_key
            handle_key(self,event)
        elif self.page == "samples":
            if key in (pg.K_UP, pg.K_DOWN):
                self.sample_index = max(1, min(99, self.sample_index + (-1 if key == pg.K_UP else 1)))
        elif self.page in ("instrument", "settings"):
            if self.page == 'settings' and self.property_index == 23 and key == pg.K_RETURN:
                self.change_property()
                return
            if self.page == 'settings' and self.property_index == 22 and key in (pg.K_RETURN,pg.K_LEFT,pg.K_RIGHT):
                from sidpulse.ui.autosave_settings import open_dialog
                open_dialog(self)
                return
            if self.page == "instrument" and key == pg.K_TAB:
                choices=("list","buttons","properties")
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
                    if self.instrument_slot in ed.song.instruments:self.instrument_focus = "properties"
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
            maximum = len(INSTRUMENT_FIELDS)-1 if self.page == "instrument" else 23
            if key in (pg.K_UP, pg.K_DOWN):
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
            if self.audio.playback.status != "stopped":
                if not preview_only:ed.enter_note(note)
                ed.status="F8 stops playback so the three SID voices are available for keyboard audition."
                return
            if scan not in self.held:
                instrument = ed.song.instruments.get(ed.instrument)
                if instrument is not None:
                    self.audio.send("on", scan, note, instrument, ed.voice if self.page == "pattern" else None, ed.instrument)
                    self.held.add(scan)
                else:
                    ed.status = "Empty instrument slot. F4: add an instrument or choose a preset."
            if not preview_only:
                ed.enter_note(note)
        elif name == "note":
            ed.enter_note(value)
        elif name in ("audition_cell", "audition_row"):
            scan = event.scancode
            if scan in self.held:
                return
            self.held.add(scan)
            cells = list(enumerate(ed.pattern.rows[ed.row])) if name == "audition_row" else [(ed.voice, ed.cell)]
            tokens = []
            for voice, cell in cells:
                if cell.note is not None and cell.note >= 0 and (cell.instrument or ed.instrument) in ed.song.instruments:
                    token = f"row-{scan}-{voice}"
                    self.audio.send("on", token, cell.note, ed.song.instruments[cell.instrument or ed.instrument], voice)
                    tokens.append(token)
            self.audition_tokens[scan] = tokens
        elif name == "page":
            self.change_page(value)
        elif name in ("move", "step_move"):
            dr, dc, select = value
            ed.move(dr * (max(1, ed.skip) if name == "step_move" else 1), dc, select)
        elif name == "channel":
            if event and event.key == pg.K_TAB and value < 0 and ed.column != 0:
                ed.column = 0
            else:
                ed.voice = max(0, min(2, ed.voice + value))
                ed.column = 0 if event and event.key == pg.K_TAB else ed.column
        elif name == "home_end":
            col, voice, row = (8, 2, len(ed.pattern.rows) - 1) if value else (0, 0, 0)
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
            ed.copy(value)
        elif name == "paste":
            ed.paste(value)
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
        elif name == "skip":
            ed.skip = value
        elif name == "center":
            ed.centered = not ed.centered
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
        elif name == "play":
            self.start_playback(value)
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
        elif name == "helper_toggle":
            self.helper_strip = not self.helper_strip
        elif name == "comments":
            self.text_dialog("Song comments", ed.song.comments, lambda text: ed.edit("Set comments", [(("comments",), text)]), "Shift+Enter: new line. Enter: save notes. Unicode text is preserved in .sidpulse.")
            self.dialog["multiline"]=True
        elif name == 'autosave_settings':
            from sidpulse.ui.autosave_settings import open_dialog
            open_dialog(self)
        elif name == "quit":
            self.confirm_quit()
        elif name == "open":
            self.confirm_discard(lambda: self.browse("open"))
        elif name == "save":
            self.save_project()
        elif name == "save_as":
            self.browse("save")
            self.prompt_filename()
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
            if self.page in ("help", "files"):
                self.page = self.previous_page if self.previous_page not in ("help", "files") else "pattern"
                self.after_save = None
            else:
                self.open_menu()
        elif name == "page_key":
            self.page_key(value)

    def dialog_event(self, event):
        from sidpulse.ui.dialogs import choices,focus
        dialog = self.dialog
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
                self.after_save = None
                pg.key.stop_text_input()
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
                    command = dispatch(event, self.page, self.editor.column)
                    if command and command.name == "page":
                        self.dialog = None
                        self.execute(command, event)
            elif event.key == pg.K_RETURN:
                self.dialog = None

    def handle(self, event):
        if self.diagnostics: self.diagnostics.event(self,event)
        if event.type in (pg.KEYDOWN, pg.KEYUP):
            LOG.debug("type=%s key=%s scan=%s mods=%s page=%s", event.type, event.key, getattr(event,'scancode',0), event.mod, self.page)
        try:
            if event.type==pg.MOUSEMOTION and self.instrument_drag:
                self.update_instrument_drag(event.pos);return
            if event.type==pg.MOUSEBUTTONUP and event.button==1 and self.instrument_drag:
                self.update_instrument_drag(event.pos);self.finish_instrument_drag();return
            if event.type in (pg.KEYDOWN,pg.QUIT,pg.WINDOWFOCUSLOST,pg.VIDEORESIZE):
                self.finish_instrument_drag(cancel=event.type==pg.KEYDOWN and event.key==pg.K_ESCAPE)
            if event.type == pg.QUIT:
                self.confirm_quit()
            elif event.type == pg.WINDOWFOCUSLOST:
                self.release_audition()
                if self.dialog and self.dialog.get('kind') in ('audio_buffer','pattern_length'):
                    self.dialog['drag_rect'] = None
            elif event.type == pg.VIDEORESIZE and not self.fullscreen:
                self.screen = pg.display.set_mode((max(480, event.w), max(360, event.h)), pg.RESIZABLE)
                if self.dialog and self.dialog.get('kind') in ('audio_buffer','pattern_length'):
                    self.dialog['drag_rect'] = None
            elif self.dialog:
                self.dialog_event(event)
            elif self.menu_path:
                self.menu_event(event)
            elif event.type==pg.KEYDOWN and self.page=="pattern" and self.control_focus and not event.mod & (pg.KMOD_ALT|pg.KMOD_CTRL):
                if event.key in (pg.K_UP,pg.K_DOWN,pg.K_PAGEUP,pg.K_PAGEDOWN):
                    self.editor.move(rows={pg.K_UP:-1,pg.K_DOWN:1,pg.K_PAGEUP:-16,pg.K_PAGEDOWN:16}[event.key])
                elif event.key==pg.K_RETURN:self.edit_control()
                elif event.key==pg.K_DELETE:
                    values=deepcopy(self.editor.pattern.controls);values.pop(self.editor.row,None)
                    self.editor.edit("Clear filter row",[(("patterns",self.editor.pattern_id,"controls"),values)])
                elif event.key==pg.K_TAB:self.control_focus=False
                elif event.key>=pg.K_F1 or event.key==pg.K_ESCAPE:
                    self.execute(dispatch(event,self.page,self.editor.column),event)
            elif event.type in (pg.KEYDOWN, pg.KEYUP):
                if self.page == 'orders' and event.type == pg.KEYDOWN:
                    from sidpulse.ui.orders import entry_key
                    if entry_key(self,event): return
                self.execute(dispatch(event, self.page, self.editor.column), event)
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
                elif self.page == "instrument":
                    x=pg.mouse.get_pos()[0]/max(1,self.renderer.cw)
                    if x<32:
                        self.select_instrument_slot(-event.y);self.instrument_focus="list"
                    elif self.instrument_tab in ('general','motion','adsr'):
                        lo,hi=(9,19) if self.instrument_tab=='motion' else (2,5) if self.instrument_tab=='adsr' else (0,8)
                        self.property_index=max(lo,min(hi,self.property_index-event.y));self.instrument_focus='properties'
                elif self.page == 'settings':self.property_index=max(0,min(23,self.property_index-event.y))
            elif event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
                for rect, action, value in reversed(self.renderer.hits):
                    if not rect.collidepoint(event.pos):
                        continue
                    if self.instrument_action(action,value,event.pos):
                        pass
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
                    elif action == "cell":
                        self.control_focus=False
                        self.editor.row, self.editor.voice, self.editor.column = value
                    elif action == "choose_instrument":
                        self.select_instrument_slot(number=value)
                        self.instrument_focus="list"
                    elif action == "setting_edit":
                        self.property_index=value
                        if value in (2,10,15,16,17,19,21,23):self.change_property(1)
                        else:self.page_key(pg.event.Event(pg.KEYDOWN,key=pg.K_RETURN,mod=0))
                    elif action == "property":
                        self.property_index = value
                        self.instrument_focus = "properties"
                    elif action == "waveform":
                        self.editor.edit("Set oscillator waveform", [(("instruments", self.editor.instrument, "waveform"), value)])
                        self.property_index = 1
                        self.instrument_focus = "properties"
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
        while self.running and (frames is None or count < frames):
            if self.diagnostics: self.diagnostics.heartbeat(self)
            for event in pg.event.get():
                self.handle(event)
            self.sync_audio()
            # Snapshot only when due; file serialization/fsync run off the UI thread.
            self.autosave.tick(self.editor, self.metadata, self.path)
            if self.autosave.warning and self.dialog is None:self.show_autosave_warning()
            self.renderer.render(self)
            pg.display.flip()
            if self.audio.error:
                self.editor.status = self.audio.error
            count += 1
            clock.tick(60)
        if screenshot:
            pg.image.save(self.screen, str(screenshot))
