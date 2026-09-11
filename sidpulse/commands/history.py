from copy import deepcopy
from dataclasses import dataclass


def get_path(root, path):
    for key in path:
        root = root[key] if isinstance(root, (dict, list)) else getattr(root, key)
    return root


def set_path(root, path, value):
    parent = get_path(root, path[:-1])
    if isinstance(parent, (dict, list)):
        parent[path[-1]] = deepcopy(value)
    else:
        setattr(parent, path[-1], deepcopy(value))


@dataclass(frozen=True)
class Change:
    path: tuple
    before: object
    after: object


@dataclass(frozen=True)
class Edit:
    name: str
    changes: tuple[Change, ...]


class History:
    def __init__(self):
        self.undo_stack = []
        self.redo_stack = []
        self.revision = 0

    def apply(self, song, name, updates):
        changes = tuple(Change(path, deepcopy(get_path(song, path)), deepcopy(value))
                        for path, value in updates if get_path(song, path) != value)
        if not changes:
            return False
        edit = Edit(name, changes)
        for change in changes:
            set_path(song, change.path, change.after)
        self.revision += 1
        self.undo_stack.append(edit)
        self.undo_stack = self.undo_stack[-128:]
        self.redo_stack.clear()
        return True

    def undo(self, song):
        if not self.undo_stack:
            return "Nothing to undo"
        self.revision += 1
        edit = self.undo_stack.pop()
        for change in reversed(edit.changes):
            set_path(song, change.path, change.before)
        self.redo_stack.append(edit)
        return f"Undo: {edit.name}"

    def redo(self, song):
        if not self.redo_stack:
            return "Nothing to redo"
        edit = self.redo_stack.pop()
        for change in edit.changes:
            set_path(song, change.path, change.after)
        self.revision += 1
        self.undo_stack.append(edit)
        return f"Redo: {edit.name}"
