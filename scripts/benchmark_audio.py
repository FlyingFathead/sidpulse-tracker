#!/usr/bin/env python3
"""Read-only SIDpulse 0.2.21 performance study; see README.md for limitations."""
import argparse
import cProfile
import ctypes
import importlib.metadata
import json
import math
import multiprocessing as mp
import os
from pathlib import Path
import platform
import pstats
import statistics
import sys
import tempfile
import time


def summary(values):
    values = sorted(values)
    if not values:
        return {}
    return dict(n=len(values), mean=statistics.mean(values), median=statistics.median(values),
                p95=values[min(len(values)-1, math.ceil(.95*len(values))-1)],
                p99=values[min(len(values)-1, math.ceil(.99*len(values))-1)], maximum=max(values))


def setup(repo):
    sys.path.insert(0, str(Path(repo).resolve()))
    os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
    os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
    os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')


def offline(repo, seconds):
    from sidpulse.project.format import load
    from sidpulse.sid.backend_residfp import ReSIDfpBackend
    from sidpulse.playback.sequencer import Sequencer
    from sidpulse.audio.engine import AudioEngine
    from sidpulse.audio.output import OutputConditioner
    results = []
    for name in ('first-light', 'autumn-at-five'):
        song = load(Path(repo)/'examples'/f'{name}.sidpulse')[0]
        for frames in (512, 2048):
            for scopes in (False, True):
                sid = ReSIDfpBackend(song.sid_model, clock=song.clock, voice_scopes=scopes)
                sid.render(48000)
                seq = Sequencer(sid); seq.start(song)
                conditioner = OutputConditioner(); conditioner.target = 1.
                meter = AudioEngine(song, enabled=False)
                stages = {k: [] for k in ('render', 'conditioner', 'meter_and_scope_snapshot', 'total')}
                cpu = time.process_time()
                blocks = math.ceil(seconds*48000/frames)
                for _ in range(blocks):
                    t0 = time.perf_counter(); pcm = seq.render(frames)
                    t1 = time.perf_counter(); pcm = conditioner.process(pcm)
                    t2 = time.perf_counter(); meter.measure(pcm)
                    if scopes: sid.voice_scopes.snapshot()
                    t3 = time.perf_counter()
                    for k, v in zip(stages, (t1-t0, t2-t1, t3-t2, t3-t0)):
                        stages[k].append(v*1000)
                cpu = time.process_time()-cpu
                budget = frames/48
                result = dict(song=name, model=song.sid_model, clock=song.clock, frames=frames,
                              scopes=scopes, audio_seconds=blocks*frames/48000, budget_ms=budget,
                              mean_budget_percent=statistics.mean(stages['total'])/budget*100,
                              over_budget=sum(t>budget for t in stages['total']),
                              cpu_seconds=cpu, stages_ms={k: summary(v) for k,v in stages.items()})
                results.append(result)
                print(json.dumps(result), flush=True)
    return results


def profile_render(repo, out):
    from sidpulse.project.format import load
    from sidpulse.sid.backend_residfp import ReSIDfpBackend
    from sidpulse.playback.sequencer import Sequencer
    from sidpulse.audio.engine import AudioEngine
    from sidpulse.audio.output import OutputConditioner
    song = load(Path(repo)/'examples/autumn-at-five.sidpulse')[0]
    sid = ReSIDfpBackend(song.sid_model, voice_scopes=True); sid.render(48000)
    seq = Sequencer(sid); seq.start(song)
    c = OutputConditioner(); c.target = 1
    meter = AudioEngine(song, False)
    p = cProfile.Profile(); p.enable()
    for _ in range(240):
        pcm = c.process(seq.render(2048)); meter.measure(pcm); sid.voice_scopes.snapshot()
    p.disable()
    with open(out, 'w') as f:
        pstats.Stats(p, stream=f).strip_dirs().sort_stats('cumulative').print_stats(45)


