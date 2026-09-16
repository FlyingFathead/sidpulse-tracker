"""Standard-library-only update engine used by the versioned parent-dir launcher.

This module never downloads, runs Git, edits user settings or follows symlinks.
The generated release launcher supplies the expected archive hash and file table.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import sys
import tempfile
import zipfile


class UpdateError(ValueError):
    pass


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def content_digest(data: bytes, text: bool) -> str:
    """Accept Git's CRLF checkout conversion, not arbitrary content changes."""
    return digest(data.replace(b'\r\n', b'\n') if text else data)


def is_link(path: Path) -> bool:
    return path.is_symlink() or bool(getattr(path, 'is_junction', lambda: False)())


def target_path(repo: Path, relative: str) -> Path:
    parts = PurePosixPath(relative).parts
    if (not parts or PurePosixPath(relative).is_absolute() or '\\' in relative
            or any(p in ('', '.', '..') or ':' in p for p in parts)
            or relative != '/'.join(parts)):
        raise UpdateError(f'Unsafe relative path: {relative!r}')
    if (parts[0] in {'.git', '.venv', 'venv', 'user_songs', 'autosave', 'autosaves',
                     'presets', '__pycache__', '.pytest_cache'}
            or parts[-1] in {'preferences.json', 'PROJECT_DETAILS.md',
                              'SIDPULSE_TRACKER_PROJECT_DETAILS_NOT_PUBLIC.md',
                              'bootstrap-history.bundle'}
            or Path(parts[-1]).suffix.lower() in {'.ttf', '.otf', '.woff', '.woff2'}):
        raise UpdateError(f'Protected path is not an update target: {relative}')
    current = repo
    if is_link(current):
        raise UpdateError(f'Repository must not be a symlink/junction: {repo}')
    for index, part in enumerate(parts):
        current = current / part
        if is_link(current):
            raise UpdateError(f'Refusing symlink/junction: {relative}')
        if index < len(parts) - 1 and current.exists() and not current.is_dir():
            raise UpdateError(f'A parent is not a directory: {relative}')
    if current.exists() and not current.is_file():
        raise UpdateError(f'Target is not a regular file: {relative}')
    return current


@dataclass
class PlannedFile:
    relative: str
    path: Path
    content: bytes
    before: bytes | None
    mode: int


def preflight(repo: Path, archive: Path, files: dict, expected_sha256: str,
              base_version: str | tuple[str, ...], version: str) -> list[PlannedFile]:
    if is_link(repo) or not repo.is_dir():
        raise UpdateError('Existing repository directory required; run from its parent or use --repo PATH.')
    if digest(archive.read_bytes()) != expected_sha256:
        raise UpdateError('Archive SHA-256 mismatch. Nothing was changed.')
    version_path = target_path(repo, 'VERSION')
    if not version_path.exists():
        raise UpdateError('Repository VERSION is missing. Nothing was changed.')
    actual_version = version_path.read_text(encoding='utf-8').strip()
    bases = (base_version,) if isinstance(base_version, str) else tuple(base_version)
    if actual_version not in (*bases, version):
        raise UpdateError(f'Expected {" / ".join(bases)} (or already {version}), found {actual_version!r}; refusing overwrite.')
    plan = []
    conflicts = []
    expected_names = {'sidpulse-tracker/' + name for name in files}
    with zipfile.ZipFile(archive) as zipped:
        members = zipped.infolist()
        names = [member.filename for member in members]
        if len(names) != len(set(names)) or set(names) != expected_names:
            raise UpdateError('Archive members do not match the release file table.')
        for member in members:
            if member.is_dir() or stat.S_ISLNK(member.external_attr >> 16):
                raise UpdateError('Unexpected directory/symlink entry in archive.')
        for relative, record in files.items():
            path = target_path(repo, relative)
            payload = zipped.read('sidpulse-tracker/' + relative)
            text = record['text']
            if content_digest(payload, text) != record['after']:
                raise UpdateError(f'Unexpected packaged content: {relative}')
            old = path.read_bytes() if path.exists() else None
            old_hash = content_digest(old, text) if old is not None else None
            if old_hash == record['after']:
                continue  # idempotent after the script or a direct ZIP overlay
            # A cumulative release can accept exact hashes from more than
            # one published baseline; arbitrary edits still abort the update.
            accepted = record['before']
            if not isinstance(accepted, (list, tuple)):
                accepted = (accepted,)
            if old_hash not in accepted:
                conflicts.append(relative)
                continue
            mode = stat.S_IMODE(path.stat().st_mode) if old is not None else record['mode']
            plan.append(PlannedFile(relative, path, payload, old, mode))
    if conflicts:
        raise UpdateError('Local changes or missing baseline files; nothing changed:\n  ' + '\n  '.join(conflicts))
    # Leave VERSION until last, so an interrupted update is not advertised as complete.
    return sorted(plan, key=lambda item: (item.relative == 'VERSION', item.relative))


