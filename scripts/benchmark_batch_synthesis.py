"""Serial batch-fitting on/off trials with the same song, Info page and scopes.

Fitting proposes instruments without applying them, so the playing song remains
identical. Run separately from tests, emulators and other benchmarks.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time


def worker(task):
    import benchmark_releases as benchmark
    benchmark.init(task['repo'],task['cpus'])
    import sidpulse.app as app_module
    from sidpulse.ui import sample_synthesis, batch_synthesis, export_squeezer
    from sidpulse.export.squeeze import SqueezeOptions
    original = app_module.App
    final = {}
    def menu():
        return dict(kind='export_squeezer',title='Export PRG',target='prg',pcm=True,
                    result=None,source=None,options=SqueezeOptions(),compare=False,focus=7,scroll=0)
    def begin(app):
        app.batch_started = time.monotonic()
        batch_synthesis.begin(app,menu())
    sample_synthesis.begin = begin
    class MeasuredApp(original):
        def __init__(self,*args,**kwargs):
            super().__init__(*args,**kwargs)
            if task.get('pcm_warning'):
                self.dialog=menu();export_squeezer.activate(self,'export')
        def sync_audio(self):
            self.page=task['page']
            return super().sync_audio()
        def poll_media_jobs(self):
            super().poll_media_jobs()
            if self.dialog and self.dialog.get('kind')=='sample_synthesis_batch':
                final.setdefault('fit_seconds',time.monotonic()-self.batch_started)
        def close(self):
            final['scopes_at_end']=self.scopes_visible
            final['batch_proposal_ready']=bool(self.dialog and self.dialog.get('kind')=='sample_synthesis_batch')
            if final['batch_proposal_ready']:
                final['fitted_samples']=self.dialog['result']['fitted_samples']
                final['proposals']=len(self.dialog['result']['proposals'])
            final['applied_edits']=len(self.editor.history.undo_stack)
            return super().close()
    app_module.App=MeasuredApp
    result=benchmark.worker(task)
    result.pop('proposal_ready',None)  # the shared runner recognizes the single-fit window
    return dict(result,**final)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--worker',type=Path)
    for key in ('song','candidate','out'):parser.add_argument('--'+key,type=Path)
    args=parser.parse_args()
    if args.worker:
        print(json.dumps(worker(json.loads(args.worker.read_text()))));return
    source=args.song.resolve();before=source.read_bytes()
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=True)
    if (out/'results.jsonl').exists():raise SystemExit('Choose a fresh output directory')
    cpus=sorted(os.sched_getaffinity(0))[:2]
    cases=[]
    for size in ((640,480),(1280,900)):
        for enabled in (False,True):
            cases.append(dict(kind='gui',case=f'popup-{size[0]}x{size[1]}',enabled=enabled,
                              pcm_warning=enabled,size=size,page='info',iterations=300))
    for frames in (2048,512):
        for enabled in (False,True):
            cases.append(dict(kind='live',case=f'batch-{frames}',enabled=enabled,
                              sample_synthesis=enabled,size=(960,1080),page='info',frames=frames,seconds=15))
    for repetition in range(3):
        for case in (cases if repetition%2==0 else cases[::-1]):
            task=dict(repo=str(args.candidate.resolve()),song=str(source),scopes=True,
                      cpus=cpus if case['kind']=='live' else cpus[:1],label='candidate',repetition=repetition,**case)
            taskfile=out/'task.json';taskfile.write_text(json.dumps(task))
            run=subprocess.run([sys.executable,str(Path(__file__).resolve()),'--worker',str(taskfile)],capture_output=True,text=True)
            if run.returncode:raise RuntimeError(run.stderr+'\n'+run.stdout)
            record={k:v for k,v in task.items() if k not in ('repo','song')}
            record.update(json.loads(run.stdout.strip().splitlines()[-1]));record['song']=source.name
            with (out/'results.jsonl').open('a') as stream:stream.write(json.dumps(record)+'\n')
            assert record['applied_edits']==0
            if case['kind']=='live':
                assert record['scopes_at_end'] and (not case['enabled'] or record['batch_proposal_ready'])
            print(case['case'],case['enabled'],repetition,flush=True)
    (out/'task.json').unlink()
    assert source.read_bytes()==before
    (out/'input.json').write_text(json.dumps(dict(sha256=hashlib.sha256(before).hexdigest(),source_unchanged=True),indent=2)+'\n')


if __name__=='__main__':main()
