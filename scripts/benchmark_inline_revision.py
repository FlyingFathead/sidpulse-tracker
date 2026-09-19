#!/usr/bin/env python3
"""Compare two snapshots on the same unchanged automation stress song.

UI and audio CPU are separate; all workers and version pairs run serially.
The full native audio case traverses the complete v8 arrangement. SDL dummy
callbacks measure scheduling counters, not physical audio-device latency.
"""
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import subprocess
import sys


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('baseline','candidate','input','out'):parser.add_argument('--'+name,required=True,type=Path)
    parser.add_argument('--repetitions',type=int,default=3)
    parser.add_argument('--phases',default='gui,audio,live')
    args=parser.parse_args();out=args.out;out.mkdir(parents=True,exist_ok=True)
    if (out/'results.jsonl').exists():parser.error('Use a fresh output directory')
    source=args.input.read_bytes();phases=args.phases.split(',');cpus=sorted(os.sched_getaffinity(0))
    env=dict(python=platform.python_version(),pygame=importlib.metadata.version('pygame-ce'),
             pyresidfp=importlib.metadata.version('pyresidfp'),platform=platform.system()+' '+platform.machine(),
             drivers='SDL dummy audio/video',affinity_available=cpus,source_sha256=hashlib.sha256(source).hexdigest(),
             source=args.input.name,repetitions=args.repetitions,features='M/S buttons and scopes enabled unless case explicitly says off')
    (out/'environment.json').write_text(json.dumps(env,indent=2)+'\n')
    versions=[('baseline',args.baseline),('candidate',args.candidate)]
    def launch(label,repo,case,repetition):
        task=dict(repo=str(repo.resolve()),song=str(args.input.resolve()),repetition=repetition,label=label,
                  cpus=cpus[:2] if case['kind']=='live' else cpus[:1],**case)
        taskfile=out/'task.json';taskfile.write_text(json.dumps(task))
        run=subprocess.run([sys.executable,str(Path(__file__).with_name('benchmark_releases.py')),
                            '--worker',str(taskfile.resolve())],capture_output=True,text=True)
        if run.returncode:raise RuntimeError(run.stderr+'\n'+run.stdout)
        result=json.loads(run.stdout.strip().splitlines()[-1])
        record={k:v for k,v in task.items() if k not in ('repo','song')};record['song']=args.input.name;record.update(result)
        with (out/'results.jsonl').open('a') as f:f.write(json.dumps(record)+'\n')
        metric=result.get('cpu_ms_per_block',result.get('cpu_ms_per_frame',result.get('audio_process_core_percent')))
        print(f"{case['kind']} {case['case']} {label} #{repetition}: {metric:.3f}",flush=True)
    for repetition in range(args.repetitions):
        order=versions if repetition%2==0 else versions[::-1]
        if 'gui' in phases:
            for page in ('pattern','instrument','info','samples'):
                case=dict(kind='gui',case=page,size=(960,1080),page=page,scopes=True,iterations=400)
                for label,repo in order:launch(label,repo,case,repetition)
            for page in ('instrument','samples'):
                case=dict(kind='gui',case='scroll-'+page,size=(960,1080),page=page,scopes=True,scrolling=True,iterations=400)
                for label,repo in order:launch(label,repo,case,repetition)
            case=dict(kind='gui',case='record-pw',size=(960,1080),page='instrument',scopes=True,recording=True,iterations=400)
            for label,repo in order:launch(label,repo,case,repetition)
        if 'audio' in phases:
            for frames,seconds in ((2048,200),(512,15)):
                case=dict(kind='audio',case=f'v8-{frames}-{seconds}s',frames=frames,seconds=seconds,scopes=True)
                for label,repo in order:launch(label,repo,case,repetition)
        if 'live' in phases:
            for page,frames,recording in (('info',2048,False),('info',512,False),('instrument',2048,True)):
                case=dict(kind='live',case=f'{page}-{frames}'+('-record-pw' if recording else ''),
                          size=(960,1080),page=page,frames=frames,seconds=15,scopes=True,recording=recording)
                for label,repo in order:launch(label,repo,case,repetition)
            case=dict(kind='live',case='instrument-2048-record-attack',size=(960,1080),page='instrument',
                      frames=2048,seconds=15,scopes=True,recording=True,recording_parameter='attack')
            launch('candidate',args.candidate,case,repetition)
    assert args.input.read_bytes()==source
    (out/'task.json').unlink(missing_ok=True)


if __name__=='__main__':main()
