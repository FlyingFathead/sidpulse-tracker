"""Finish the v0.2.38 ZIP overlay by removing obsolete root documents.

Run once after extracting the incremental ZIP into an existing v0.2.37 tree:
    python scripts/finish_update.py

ZIP extraction cannot delete old files. This touches only the exact legacy
document paths below; projects, configuration and autosaves are not traversed.
"""
from pathlib import Path

LEGACY_ROOT_FILES = ('PATTERN_ARPEGGIO.md', 'CHECKPOINT.md', 'CHANGELOG.md')


def main():
    root = Path(__file__).resolve().parents[1]
    if (root/'VERSION').read_text().strip() != '0.2.38':
        raise SystemExit('Extract the v0.2.38 update before running this cleanup.')
    for name in ('PATTERN_ARPEGGIO.md','CHECKPOINT.md','ROADMAP.md','CHANGELOG.md'):
        if not (root/'docs'/name).is_file():
            raise SystemExit(f'Missing docs/{name}; extract the complete update first.')
    for name in LEGACY_ROOT_FILES:
        path = root/name
        if path.exists() or path.is_symlink():
            path.unlink()
            print(f'Removed obsolete root file: {name}')
    print('Update cleanup complete. Guides and development notes are in docs/.')


if __name__ == '__main__':
    main()
