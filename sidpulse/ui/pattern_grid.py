"""Display-only beat/bar grid; no playback or project-schema changes."""
from dataclasses import asdict, dataclass, replace


@dataclass(frozen=True)
class PatternGrid:
    rows_per_beat: int = 4
    beats_per_bar: int = 4

    def __post_init__(self):
        for name, maximum in (("rows_per_beat", 256), ("beats_per_bar", 32)):
            value = getattr(self, name)
            if type(value) is not int or not 1 <= value <= maximum:
                raise ValueError(f"{name}: use 1..{maximum} in decimal")

    @property
    def rows_per_bar(self):
        return self.rows_per_beat * self.beats_per_bar

    def level(self, row):
        """0: ordinary row, 1: beat, 2: bar; phase resets at pattern row zero."""
        if row % self.rows_per_bar == 0:
            return 2
        return 1 if row % self.rows_per_beat == 0 else 0

    def changed(self, field, *, delta=0, direct=None):
        maxima = {"rows_per_beat": 256, "beats_per_bar": 32}
        if field not in maxima:
            raise ValueError("Unknown pattern-grid field")
        if direct is None:
            value = max(1, min(maxima[field], getattr(self, field) + delta))
        else:
            if not isinstance(direct, (str, int)) or isinstance(direct, bool):
                raise ValueError("Use a whole decimal number")
            value = int(direct)
        return replace(self, **{field: value})

    @classmethod
    def from_metadata(cls, data):
        """Invalid optional UI metadata cannot prevent opening a song."""
        values = {}
        if isinstance(data, dict):
            for name, maximum in (("rows_per_beat", 256), ("beats_per_bar", 32)):
                value = data.get(name)
                if type(value) is int and 1 <= value <= maximum:
                    values[name] = value
        return cls(**values)

    def metadata(self, previous=None):
        # Preserve unknown nested UI fields written by a newer application.
        result = dict(previous) if isinstance(previous, dict) else {}
        result.update(asdict(self))
        return result
