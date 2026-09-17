#!/usr/bin/env python3
"""Measure complete SID/PRG files and resident music RAM without opening SDL.

Run from the repository root. No export/native project is written; --json writes
only this report. With no inputs, benchmark the bundled native examples.
"""
import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sidpulse import __version__
from sidpulse.export.psid import compile_song
from sidpulse.export.prg import compile_prg
from sidpulse.project.format import load


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('songs', nargs='*', type=Path)
    parser.add_argument('--json', type=Path, help='write the measured report here')
    args = parser.parse_args()
    paths = args.songs or sorted((ROOT/'examples').glob('*.sidpulse'))
    records = []
    for path in paths:
        before = path.read_bytes()
        song, _ = load(path)
        for target, compiler in (('sid', compile_song), ('prg', compile_prg)):
            start = time.perf_counter()
            old = compiler(song, squeeze=False)
            new = compiler(song)
            report = new.squeeze_report
            entry = dict(song=path.name, clock=song.clock, loop=song.export_config.get('loop', True),
                         target=target, source_sha256=hashlib.sha256(before).hexdigest(),
                         legacy_file_bytes=len(old.data), squeezed_file_bytes=len(new.data),
                         saved_file_bytes=len(old.data)-len(new.data),
                         reduction_percent=round(100*(1-len(new.data)/len(old.data)),2),
                         legacy_resident_bytes=old.squeeze_report.resident_bytes,
                         squeezed_resident_bytes=report.resident_bytes,
                         ticks=new.ticks, seconds=new.seconds,
                         compile_seconds=round(time.perf_counter()-start,3),
                         legacy_sha256=hashlib.sha256(old.data).hexdigest(),
                         squeezed_sha256=hashlib.sha256(new.data).hexdigest(),
                         report=asdict(report))
            records.append(entry)
            print(f'{path.name} .{target}: {len(old.data):,} -> {len(new.data):,} file bytes; '
                  f'{report.original_resident_bytes:,} -> {report.resident_bytes:,} resident bytes', flush=True)
        if path.read_bytes() != before:
            raise RuntimeError(f'Native source changed while benchmarking: {path.name}')
    data = dict(version=__version__, measurements=records,
                ram_scope='Loaded image plus owned zero page and replay/loader call stack; excludes unrelated C64/ROM/screen workspace.',
                note='Instruction verification is not a full C64/SID audio or hardware-equivalence test.')
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(data, indent=2)+'\n', encoding='utf-8')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