def instrument_stream():
    from sidpulse.audio.stream import PCMStream
    original = PCMStream.callback
    streams = []
    init = PCMStream.__init__
    def new_init(self, *args, **kwargs):
        self.perf_callbacks = []
        streams.append(self)
        init(self, *args, **kwargs)
    def callback(self, device, stream):
        self.perf_callbacks.append(time.perf_counter())
        original(self, device, stream)
    PCMStream.__init__ = new_init
    PCMStream.callback = callback
    return streams


def read_engine(engine, streams, start, duration):
    timestamps = [t for s in streams for t in s.perf_callbacks if t >= start]
    periods = [(b-a)*1000 for a,b in zip(timestamps,timestamps[1:])]
    budget = engine.buffer_frames/48
    timing = summary(periods) if periods else dict(n=getattr(engine,'callback_count',0),
                maximum=getattr(engine,'max_callback_interval',0)*1000)
    return dict(duration_seconds=duration, gaps=engine.underruns,
                missing_frames=sum(s.missing_frames for s in streams) if streams else getattr(engine,'missing_frames',0),
                callback_intervals_ms=timing,
                intervals_above_1_5_blocks=sum(t>1.5*budget for t in periods) if periods else getattr(engine,'late_callbacks',0),
                render_load=engine.render_load, peak_render_load=engine.peak_render_load,
                over_budget=engine.over_budget, late_wakes=engine.late_wakes, error=engine.error)


def wait_ready(engine):
    deadline=time.monotonic()+10
    while not engine.ready and not engine.error and time.monotonic()<deadline: time.sleep(.005)
    if not engine.ready: raise RuntimeError(engine.error or 'Audio startup timeout')


def audio_child(repo, conn, duration, frames):
    setup(repo)
    from sidpulse.project.format import load
    from sidpulse.audio.engine import AudioEngine
    streams=instrument_stream()
    song=load(Path(repo)/'examples/autumn-at-five.sidpulse')[0]
    engine=AudioEngine(song,buffer_frames=frames)
    try:
        wait_ready(engine); engine.send('play',song,'song',0,0,None); engine.send('scopes',True)
        time.sleep(.6); engine.send('reset_stats'); time.sleep(.1)
        start=time.perf_counter(); conn.send('ready')
        time.sleep(duration)
        result=read_engine(engine, streams,start,duration)
        engine.close(); conn.send(result)
    finally:
        engine.close(); conn.close()