def apply_plan(repo: Path, plan: list[PlannedFile], release: str) -> Path | None:
    if not plan:
        return None
    backup_root = repo.parent / 'sidpulse-tracker-update-backups'
    if is_link(backup_root) or (backup_root.exists() and not backup_root.is_dir()):
        raise UpdateError('Backup root must be a real directory, not a symlink or file.')
    backup_root.mkdir(exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    backup = backup_root / (release + '-' + stamp)
    backup.mkdir()
    replaced = []
    created_dirs = []
    manifest = {'release': release, 'files': []}
    # Prepare every backup and every staged file before changing the repository.
    with tempfile.TemporaryDirectory(prefix='.sidpulse-update-', dir=repo.parent) as stage_name:
        stage = Path(stage_name)
        for item in plan:
            staged = stage / item.relative
            staged.parent.mkdir(parents=True, exist_ok=True)
            with staged.open('xb') as stream:
                stream.write(item.content)
                stream.flush()
                os.fsync(stream.fileno())
            staged.chmod(item.mode)
            if item.before is not None:
                saved = backup / item.relative
                saved.parent.mkdir(parents=True, exist_ok=True)
                saved.write_bytes(item.before)
                saved.chmod(item.mode)
            manifest['files'].append({'path': item.relative, 'existed': item.before is not None,
                                      'before_sha256': digest(item.before) if item.before is not None else None,
                                      'after_sha256': digest(item.content), 'mode': item.mode})
        (backup / 'RESTORE.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
        try:
            # Recheck all inputs after staging, before the first write.
            for item in plan:
                target = target_path(repo, item.relative)
                current = target.read_bytes() if target.exists() else None
                if current != item.before:
                    raise UpdateError(f'File changed during preflight: {item.relative}')
            for item in plan:
                target = target_path(repo, item.relative)
                missing = []
                parent = target.parent
                while parent != repo and not parent.exists():
                    missing.append(parent)
                    parent = parent.parent
                for directory in reversed(missing):
                    directory.mkdir()
                    created_dirs.append(directory)
                os.replace(stage / item.relative, target)
                replaced.append(item)
        except BaseException as exc:
            rollback_errors = []
            for item in reversed(replaced):
                try:
                    target = target_path(repo, item.relative)
                    # Never erase an edit made by another process after replacement.
                    if not target.exists() or target.read_bytes() != item.content:
                        raise UpdateError('Target changed again; recover manually from the backup')
                    if item.before is None:
                        target.unlink()
                    else:
                        recovery = stage / ('rollback-' + str(len(rollback_errors)) + '-' + digest(item.relative.encode()))
                        recovery.write_bytes(item.before)
                        recovery.chmod(item.mode)
                        os.replace(recovery, target)
                except (OSError, ValueError) as rollback_exc:
                    rollback_errors.append(f'{item.relative}: {rollback_exc}')
            for directory in reversed(created_dirs):
                try:
                    directory.rmdir()
                except OSError:
                    pass
            detail = ('Rollback incomplete: ' + '; '.join(rollback_errors)) if rollback_errors else 'Replaced files were rolled back.'
            raise UpdateError(f'Update failed: {exc}. {detail} Backup: {backup}') from exc
    return backup


def release_cli(*, archive_name: str, expected_sha256: str, files: dict,
                base_version: str | tuple[str, ...], version: str, release: str) -> int:
    baseline_label = base_version if isinstance(base_version, str) else " / ".join(base_version)
    parser = argparse.ArgumentParser(description=f'Check/apply SIDpulse Tracker {baseline_label} -> {version}. Run from the repository parent.')
    parser.add_argument('--repo', type=Path, default=Path.cwd() / 'sidpulse-tracker')
    parser.add_argument('--archive', type=Path, default=Path(__file__).resolve().with_name(archive_name))
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--apply', action='store_true', help='Apply after all checks pass; create sibling backups first')
    mode.add_argument('--check', action='store_true', help='Check only (also the default)')
    args = parser.parse_args()
    try:
        repo = args.repo.expanduser().absolute()
        plan = preflight(repo, args.archive.expanduser(), files, expected_sha256, base_version, version)
        if not plan:
            print(f'Already matches {release}; nothing to change.')
            return 0
        print(f'{len(plan)} files ready for {release}:')
        for item in plan:
            print('  ' + ('update ' if item.before is not None else 'add    ') + item.relative)
        if not args.apply:
            print('Check only. No files changed. Re-run with --apply to install.')
            return 0
        backup = apply_plan(repo, plan, release)
        print(f'Applied {release}. Backup: {backup}')
        print('Review git diff from the repository; no commit or push was performed.')
        return 0
    except (OSError, ValueError, zipfile.BadZipFile) as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        return 2
