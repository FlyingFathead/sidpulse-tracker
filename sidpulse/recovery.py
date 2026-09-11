"""Independent recovery snapshots, with per-session locks and atomic metadata."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import tempfile
import time
from uuid import uuid4

from sidpulse.preferences import config_path, save_preferences
from sidpulse.project.format import save


def atomic_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(dir=path.parent, suffix='.tmp')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(data, stream, ensure_ascii=False, indent=2)
            stream.flush(); os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name): os.unlink(name)


class SessionLock:
    """An OS-released lock distinguishes a crashed session from another instance."""
    def __init__(self, path):
        self.file = open(path, 'a+b')
        try:
            if self.file.tell() == 0:
                self.file.write(b'1'); self.file.flush()
            self.file.seek(0)
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(self.file.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BaseException:
            self.file.close()
            raise

    def close(self):
        if self.file.closed: return
        if os.name == 'nt':
            import msvcrt
            self.file.seek(0); msvcrt.locking(self.file.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            fcntl.flock(self.file, fcntl.LOCK_UN)
        self.file.close()


def preferences():
    result = {'autosave_enabled': True, 'autosave_minutes': 5,
              'autosave_directory': str(Path(__file__).resolve().parents[1] / 'autosave')}
    try:
        data = json.loads(config_path().read_text(encoding='utf-8'))
        if type(data.get('autosave_enabled')) is bool:
            result['autosave_enabled'] = data['autosave_enabled']
        value = data.get('autosave_minutes')
        if type(value) is int and 1 <= value <= 60:
            result['autosave_minutes'] = value
        value = data.get('autosave_directory')
        if isinstance(value, str) and value.strip():
            result['autosave_directory'] = str(Path(value).expanduser().absolute())
    except (OSError, ValueError, AttributeError): pass
    return result


class Autosave:
    def __init__(self):
        self.settings = preferences()
        self.session = uuid4().hex
        self.state_path = config_path().parent / 'recovery' / (self.session + '.json')
        self.state = {'session': self.session, 'clean': False, 'autosave': None}
        self.lock = None
        self.started = False
        self.warning = None
        self.blocked = False
        self.next_due = time.monotonic() + self.minutes * 60
        self.saved_revision = None
        self.document = None
        self.future = None
        self.executor = None
        self.closed = False

    @property
    def enabled(self): return self.settings['autosave_enabled']
    @property
    def minutes(self): return self.settings['autosave_minutes']
    @property
    def directory(self): return Path(self.settings['autosave_directory'])

    def ensure_directory(self):
        self.directory.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryFile(dir=self.directory) as check:
            check.write(b'SIDpulse autosave write check'); check.flush()

    def fail(self, exc):
        self.saved_revision = None
        self.blocked = True
        self.warning = (f'Autosave could not use {self.directory}: {exc}. '
                        'Open Settings > Autosave settings to choose or create a writable folder.')

    def start(self):
        if self.started: return
        self.started = True
        if not self.enabled: return
        try:
            self.ensure_directory()
            self.state_path.parent.mkdir(parents=True, exist_ok=True)
            self.lock = SessionLock(self.state_path.with_suffix('.lock'))
            atomic_json(self.state_path, self.state)
        except OSError as exc: self.fail(exc)

    def configure(self, enabled, minutes, directory):
        if type(minutes) is not int or not 1 <= minutes <= 60:
            raise ValueError('Autosave interval must be 1..60 minutes')
        self.flush()
        settings = {'autosave_enabled': bool(enabled), 'autosave_minutes': minutes,
                    'autosave_directory': str(Path(directory).expanduser().absolute())}
        save_preferences(settings)
        self.settings = settings
        self.saved_revision = None
        self.blocked = False; self.warning = None
        self.next_due = time.monotonic() + minutes * 60
        if enabled:
            if not self.lock:
                self.started = False; self.start()
            else:
                try: self.ensure_directory()
                except OSError as exc: self.fail(exc)
        # Turning off preserves existing recovery files; it stops future writes.

    def poll(self):
        if self.future and self.future.done():
            future, self.future = self.future, None
            try: future.result()
            except Exception as exc: self.fail(exc)

    def flush(self):
        if self.future:
            try: self.future.result()
            except Exception as exc: self.fail(exc)
            self.future = None

    def tick(self, editor, metadata, source=None, now=None):
        self.poll()
        if not self.started or self.closed or not self.enabled or self.blocked: return
        now = time.monotonic() if now is None else now
        if self.document is not editor:
            self.document = editor; self.saved_revision = None
            self.next_due = now + self.minutes * 60
        if self.future or now < self.next_due: return
        self.next_due = now + self.minutes * 60
        if not editor.dirty or self.saved_revision == editor.history.revision: return
        # Only immutable-to-the-worker copies cross the UI/file-worker boundary.
        song, meta = deepcopy(editor.song), deepcopy(metadata() if callable(metadata) else metadata)
        revision = editor.history.revision
        if self.executor is None:
            self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='sidpulse-autosave')
        self.future = self.executor.submit(self._write, song, meta, source)
        self.saved_revision = revision

    def _write(self, song, metadata, source):
        stamp = datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S-%f')
        target = self.directory / f'autosave-{stamp}-{self.session[:8]}.sidpulse'
        source = str(Path(source).expanduser().absolute()) if source else None
        metadata['recovery_source'] = source
        save(target, song, metadata)
        self.state.update(autosave=str(target), title=song.title,
                          source=str(source) if source else None, saved_at=stamp, clean=False)
        atomic_json(self.state_path, self.state)
        return target

    def emergency(self, editor, metadata, source):
        if not self.enabled or self.blocked: return None
        self.flush()
        try:
            return self._write(deepcopy(editor.song), deepcopy(metadata), source)
        except Exception as exc:
            self.fail(exc)
            return None

    def candidates(self):
        if not self.enabled: return []
        candidates = []
        for marker in self.state_path.parent.glob('*.json'):
            if marker == self.state_path: continue
            guard = None
            try:
                guard = SessionLock(marker.with_suffix('.lock'))
                data = json.loads(marker.read_text(encoding='utf-8'))
                if data.get('clean') is False and data.get('autosave') and Path(data['autosave']).is_file():
                    candidates.append((marker, data))
            except (OSError, ValueError, AttributeError): pass
            finally:
                if guard: guard.close()
        return sorted(candidates, key=lambda item: item[1].get('saved_at', ''), reverse=True)

    def acknowledge(self, marker):
        guard = SessionLock(marker.with_suffix('.lock'))
        try:
            data = json.loads(marker.read_text(encoding='utf-8'))
            data['clean'] = True  # recovery decision acknowledged; keep its file
            atomic_json(marker, data)
        finally: guard.close()

    def close(self, clean=True):
        if self.closed: return
        self.flush()
        if self.executor: self.executor.shutdown(wait=True)
        try:
            if self.lock and clean:
                self.state['clean'] = True
                atomic_json(self.state_path, self.state)
        except OSError as exc: self.warning = str(exc)
        finally:
            if self.lock: self.lock.close()
            self.closed = True
