"""Shared console notice for the Linux and Windows launchers; standard library only."""
from pathlib import Path
import shutil


def main():
    version = (Path(__file__).resolve().parents[1] / 'VERSION').read_text(encoding='utf-8').strip()
    line = '-' * shutil.get_terminal_size(fallback=(80, 24)).columns
    print(line)
    print(f'Running SIDpulse Tracker v{version}...')
    print('Do NOT close this window while the program is running!')
    print('Pressing CTRL-C inside this window will force-quit the program')
    print('(WARNING: by doing so, unsaved work will be lost!)')
    print(line, flush=True)


if __name__ == '__main__':
    main()
