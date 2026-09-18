"""Machine preferences are separate from .sidpulse musical data."""
import json
import os
from pathlib import Path
import sys
import tempfile

BUFFERS = (256, 512, 1024, 2048, 4096, 8192)
DEFAULT_BUFFER = 2048


def config_path():
    override = os.environ.get('SIDPULSE_CONFIG_HOME')
    if override:
        root = Path(override)
    elif sys.platform == 'win32':
        root = Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData/Local')) / 'SIDpulse'
    else:
        root = Path(os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config')) / 'sidpulse-tracker'
    return root / 'preferences.json'


def load_preferences():
    try:
        data = json.loads(config_path().read_text())
        size = data.get('audio_buffer', DEFAULT_BUFFER)
        return size if type(size) is int and size in BUFFERS else DEFAULT_BUFFER
    except (OSError, ValueError, AttributeError):
        return DEFAULT_BUFFER


def save_buffer(size):
    if size not in BUFFERS:
        raise ValueError('Supported buffers: 256, 512, 1024, 2048, 4096 or 8192 samples')
    save_preferences({'audio_buffer': size})


def save_preferences(updates):
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {}
    try:
        data = json.loads(path.read_text())
        if not isinstance(data, dict):
            data = {}
    except (OSError, ValueError):
        pass
    data.update(updates)
    fd, name = tempfile.mkstemp(dir=path.parent, suffix='.tmp')
    try:
        with os.fdopen(fd, 'w') as stream:
            json.dump(data, stream, indent=2)
            stream.write('\n')
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


APPEARANCE = {'theme': 'Classic crimson', 'font_size': 16, 'font_bold': True,
              'font_file': '', 'colors': {}}
THEMES = ('Classic crimson', 'Charcoal crimson', 'High contrast')


def load_appearance():
    from copy import deepcopy
    result = deepcopy(APPEARANCE)
    try:
        data = json.loads(config_path().read_text())
        if not isinstance(data, dict):return result
        if data.get('theme') in THEMES:result['theme'] = data['theme']
        size=data.get('font_size',16)
        if type(size) is int and 12 <= size <= 28:result['font_size']=size
        if type(data.get('font_bold')) is bool:result['font_bold']=data['font_bold']
        if isinstance(data.get('font_file'),str):result['font_file']=data['font_file']
        if isinstance(data.get('colors'),dict):result['colors']=data['colors']
    except (ValueError,OSError):pass
    return result


def load_file_browser_dates():
    try:
        value = json.loads(config_path().read_text()).get('file_browser_show_modified', True)
        return value if type(value) is bool else True
    except (OSError, ValueError, AttributeError):
        return True


def load_restart_on_f5():
    try:
        value = json.loads(config_path().read_text()).get('restart_on_f5', False)
        return value if type(value) is bool else False
    except (OSError, ValueError, AttributeError):
        return False


def load_audio_underrun_detection():
    try:
        value = json.loads(config_path().read_text()).get('audio_underrun_detection', True)
        return value if type(value) is bool else True
    except (OSError, ValueError, AttributeError):
        return True


def load_squeeze_options():
    from dataclasses import fields
    from sidpulse.export.squeeze import SqueezeOptions
    try:
        document = json.loads(config_path().read_text())
        data = document.get('export_squeeze', document.get('export_squeezer', {}))
        if not isinstance(data, dict):
            data = {}
        else:
            data = dict(data)
            # Preserve explicit choices made by the earlier local candidates.
            for old, current in (('duplicate_patterns', 'patterns'),
                                 ('identical_instruments', 'instruments'),
                                 ('unused_data', 'unused'), ('compact', 'streams'),
                                 ('phrases', 'streams')):
                if current not in data and type(data.get(old)) is bool:
                    data[current] = data[old]
    except (OSError, ValueError, AttributeError):
        data = {}
    return SqueezeOptions(**{field.name: data[field.name] for field in fields(SqueezeOptions)
                             if type(data.get(field.name)) is bool})


def save_squeeze_options(options):
    from dataclasses import asdict
    from sidpulse.export.squeeze import SqueezeOptions
    if not isinstance(options, SqueezeOptions):
        raise TypeError('Expected SqueezeOptions')
    save_preferences({'export_squeeze': asdict(options)})