def stress_loop(duration, workload):
    """Synthetic workloads distinguish bytecode contention from unbroken GIL holds."""
    start=time.perf_counter(); n=0; next_stall=start+.25
    # Linux-only reproducible stand-in for a GIL-holding native call.
    usleep=None
    if workload == 'gil_hold':
        if sys.platform == 'win32':
            held_sleep=ctypes.PyDLL('kernel32').Sleep
            held_sleep.argtypes=[ctypes.c_uint32];held_sleep.restype=None
            usleep=lambda microseconds:held_sleep(microseconds//1000)
        else:
            usleep=ctypes.PyDLL(None).usleep
            usleep.argtypes=[ctypes.c_uint]; usleep.restype=ctypes.c_int
    while time.perf_counter()-start < duration:
        if workload == 'cpu':
            for i in range(10000): n=(n+i)%1000003
        elif workload == 'gil_hold' and time.perf_counter() >= next_stall:
            usleep(100000); next_stall=time.perf_counter()+.25
        else:
            time.sleep(.001)


def realtime(repo, duration, kind, frames):
    from sidpulse.project.format import load
    from sidpulse.audio.engine import AudioEngine
    song=load(Path(repo)/'examples/autumn-at-five.sidpulse')[0]
    if kind == 'process_gil_hold':
        ctx=mp.get_context('spawn'); parent, child=ctx.Pipe()
        p=ctx.Process(target=audio_child,args=(repo,child,duration,frames))
        p.start(); child.close()
        try:
            if not parent.poll(15): raise RuntimeError('Child startup timeout')
            assert parent.recv() == 'ready'
            stress_loop(duration,'gil_hold')
            if not parent.poll(10): raise RuntimeError('Child result timeout')
            result=parent.recv()
            p.join(5)
        finally:
            if p.is_alive(): p.terminate(); p.join()
            parent.close()
        return dict(kind=kind,frames=frames,**result)
    streams=instrument_stream()
    app=None
    if kind.startswith('ui_'):
        from sidpulse.app import App
        import pygame as pg
        app=App(song,audio=True,audio_buffer=frames)
        engine=app.audio
        app.page='info' if kind=='ui_churn' else kind[3:]
    else:
        engine=AudioEngine(song,buffer_frames=frames)
    try:
        wait_ready(engine)
        engine.send('play',song,'song',0,0,None)
        engine.send('scopes',kind not in ('idle_no_scopes','ui_pattern'))
        if app: app.scopes_visible=app.page=='info'
        time.sleep(.6); engine.send('reset_stats'); time.sleep(.1)
        start=time.perf_counter()
        frame_times=[]
        if app:
            clock=pg.time.Clock()
            count=0
            while time.perf_counter()-start<duration:
                t=time.perf_counter()
                if kind=='ui_churn':
                    if count%25==0:app.page='pattern' if app.page=='info' else 'info'
                    if count%60==0:
                        w,h=(1280,900) if count%120==0 else (980,780)
                        app.handle(pg.event.Event(pg.VIDEORESIZE,w=w,h=h,size=(w,h)))
                    if count%30==0:app.editor.enter_note(48+count%24)
                for event in pg.event.get(): app.handle(event)
                app.sync_audio(); app.renderer.render(app); pg.display.flip()
                frame_times.append((time.perf_counter()-t)*1000)
                count+=1
                clock.tick(60)
        else:
            stress_loop(duration, 'gil_hold' if kind=='gil_hold' else 'cpu' if kind=='cpu' else 'idle')
        result=read_engine(engine,streams,start,duration)
        if app: result['ui_frame_work_ms']=summary(frame_times)
        return dict(kind=kind,frames=frames,**result)
    finally:
        engine.close()
        if app: pg.display.quit()


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--repo',required=True)
    ap.add_argument('--mode',choices=('offline','profile','realtime'),required=True)
    ap.add_argument('--seconds',type=float,default=30); ap.add_argument('--output',required=True)
    ap.add_argument('--kind',default='idle_no_scopes'); ap.add_argument('--frames',type=int,default=2048)
    ap.add_argument('--assert-clean',action='store_true',help='exit nonzero for missing PCM, late callbacks or audio errors')
    args=ap.parse_args(); setup(args.repo)
    with tempfile.TemporaryDirectory(prefix='sidpulse-perf-') as config:
        os.environ['SIDPULSE_CONFIG_HOME']=config
        if args.mode=='profile': profile_render(args.repo,args.output); return
        result=offline(args.repo,args.seconds) if args.mode=='offline' else realtime(args.repo,args.seconds,args.kind,args.frames)
        record=dict(environment=dict(python=sys.version,platform=platform.platform(),
                    cpu_count=os.cpu_count(),audio_driver=os.environ.get('SDL_AUDIODRIVER'),
                    pygame=importlib.metadata.version('pygame-ce'),pyresidfp=importlib.metadata.version('pyresidfp')),
                    results=result)
        Path(args.output).write_text(json.dumps(record,indent=2)+'\n')
        if args.mode!='offline':print(json.dumps(record),flush=True)
        if args.assert_clean:
            if args.mode != 'realtime':
                raise SystemExit('--assert-clean requires --mode realtime')
            if result['gaps'] or result['missing_frames'] or result['intervals_above_1_5_blocks'] or result['error']:
                raise SystemExit(1)


if __name__=='__main__': main()
