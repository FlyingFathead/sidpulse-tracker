"""Serial sample-tool checks with an identical background page and scopes.

Run after the release benchmark, with no other heavy jobs. The normal product
returns to F3 after fitting; this measurement retains F5's scope background so
that switching views does not make audio CPU artificially look cheaper.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys


def worker(task):
    import benchmark_releases as benchmark
    benchmark.init(task['repo'],task['cpus'])
    import sidpulse.app as app_module
    original=app_module.App
    final={}
    class MeasuredApp(original):
        def __init__(self,*args,**kwargs):
            super().__init__(*args,**kwargs)
            if 'freeze' in task:
                self.editor.instrument=self.instrument_slot=task.get('instrument_number',1)
                if self.instrument_frozen()!=task['freeze']:self.toggle_instrument_freeze()
        def sync_audio(self):
            if task.get('fixed_background'):self.page=task['page']
            return super().sync_audio()
        def close(self):
            final['scopes_at_end']=self.scopes_visible
            return super().close()
    app_module.App=MeasuredApp
    result=benchmark.worker(task)
    return dict(result,**final)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--worker',type=Path)
    for key in ('song','candidate','out'):parser.add_argument('--'+key,type=Path)
    args=parser.parse_args()
    if args.worker:
        print(json.dumps(worker(json.loads(args.worker.read_text()))));return
    source=args.song.resolve();before=source.read_bytes();out=args.out.resolve();out.mkdir(parents=True,exist_ok=True)
    if (out/'results.jsonl').exists():raise SystemExit('Choose a fresh output directory')
    cpus=sorted(os.sched_getaffinity(0))[:2]
    cases=[]
    for size in ((640,480),(960,1080),(1280,900)):
        for enabled in (False,True):
            cases.append(dict(kind='gui',case=f'freeze-{int(enabled)}-{size[0]}x{size[1]}',
                         size=size,page='instrument',freeze=enabled,instrument_number=3,iterations=300))
    for enabled in (False,True):
        cases.append(dict(kind='live',case=f'synthesis-fixed-scopes-{int(enabled)}',size=(960,1080),
                         page='info',frames=2048,seconds=12,sample_synthesis=enabled,fixed_background=True))
    for repeat in range(3):
        for case in (cases if repeat%2==0 else cases[::-1]):
            task=dict(repo=str(args.candidate.resolve()),song=str(source),cpus=cpus if case['kind']=='live' else cpus[:1],
                      scopes=True,label='candidate-pcm',repetition=repeat,**case)
            taskfile=out/'task.json';taskfile.write_text(json.dumps(task))
            run=subprocess.run([sys.executable,str(Path(__file__).resolve()),'--worker',str(taskfile)],capture_output=True,text=True)
            if run.returncode:raise RuntimeError(run.stderr+'\n'+run.stdout)
            record={k:v for k,v in task.items() if k not in ('repo','song')}
            record.update(json.loads(run.stdout.strip().splitlines()[-1]));record['song']=source.name
            with (out/'results.jsonl').open('a') as stream:stream.write(json.dumps(record)+'\n')
            if case['kind']=='live':assert record['scopes_at_end'] and (not case['sample_synthesis'] or record['proposal_ready'])
            print(case['case'],repeat,flush=True)
    (out/'task.json').unlink()
    assert source.read_bytes()==before
    (out/'input.json').write_text(json.dumps(dict(sha256=hashlib.sha256(before).hexdigest(),source_unchanged=True),indent=2)+'\n')


if __name__=='__main__':main()
