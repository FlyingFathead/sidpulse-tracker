"""App-facing file operations; every destination uses the same browser page."""
from pathlib import Path
from .file_browser import LABELS, SUFFIXES


class FileActions:
    # Keep the previous App file-browser attributes compatible for integrations.
    @property
    def file_dir(self):
        return self.browser.directory

    @file_dir.setter
    def file_dir(self, value):
        self.browser.directory = Path(value).expanduser().absolute()
        self.browser.location.reset(str(self.browser.directory))

    @property
    def file_mode(self):
        return self.browser.mode

    @file_mode.setter
    def file_mode(self, value):
        if value not in SUFFIXES:
            raise ValueError('Unsupported file operation: ' + str(value))
        self.browser.mode = value

    @property
    def file_name(self):
        return self.browser.name.text

    @file_name.setter
    def file_name(self, value):
        self.browser.set_name(value)

    @property
    def file_entries(self):
        return self.browser.entries

    @property
    def file_modified(self):
        return self.browser.modified

    @property
    def file_index(self):
        return self.browser.index

    @file_index.setter
    def file_index(self, value):
        self.browser.index = max(0, min(max(0, len(self.browser.entries) - 1), int(value)))

    def sync_file_text_input(self):
        import pygame as pg
        if self.page == 'files' and self.dialog is None and self.browser.field is not None:
            pg.key.start_text_input()
        else:
            pg.key.stop_text_input()

    def file_status(self):
        b = self.browser
        self.editor.status = b.error or ('Tab: list/name/directory/buttons | Ctrl+L: directory | '
                            'Enter: ' + LABELS[b.mode].lower() + ' | Esc: cancel')

    def browse(self, mode, *, result=None):
        self.release_audition()
        if self.page != 'files':
            self.previous_page = self.page
            self.browser.return_page = self.page if self.page not in ('files', 'help') else 'pattern'
        self.page = 'files'
        self.browser.start(mode, self.path, result)
        self.file_status()
        self.sync_file_text_input()

    def refresh_files(self):
        self.browser.refresh(select=self.browser.selected)
        self.file_status()

    def file_navigate(self, path):
        self.browser.navigate(path)
        self.file_status()
        self.sync_file_text_input()

    def select_file(self):
        path = self.browser.selected
        if path is None:
            return
        if path.is_dir():
            self.file_navigate(path)
        else:
            self.browser.set_name(path.name)
            if self.file_mode in ('open', 'sample'):
                self.submit_file()
            else:
                self.prompt_filename()

    def prompt_filename(self):
        # Inline, not a modal that hides directories or steals the arrow keys.
        self.browser.focus = 'name'
        self.file_status()
        self.sync_file_text_input()

    def cancel_browser(self):
        self.page = self.browser.return_page
        self.after_save = None
        self.browser.export_result = None
        self.editor.status = 'File operation cancelled. Project unchanged.'
        self.sync_file_text_input()

    def _file_error(self, exc):
        self.browser.error = str(exc)
        self.browser.focus = 'name'
        self.file_status()
        self.sync_file_text_input()

    def _resume_file_browser(self):
        self.browser.focus = 'name'
        self.file_status()
        self.sync_file_text_input()

    def submit_file(self):
        b = self.browser
        try:
            if b.location.text != str(b.directory):
                if not b.enter_directory():
                    self.file_status()
                    self.sync_file_text_input()
                    return
            # A directory entered in Filename navigates instead of writing it.
            raw = Path(b.name.text).expanduser() if b.name.text.strip() else None
            raw = b.directory / raw if raw is not None and not raw.is_absolute() else raw
            if raw is not None and raw.is_dir():
                self.file_navigate(raw)
                return
            target = b.target()
            if b.mode == 'open':
                self.open_project(target)
                return
            if b.mode == 'sample':
                self.start_sample_import(target)
                return
            mode, result = b.mode, b.export_result
            loops = b.loop_count() if b.audio_export else 0
            if mode in ('sid', 'prg') and result is None:
                raise ValueError('No compiled export is ready. Reopen Export from the File menu.')

            def write():
                try:
                    if mode == 'save':
                        self.save_project(target)
                    elif mode in ('wav', 'mp3'):
                        self.start_audio_export(target, mode, loops)
                    else:
                        self._write_export(target, result, mode)
                except (OSError, ValueError) as exc:
                    self._file_error(exc)

            if target.exists():
                self.dialog = {'title': 'Overwrite ' + ('project?' if mode == 'save' else mode.upper() + ' export?'),
                               'message': f'Replace {target.name}? The previous file will be kept as {target.suffix}.bak.',
                               'yes': write, 'on_cancel': self._resume_file_browser,
                               'hint': 'Y: overwrite | Esc: return to filename'}
                self.sync_file_text_input()
            else:
                write()
        except (OSError, ValueError) as exc:
            self._file_error(exc)

    def prompt_export(self, result, kind='sid'):
        self.browse(kind, result=result)

    def _write_export(self, target, result, kind):
        from sidpulse.export.prg import save_prg
        from sidpulse.export.psid import save_export
        path = save_prg(target, result) if kind == 'prg' else save_export(target, result)
        self.file_dir = path.parent
        self.browser.export_result = None
        self.page = self.browser.return_page
        self.editor.status = f'Exported {path.name}: {len(result.data):,} bytes / {result.seconds:.2f}s'
        self.notice(kind.upper() + ' exported', self.editor.status + ' ' +
                    ((result.squeeze_report.summary() + ' ') if result.squeeze_report else '') +
                    (' '.join(result.warnings) or 'Editable project and song notes remain intact.'))
        self.sync_file_text_input()
