"""Pause the pygame-owned SDL device without holding Python's GIL.

pygame-ce 2.5.7 AudioDevice.pause calls SDL_PauseAudioDevice with the GIL held.
SDL waits for the callback, which needs that GIL: an intermittent deadlock.
CDLL calls release the GIL. Resolve the SDL already shipped with pygame, never
an unrelated system SDL whose device IDs belong to a different instance.
"""
import ctypes
from functools import lru_cache
from pathlib import Path
import sys


@lru_cache(maxsize=1)
def _pause_function():
    import pygame
    package = Path(pygame.__file__).parent
    candidates = ([package / 'SDL2.dll'] if sys.platform == 'win32' else
                  [Path(pygame.base.__file__), *package.glob('*SDL2*.dylib')])
    for path in candidates:
        if not path.is_file():
            continue
        try:
            library = ctypes.CDLL(str(path))
            function = library.SDL_PauseAudioDevice
        except (OSError, AttributeError):
            continue
        function.argtypes = (ctypes.c_uint32, ctypes.c_int)
        function.restype = None
        return function
    raise RuntimeError('Cannot locate pygame\'s SDL audio controls safely. Audio is disabled.')


def pause_device(device, paused):
    _pause_function()(device.deviceid, int(paused))


def close_device(device):
    # Once paused, SDL guarantees no callback is in flight. pygame's close and
    # later destructor can then run without waiting for Python callback code.
    pause_device(device, True)
    device.close()
