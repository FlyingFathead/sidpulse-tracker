"""Linux SDL-dummy order-navigation stress; print four JSON records to stdout."""
from pathlib import Path
import os,sys,json,time,statistics,multiprocessing as mp
repo=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(repo/'scripts'));sys.path.insert(0,str(repo))
from benchmark_runtime import cpu
from benchmark_releases import init

def trial(kind,frames):
    import pygame as pg
    from sidpulse.app import App
    from sidpulse.project.format import load
    source=repo/'examples'/('autumn-at-five-synthwave-pcm-drums.sidpulse' if kind=='pcm' else 'autumn-at-five-synthwave-mix_v9-pw-sweep.sidpulse')
    app=App(load(source)[0],size=(1280,900),audio_buffer=frames)
    try:
        app.change_page('info');app.start_services();app.run(frames=65)
        assert app.audio.ready,app.audio.error
        app.audio.send('play',app.editor.song,'song',0,0,None);app.run(frames=60)
        app.audio.send('reset_stats');app.run(frames=8)
        worker=next(p for p in mp.active_children() if p.name=='sidpulse-audio');pid=worker.pid
        original=app.sync_audio;last=[0.];events=[];clock=[app.audio.playback.frames]
        def tick():
            original();now=time.monotonic();state=app.audio.playback
            assert state.frames>=clock[0];clock[0]=state.frames
            if now-last[0]>.2:
                direction=1 if len(events)%4<2 else -1
                app.handle(pg.event.Event(pg.KEYDOWN,key=pg.K_KP_PLUS if direction==1 else pg.K_KP_MINUS,mod=0,unicode='',scancode=0))
                events.append((state.frames,state.order,direction));last[0]=now
        app.sync_audio=tick
        t=time.monotonic();u=cpu(os.getpid());a=cpu(pid);start_frames=app.audio.playback.frames
        app.run(frames=480);elapsed=time.monotonic()-t
        assert worker.is_alive() and not app.audio.error
        result=dict(input=kind,frames=frames,elapsed=elapsed,commands=len(events),ui_cpu=100*(cpu(os.getpid())-u)/elapsed,audio_cpu=100*(cpu(pid)-a)/elapsed,gaps=app.audio.underruns,missing_frames=app.audio.missing_frames,late_callbacks=app.audio.late_callbacks,over_budget=app.audio.over_budget,clock_continuous=True,worker_preserved=True,scopes=app.scopes_visible,audio_frames=app.audio.playback.frames-start_frames)
        return result
    finally:app.close()
if __name__=='__main__':
    init(repo,sorted(os.sched_getaffinity(0))[:2])
    import tempfile
    with tempfile.TemporaryDirectory(prefix='sidpulse-skip-') as config:
        os.environ['SIDPULSE_CONFIG_HOME']=config
        for kind in ('sid','pcm'):
            for frames in (2048,512):print(json.dumps(trial(kind,frames)),flush=True)
