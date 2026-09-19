"""Comparable exports from one snapshot, with request-local work reuse."""
from dataclasses import dataclass, replace

from .squeeze import squeezer_version_label


@dataclass(frozen=True)
class VersionResult:
    version: int
    result: object = None
    error: str = ''


@dataclass(frozen=True)
class Comparison:
    entries: tuple[VersionResult, ...]

    @property
    def leaders(self):
        """Equal best file/RAM/cycle results; unknown cycles never mean zero."""
        valid = [entry for entry in self.entries if entry.result is not None]
        def cost(entry):
            result = entry.result; report = result.squeeze_report
            return (len(result.data), report.resident_bytes,
                    report.verified_max_cycles or float('inf'))
        if not valid: return ()
        minimum = min(map(cost,valid))
        return tuple(entry for entry in valid if cost(entry)==minimum)

    @property
    def best(self):
        return max(self.leaders,key=lambda entry:entry.version,default=None)

    def preferred(self, version):
        return next((entry for entry in self.leaders if entry.version==version),self.best)


def compile_comparison(song, options, kind, *, progress=None):
    from .psid import compile_song, ExportMemoryError
    from .prg import compile_prg
    if kind not in ('sid', 'prg'): raise ValueError('Comparison target must be SID or PRG')
    compiler = compile_prg if kind == 'prg' else compile_song
    cache, entries = {}, []
    # Cache lifetime cannot outlive this immutable song/settings/target snapshot.
    for version in (1, 2, 201, 202):
        if progress:
            progress('Comparing SQUEEZER v'+squeezer_version_label(version)+'...',
                     'Same song and settings; shared analysis work is reused.')
        try:
            result = compiler(song, squeeze=replace(options, version=version),
                              progress=progress, _comparison_cache=cache)
            entries.append(VersionResult(version, result))
        except ExportMemoryError as exc:
            # One version may not fit where another does. Semantic failures
            # remain fatal; they are never presented as a successful comparison.
            entries.append(VersionResult(version, error=str(exc)))
    return Comparison(tuple(entries))
