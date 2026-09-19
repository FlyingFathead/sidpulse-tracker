"""Set desktop identity and icon once at startup, before creating the window."""
import logging
import os
from pathlib import Path
import sys

APP_ID = 'FlyingFathead.SIDpulseTracker'
WINDOW_CLASS = 'SIDpulseTracker'


def prepare():
    os.environ.setdefault('SDL_APP_NAME', 'SIDpulse Tracker')
    # pygame may seed WM_CLASS from python's entry point while importing.
    os.environ['SDL_VIDEO_X11_WMCLASS'] = WINDOW_CLASS
    os.environ['SDL_VIDEO_WAYLAND_WMCLASS'] = WINDOW_CLASS
    if sys.platform == 'win32':
        try:
            import ctypes
            from ctypes import wintypes
            identify = ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID
            identify.argtypes = [wintypes.LPCWSTR]
            identify.restype = ctypes.c_long
            if identify(APP_ID) < 0:
                logging.getLogger(__name__).warning('Desktop declined SIDpulse application identity.')
        except (AttributeError, OSError):
            logging.getLogger(__name__).warning('Desktop application identity is unavailable.')


def set_icon():
    import pygame as pg
    icon = Path(__file__).resolve().parents[1] / 'assets' / 'sidpulse-icon.png'
    pg.display.set_icon(pg.transform.smoothscale(pg.image.load(str(icon)), (128, 128)))
