"""Serial, matched runtime regression checks, including the real stopped UI loop.

Uses SDL dummy devices and Linux process counters. Never mutates source songs.
Run without other heavy jobs; inspect raw counters as well as median CPU.
"""
import argparse
import hashlib
import importlib.metadata
import json
import multiprocessing as mp
import os
from pathlib import Path
import platform
import statistics
import resource
import subprocess
import sys
import tempfile
import time


def cpu(pid):
    fields=Path(f'/proc/{pid}/stat').read_text().split(') ',1)[1].split()
    return (int(fields[11])+int(fields[12]))/os.sysconf('SC_CLK_TCK')


def live(task):
    import pygame as pg
    from sidpulse.app import App
    from sidpulse.project.format import load
    from sidpulse.audio.media import import_sample
    from sidpulse.song.model import Instrument
    app=App(load(task['song'])[0],size=tuple(task['size']),audio_buffer=task['frames'])
    case=task['case'];draw_times=[];events=[]
    original=app.renderer.render
    def draw(host):
        start=time.perf_counter();original(host);draw_times.append((time.perf_counter()-start)*1000)
    app.renderer.render=draw
    try:
        app.change_page(task['page']);app.start_services();app.run(frames=65)
        if not app.audio.ready:raise RuntimeError(app.audio.error or 'Audio not ready')
        if case not in ('startup','audition','sample'):
            app.audio.send('play',app.editor.song,'song',0,0,None)
            app.run(frames=40)
        if case=='record':
            app.automation_display=1  # modal over Info, keeping all scopes visible
            app.open_automation_recording();app.set_recording_channel(1);app.toggle_pulse_recording()
            sync=app.sync_audio;phase=[0]
            def record_changes():
                sync();phase[0]+=1
                hits=[(r,v) for r,a,v in app.renderer.hits if a=='automation_slider']
                if hits:
                    rect,data=hits[0];fraction=.2+.6*(1-abs((phase[0]%120)/60-1))
                    pos=(int(rect.left+rect.width*fraction),rect.centery)
                    if app.pulse_take is None:app.begin_pulse_drag(data,pos)
                    elif not app.pulse_take['pending']:app.update_pulse_drag(pos)
            app.sync_audio=record_changes
        if case=='stopped':app.audio.send('panic')
        if case=='paused':app.audio.send('pause')
        if case=='audition':app.audio.send('on','bench',48,Instrument(attack=0,sustain=15,release=5))
        if case=='sample':
            source=import_sample(Path(task['repo'])/'examples/samples/sidpulse_sample_synthwave_snare.wav')
            sync=app.sync_audio;last=[0.]
            def repeat_sample():
                sync();now=time.monotonic()
                if now-last[0]>.65:
                    app.audio.send('sample_on','bench',48,source);last[0]=now
            app.sync_audio=repeat_sample
        if case=='fit':
            sync=app.sync_audio
            def keep_scopes():
                app.page='info';sync()
            app.sync_audio=keep_scopes
        app.run(frames=30);app.audio.send('reset_stats');app.run(frames=8)
        child=next(p for p in mp.active_children() if p.name=='sidpulse-audio')
        draw_times.clear();u0=cpu(os.getpid());a0=cpu(child.pid)
        usage=resource.getrusage(resource.RUSAGE_CHILDREN);jobs0=usage.ru_utime+usage.ru_stime
        start=time.monotonic()
        if case=='export':
            from sidpulse.ui.export_squeezer import open_dialog
            open_dialog(app,'prg')
        if case=='fit':
            from sidpulse.ui.sample_synthesis import begin
            app.sample_index=1;begin(app)
        if case=='edit':
            sync=app.sync_audio;last=[0.]
            def edit_during_playback():
                sync();now=time.monotonic()
                if now-last[0]>.2:
                    pg.event.post(pg.event.Event(pg.KEYDOWN,key=pg.K_RIGHT,mod=0,unicode=''))
                    events.append(now);last[0]=now
            app.sync_audio=edit_during_playback
        app.run(frames=round(task['seconds']*60));elapsed=time.monotonic()-start
        a=app.audio
        result=dict(elapsed=elapsed,ui_cpu=100*(cpu(os.getpid())-u0)/elapsed,
                    audio_cpu=100*(cpu(child.pid)-a0)/elapsed,draw_fps=len(draw_times)/elapsed,
                    draw_median_ms=statistics.median(draw_times),draw_max_ms=max(draw_times),
                    gaps=a.underruns,missing_frames=a.missing_frames,late_callbacks=a.late_callbacks,
                    over_budget=a.over_budget,status=a.playback.status,error=a.error,
                    scopes=app.scopes_visible,edits=len(events),idle=getattr(a,'idle',None))
        if case in ('fit','export'):
            result['dialog_kind']=app.dialog.get('kind') if app.dialog else None
            result['job_error']=app.dialog.get('error') if app.dialog else None
            result['job_busy']=bool(app.media_jobs or app.export_jobs)
            workers=[p for p in mp.active_children() if p.pid!=child.pid]
            # Completed worker CPU is available in the parent's waited-child
            # counters; report it separately from real-time UI/audio cost.
            usage=resource.getrusage(resource.RUSAGE_CHILDREN)
            result['background_cpu_seconds']=usage.ru_utime+usage.ru_stime-jobs0+sum(cpu(p.pid) for p in workers if p.is_alive())
        if result['error']:raise RuntimeError(result['error'])
        return result
    finally:app.close()


