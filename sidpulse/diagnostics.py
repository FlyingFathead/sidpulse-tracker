"""Persistent Python/native crash reports and an event-loop hang watchdog."""
from collections import deque
from datetime import datetime, timezone
import faulthandler
import json
import logging
import os
from pathlib import Path
import platform
import sys
import tempfile
import traceback
import time
from uuid import uuid4
from sidpulse.preferences import config_path

_ACTIVE = None


class Diagnostics:
    def __init__(self):
        self.stream = None
        self.path = None
        self.events = deque(maxlen=40)
        self.context = {}
        self.old_hook = None
        self.last_arm = -float("inf")

    def start(self):
        global _ACTIVE
        stamp = datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')
        name = f'sidpulse-{stamp}-{uuid4().hex[:8]}.log'
        roots = (config_path().parent / 'logs', Path(tempfile.gettempdir()) / 'SIDpulse-logs')
        for root in roots:
            try:
                root.mkdir(parents=True, exist_ok=True)
                self.path = root / name
                self.stream = self.path.open('w', encoding='utf-8', buffering=1)
                break
            except OSError: continue
        if self.stream is None: return
        from sidpulse import __version__
        self.stream.write(f'SIDpulse Tracker {__version__}\nPython {sys.version}\n{platform.platform()}\n')
        faulthandler.enable(file=self.stream, all_threads=True)
        self.old_hook = __import__('threading').excepthook
        def hook(args):
            self.exception(f'Thread {args.thread.name}', args.exc_value)
        __import__('threading').excepthook = hook
        _ACTIVE = self
        faulthandler.dump_traceback_later(15,repeat=True,file=self.stream)
        self.last_arm = time.monotonic()

    def event(self, app, event):
        import pygame as pg
        if event.type in (pg.KEYDOWN, pg.KEYUP, pg.MOUSEBUTTONDOWN, pg.QUIT):
            # Never record typed text, filenames or song contents.
            item = {'type': event.type, 'page': app.page}
            if not app.dialog or 'text' not in app.dialog:
                for key in ('key', 'scancode', 'mod', 'button'):
                    if hasattr(event, key): item[key] = getattr(event, key)
            self.events.append(item)
            if self.stream: self.stream.write("Input " + json.dumps(item) + "\n")

    def heartbeat(self, app):
        if not self.stream: return
        ed = app.editor
        context = {'page': app.page, 'pattern': ed.pattern_id, 'row': ed.row,
                   'voice': ed.voice, 'column': ed.column, 'revision': ed.history.revision,
                   'playback': app.audio.playback.status, 'audio_error': app.audio.error}
        if context != self.context:
            self.stream.write('State ' + json.dumps(context) + '\n')
            self.context = context
        # Native watchdog can dump all stacks even if Python's GIL is deadlocked.
        now = time.monotonic()
        if now - self.last_arm >= 1:
            faulthandler.dump_traceback_later(15, repeat=True, file=self.stream)
            self.last_arm = now

    def exception(self, origin, exc):
        if not self.stream:
            traceback.print_exception(exc)
            return
        self.stream.write(f'\nERROR: {origin}\n')
        self.stream.write('State ' + json.dumps(self.context) + '\nRecent input ' + json.dumps(list(self.events)) + '\n')
        traceback.print_exception(type(exc), exc, exc.__traceback__, file=self.stream)
        self.stream.flush()
        try: os.fsync(self.stream.fileno())
        except OSError: pass

    def close(self):
        global _ACTIVE
        if self.stream:
            faulthandler.cancel_dump_traceback_later()
            faulthandler.disable()
            self.stream.close()
            self.stream = None
        if self.old_hook: __import__('threading').excepthook = self.old_hook
        if _ACTIVE is self: _ACTIVE = None


def record_exception(origin, exc):
    if _ACTIVE: _ACTIVE.exception(origin, exc)
    else: logging.getLogger('sidpulse').error('%s', origin, exc_info=(type(exc), exc, exc.__traceback__))


def show_crash(path, recovery=None, interactive=True):
    message = 'SIDpulse Tracker stopped unexpectedly.'
    message += f'\nCrash report: {path}' if path else '\nThe crash report could not be written.'
    if recovery: message += f'\nRecovery project: {recovery}'
    print(message, file=sys.stderr, flush=True)
    if sys.platform == 'win32' and interactive:
        import ctypes
        ctypes.windll.user32.MessageBoxW(None, message, 'SIDpulse Tracker error', 0x10)
