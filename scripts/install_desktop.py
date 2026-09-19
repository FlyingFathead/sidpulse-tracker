#!/usr/bin/env python3
"""Install this checkout's Linux launcher and icon in the current user's menu."""
import os
from pathlib import Path


def install(root, data_home):
    root = Path(root).resolve()
    launcher = root / 'run.sh'
    if not launcher.is_file():
        raise ValueError('Run this installer from a complete SIDpulse checkout.')
    # Desktop Entry quoted arguments need two levels of backslash escaping.
    command = str(launcher)
    if any(c in command for c in '\n\r'):
        raise ValueError('The checkout path cannot contain a line break.')
    command = command.replace('\\', '\\\\\\\\').replace('"', '\\\\"').replace('`', '\\\\`').replace('$', '\\\\$').replace('%','%%')
    data_home = Path(data_home)
    icon = data_home.resolve() / 'icons/SIDpulseTracker.png'
    entry = data_home / 'applications/SIDpulseTracker.desktop'
    icon.parent.mkdir(parents=True, exist_ok=True)
    entry.parent.mkdir(parents=True, exist_ok=True)
    icon.write_bytes((root / 'sidpulse/assets/sidpulse-icon.png').read_bytes())
    entry.write_text('[Desktop Entry]\nType=Application\nName=SIDpulse Tracker\n'
                     'Comment=SID music tracker\nExec="'+command+'" %f\n'
                     'Icon='+str(icon).replace('\\','\\\\')+'\nStartupWMClass=SIDpulseTracker\n'
                     'Terminal=true\nCategories=AudioVideo;Audio;Music;\n',encoding='utf-8')
    return entry


if __name__ == '__main__':
    checkout = Path(__file__).resolve().parents[1]
    data_home = Path(os.environ.get('XDG_DATA_HOME', str(Path.home()/'.local/share')))
    print('Installed:', install(checkout, data_home))
