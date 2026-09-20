"""Measure W and SID modulation FX enabled/disabled, with scopes on.

Run serially after the baseline/candidate release benchmark. Input fixtures
share the same instruments and notes; only W and Z row commands differ.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ('candidate','fixtures','out'):parser.add_argument('--'+key,type=Path,required=True)
    args=parser.parse_args();out=args.out.resolve();out.mkdir(parents=True,exist_ok=True)
    if (out/'results.jsonl').exists():raise SystemExit('Choose a fresh output directory')
    cpus=sorted(os.sched_getaffinity(0))[:2]
    inputs={state:args.fixtures.resolve()/f'automation-{state}.sidpulse' for state in ('off','on')}
    hashes={state:hashlib.sha256(path.read_bytes()).hexdigest() for state,path in inputs.items()}
    cases=[]
    for state in inputs:
        for frames in (2048,512):
            cases.append(dict(kind='audio',case=f'audio-{frames}',state=state,frames=frames,seconds=20))
        cases.append(dict(kind='gui',case='pattern-1280x900',state=state,page='pattern',size=(1280,900),iterations=300))
        for frames in (2048,512):
            cases.append(dict(kind='live',case=f'live-{frames}',state=state,frames=frames,seconds=12,page='info',size=(960,1080)))
    for repetition in range(3):
        for item in (cases if repetition%2==0 else cases[::-1]):
            case=dict(item);state=case.pop('state')
            task=dict(repo=str(args.candidate.resolve()),song=str(inputs[state]),cpus=cpus if case['kind']=='live' else cpus[:1],
                      scopes=True,label=state,repetition=repetition,**case)
            taskfile=out/'task.json';taskfile.write_text(json.dumps(task))
            run=subprocess.run([sys.executable,str(Path(__file__).with_name('benchmark_releases.py')),'--worker',str(taskfile)],capture_output=True,text=True)
            if run.returncode:raise RuntimeError(run.stderr+'\n'+run.stdout)
            record={k:v for k,v in task.items() if k not in ('repo','song')}
            record.update(json.loads(run.stdout.strip().splitlines()[-1]))
            with (out/'results.jsonl').open('a') as stream:stream.write(json.dumps(record)+'\n')
            print(case['case'],state,repetition,flush=True)
    (out/'task.json').unlink()
    assert hashes=={s:hashlib.sha256(p.read_bytes()).hexdigest() for s,p in inputs.items()}
    (out/'inputs.json').write_text(json.dumps(dict(sha256=hashes,source_unchanged=True,scopes=True),indent=2)+'\n')


if __name__=='__main__':main()