def worker(task):
    import benchmark_releases as shared
    shared.init(task['repo'],task['cpus'])
    with tempfile.TemporaryDirectory(prefix='sidpulse-runtime-') as config:
        os.environ['SIDPULSE_CONFIG_HOME']=config
        if task['kind']=='live':return live(task)
        return {'audio':shared.audio,'gui':shared.gui}[task['kind']](task)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--worker',type=Path)
    for name in ('baseline','candidate','out'):parser.add_argument('--'+name,type=Path)
    parser.add_argument('--repetitions',type=int,default=3)
    parser.add_argument('--cases',nargs='+',help='Repeat only named cases, e.g. export or fit.')
    args=parser.parse_args()
    if args.worker:
        if (args.worker.parent/'STOP').exists():raise SystemExit('Benchmark stopped between trials.')
        print(json.dumps(worker(json.loads(args.worker.read_text()))));return
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=True)
    if (out/'runtime.jsonl').exists():raise SystemExit('Choose a fresh output directory.')
    baseline=args.baseline.resolve();candidate=args.candidate.resolve()
    songs={'sid':baseline/'examples/autumn-at-five-synthwave-mix_v9-pw-sweep.sidpulse',
           'pcm':baseline/'examples/autumn-at-five-synthwave-pcm-drums.sidpulse'}
    hashes={k:hashlib.sha256(v.read_bytes()).hexdigest() for k,v in songs.items()}
    cpus=sorted(os.sched_getaffinity(0))[:2]
    cases=[]
    for kind in ('sid','pcm'):
        for frames in (2048,512):
            cases.append(dict(kind='audio',case='offline',input=kind,frames=frames,seconds=12))
            cases.append(dict(kind='live',case='playback',input=kind,frames=frames,page='info',seconds=5,size=(1280,900)))
    for case,page in [('startup','pattern'),('stopped','info'),('paused','info'),('audition','info'),('sample','samples'),('edit','pattern'),('record','info')]:
        cases.append(dict(kind='live',case=case,input='sid',frames=2048,page=page,seconds=5,size=(1280,900)))
    for case,kind in [('export','sid'),('export','pcm'),('fit','pcm')]:
        for frames in (2048,512):
            cases.append(dict(kind='live',case=case,input=kind,frames=frames,page='info',seconds=18 if case=='fit' else 5,size=(1280,900)))
    for size in ((640,480),(1280,900)):
        for page in ('pattern','info','samples','instrument'):
            cases.append(dict(kind='gui',case='draw',input='pcm',size=size,page=page,iterations=200))
    if args.cases:
        unknown=set(args.cases)-{case['case'] for case in cases}
        if unknown:parser.error('Unknown cases: '+', '.join(sorted(unknown)))
        cases=[case for case in cases if case['case'] in args.cases]
    env=dict(python=platform.python_version(),platform=platform.system()+' '+platform.machine(),
             versions={n:importlib.metadata.version(n) for n in ('numpy','pygame-ce','pyresidfp')},
             cpus=cpus,drivers='SDL dummy',input_sha256=hashes,repetitions=args.repetitions)
    (out/'environment.json').write_text(json.dumps(env,indent=2)+'\n')
    for repetition in range(args.repetitions):
        for case in cases:
            versions=[('baseline',baseline),('candidate',candidate)]
            if repetition%2:versions.reverse()
            for label,repo in versions:
                task=dict(repo=str(repo),song=str(songs[case['input']]),cpus=cpus if case['kind']=='live' else cpus[:1],scopes=True,**case)
                path=out/'task.json';path.write_text(json.dumps(task))
                run=subprocess.run([sys.executable,str(Path(__file__).resolve()),'--worker',str(path)],capture_output=True,text=True)
                if run.returncode:raise RuntimeError(run.stdout+'\n'+run.stderr)
                record=dict(repetition=repetition,label=label,**case,result=json.loads(run.stdout.strip().splitlines()[-1]))
                with (out/'runtime.jsonl').open('a') as f:f.write(json.dumps(record)+'\n')
                print(repetition,label,case['kind'],case['case'],case['input'],case.get('frames',case.get('size')),flush=True)
    (out/'task.json').unlink()
    assert hashes=={k:hashlib.sha256(v.read_bytes()).hexdigest() for k,v in songs.items()}


if __name__=='__main__':main()
