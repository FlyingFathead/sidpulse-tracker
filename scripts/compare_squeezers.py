#!/usr/bin/env python3
"""Matched, serial SQUEEZER comparisons; exact input preservation and replay checks.

--isolated measures each trial in a fresh process, including its peak host RSS.
--include-comparison additionally measures the default version-comparison GUI analysis.
Reports contain filenames/hashes rather than developer-machine paths.
"""
import argparse
from dataclasses import asdict
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import time
import platform
import subprocess

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from sidpulse import __version__
from sidpulse.project.format import load
from sidpulse.export.squeeze import SqueezeOptions, squeezer_version_label
from sidpulse.export.psid import compile_song
from sidpulse.export.prg import compile_prg
from sidpulse.export.comparison import compile_comparison


def label(version):
    return 'comparison' if version=='compare' else 'v'+squeezer_version_label(version)


def peak_rss():
    try:
        import resource
        value=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return value/1024 if sys.platform=='darwin' else value
    except ImportError:
        return None


def measure(task):
    path=Path(task['path']);source=path.read_bytes();song,_=load(path);before=deepcopy(song)
    version=task['version'];target=task['target']
    entry=dict(song=path.name,source_sha256=hashlib.sha256(source).hexdigest(),target=target,
               version=version,repetition=task['repetition'],host_peak_before_kib=peak_rss())
    start=time.perf_counter();cpu=time.process_time()
    try:
        if version=='compare':
            comparison=compile_comparison(song,SqueezeOptions(),target)
            if comparison.best is None:raise ValueError('No comparison version fits')
            result=comparison.best.result
            entry['comparison']=[dict(version=e.version,file_bytes=len(e.result.data) if e.result else None,
                                      sha256=hashlib.sha256(e.result.data).hexdigest() if e.result else None,
                                      error=e.error) for e in comparison.entries]
        else:
            compiler=compile_song if target=='sid' else compile_prg
            result=compiler(song,squeeze=SqueezeOptions(version=version))
        entry.update(file_bytes=len(result.data),sha256=hashlib.sha256(result.data).hexdigest(),
                     report=asdict(result.squeeze_report),ticks=result.ticks,seconds=result.seconds,
                     max_cycles_bound=result.max_cycles_bound)
        if task.get('write') and version!='compare':
            (Path(task['write'])/(path.stem+'-squeezer-'+label(version)+'.'+target)).write_bytes(result.data)
    except ValueError as exc:entry['error']=str(exc)
    entry.update(cpu_seconds=time.process_time()-cpu,wall_seconds=time.perf_counter()-start,
                 host_peak_rss_kib=peak_rss())
    if song!=before or path.read_bytes()!=source:raise RuntimeError('Input changed during comparison')
    return entry


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('songs',nargs='*',type=Path)
    parser.add_argument('--out',type=Path)
    parser.add_argument('--repetitions',type=int,default=3)
    parser.add_argument('--write-exports',action='store_true')
    parser.add_argument('--versions',default='1,2,201,202',help='Comma-separated IDs: 1,2,201,202')
    parser.add_argument('--isolated',action='store_true')
    parser.add_argument('--include-comparison',action='store_true')
    parser.add_argument('--worker',action='store_true',help=argparse.SUPPRESS)
    args=parser.parse_args()
    if args.worker:
        print(json.dumps(measure(json.load(sys.stdin))));return
    if args.out is None:parser.error('--out is required')
    args.out.mkdir(parents=True,exist_ok=True)
    if (args.out/'results.jsonl').exists():parser.error('Use a fresh output directory')
    versions=tuple(map(int,args.versions.split(',')))
    for version in versions:SqueezeOptions(version=version)
    if args.include_comparison:versions+=('compare',)
    paths=args.songs or sorted((ROOT/'examples').glob('*.sidpulse'))
    (args.out/'environment.json').write_text(json.dumps(dict(tracker=__version__,python=platform.python_version(),
        platform=platform.system()+' '+platform.machine(),repetitions=args.repetitions,isolated=args.isolated,
        notes='Serial compiler CPU/wall trials. Peak RSS is whole host process, not C64 RAM; cumulative unless isolated. Complete replay verification on every selected compact export.'),indent=2)+'\n')
    for path in paths:
        for repetition in range(args.repetitions):
            for target in ('sid','prg'):
                for version in (versions if repetition%2==0 else versions[::-1]):
                    task=dict(path=str(path.resolve()),target=target,version=version,repetition=repetition,
                              write=str(args.out.resolve()) if args.write_exports and repetition==0 else None)
                    if args.isolated:
                        run=subprocess.run([sys.executable,str(Path(__file__).resolve()),'--worker'],
                                           input=json.dumps(task),capture_output=True,text=True,check=True)
                        entry=json.loads(run.stdout)
                    else:entry=measure(task)
                    with (args.out/'results.jsonl').open('a') as out:out.write(json.dumps(entry)+'\n')
                    print(f"{path.name} {target} {label(version)} #{repetition}: {entry.get('file_bytes',entry.get('error'))}; {entry['cpu_seconds']:.3f}s CPU",flush=True)


if __name__=='__main__':main()
