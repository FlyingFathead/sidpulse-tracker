"""Shared Load / Save As / SID / PRG destination-browser state.

No SDL, filesystem writes or song mutations. Directory traversal preserves the
filename draft; only an explicit file choice or a new operation replaces it.
"""
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from .text_edit import TextEdit

SUFFIXES = {'open': '.sidpulse', 'save': '.sidpulse', 'sid': '.sid', 'prg': '.prg'}
LABELS = {'open': 'Open', 'save': 'Save', 'sid': 'Export SID', 'prg': 'Export PRG'}
TITLES = {'open': 'Load Project (F9)', 'save': 'Save Project / Save As (F10)',
          'sid': 'Export .sid (PSID)', 'prg': 'Export .prg (C64 program)'}
FOCI = ('list', 'name', 'directory', 'action', 'cancel')


def default_name(project: Path | None, mode: str) -> str:
    suffix = SUFFIXES[mode]
    if project is None:
        return 'untitled' + suffix
    return Path(project).with_suffix(suffix).name


def filename_caret(name: str) -> int:
    """Start before the extension, ready to append/change a revision suffix."""
    suffix = Path(name).suffix
    return len(name) - len(suffix) if suffix else len(name)


@dataclass
class FileBrowser:
    directory: Path = field(default_factory=Path.cwd)
    mode: str = 'open'
    name: TextEdit = field(default_factory=TextEdit)
    location: TextEdit = field(default_factory=TextEdit)
    focus: str = 'list'
    entries: list[Path] = field(default_factory=list)
    modified: dict[Path, str] = field(default_factory=dict)
    index: int = 0
    error: str = ''
    visible_rows: int = 12
    export_result: object = None
    return_page: str = 'pattern'

    def __post_init__(self):
        self.directory = Path(self.directory).expanduser().absolute()
        self.location.reset(str(self.directory))
        self.set_name(self.name.text or 'untitled.sidpulse')

    def set_name(self, name: str) -> None:
        self.name.reset(str(name), filename_caret(str(name)))

    def start(self, mode: str, project: Path | None = None, result=None) -> None:
        if mode not in SUFFIXES:
            raise ValueError('Unsupported file operation: ' + str(mode))
        self.mode, self.export_result = mode, result
        if project is not None:
            self.directory = Path(project).expanduser().absolute().parent
        self.set_name(default_name(project, mode))
        self.location.reset(str(self.directory))
        self.focus = 'list' if mode == 'open' else 'name'
        self.error = ''
        self.refresh()
        if project and Path(project).absolute() in self.entries:
            self.index = self.entries.index(Path(project).absolute())

    def remember_project(self, project: Path) -> None:
        path = Path(project).expanduser().absolute()
        self.directory = path.parent
        self.location.reset(str(self.directory))
        self.set_name(path.name)

    def refresh(self, select: Path | None = None) -> bool:
        try:
            paths = sorted(self.directory.iterdir(), key=lambda p: (not p.is_dir(), p.name.casefold()))
            self.entries = [self.directory.parent] + [p for p in paths if not p.name.startswith('.')
                           and (p.is_dir() or p.suffix.lower() == SUFFIXES[self.mode])]
            self.modified = {}
            for path in self.entries[1:]:
                try:
                    self.modified[path] = datetime.fromtimestamp(path.stat().st_mtime).strftime('%Y-%m-%d %H:%M')
                except (OSError, ValueError, OverflowError):
                    self.modified[path] = 'Unavailable'
            self.index = self.entries.index(select) if select in self.entries else 0
            self.error = ''
            return True
        except OSError as exc:
            self.entries, self.modified, self.index = [], {}, 0
            self.error = str(exc)
            return False

    def navigate(self, target: Path) -> bool:
        target = Path(target).expanduser().absolute()
        try:
            if not target.is_dir():
                raise ValueError('Not an accessible directory: ' + str(target))
            # Check before replacing the current directory or list.
            next(target.iterdir(), None)
        except (OSError, ValueError) as exc:
            self.error = str(exc)
            return False
        previous = self.directory
        self.directory = target
        self.location.reset(str(target))
        self.focus = 'list'
        return self.refresh(select=previous)

    def enter_directory(self) -> bool:
        value = self.location.text.strip()
        if not value:
            self.error = 'Enter a directory.'
            return False
        target = Path(value).expanduser()
        if not target.is_absolute():
            target = self.directory / target
        return self.navigate(target)

    def move(self, delta: int) -> None:
        self.index = max(0, min(max(0, len(self.entries) - 1), self.index + delta))

    def tab(self, backwards: bool = False) -> None:
        self.focus = FOCI[(FOCI.index(self.focus) + (-1 if backwards else 1)) % len(FOCI)]

    @property
    def field(self) -> TextEdit | None:
        return self.name if self.focus == 'name' else self.location if self.focus == 'directory' else None

    @property
    def selected(self) -> Path | None:
        return self.entries[self.index] if 0 <= self.index < len(self.entries) else None

    def target(self) -> Path:
        # Reject empty/whitespace-only input, but never silently trim real names.
        value = self.name.text
        if not value.strip():
            raise ValueError('Enter a filename.')
        if any(ord(c) < 32 or c == '\x7f' for c in value):
            raise ValueError('A filename cannot contain control characters.')
        target = Path(value).expanduser()
        if not target.is_absolute():
            target = self.directory / target
        if target.is_dir():
            raise ValueError('That is a directory. Use the directory field or open it in the list.')
        if value.endswith(('/', '\\')) or target.name in ('', '.', '..'):
            raise ValueError('Enter a filename, not a directory.')
        if self.mode != 'open':
            suffix = SUFFIXES[self.mode]
            if target.suffix.lower() != suffix:
                target = target.with_suffix(suffix)
        return target
