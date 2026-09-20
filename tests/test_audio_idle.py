"""Idle scheduling must preserve audition tails, transport and responsive UI."""
import math
import time
from array import array
from threading import Thread
import pytest
from sidpulse.audio.engine import AudioEngine
from sidpulse.sid.backend_residfp import ReSIDfpBackend
from sidpulse.song.model import Song, Instrument


def wait(predicate, timeout=5):
    until = time.monotonic()+timeout
    while not predicate():
        assert time.monotonic()<until
        time.sleep(.005)


def test_meter_matches_scalar_reference_without_modifying_pcm():
    import numpy as np
    rng=np.random.default_rng(41)
    engine=AudioEngine(Song(),enabled=False)
    for frames in (1,17,256,512,2048,8192):
        pcm=rng.integers(-32768,32768,frames,dtype=np.int16).tobytes()
        samples=array('h',pcm);mean=sum(samples)/len(samples)
        centered=[(v-mean)/32768 for v in samples]
        engine.measure(pcm)
        assert engine.peak == min(1.,max(abs(v) for v in centered))
        assert engine.rms == pytest.approx(min(1.,math.sqrt(sum(v*v for v in centered)/frames)),abs=1e-14)
        assert engine.waveform == tuple(centered[::max(1,frames//64)])
        assert pcm==samples.tobytes()


@pytest.mark.parametrize('model', ['6581', '8580'])
def test_idle_worker_stops_emulation_wakes_and_preserves_release(monkeypatch, model):
    calls=[]
    original=ReSIDfpBackend.render
    def render(self,frames):
        calls.append(frames)
        return original(self,frames)
    monkeypatch.setattr(ReSIDfpBackend,'render',render)
    engine=AudioEngine(Song(sid_model=model),enabled=False,buffer_frames=512)
    engine.thread=Thread(target=engine._run,daemon=True);engine.thread.start()
    try:
        wait(lambda:engine.ready and engine.idle)
        count=len(calls);time.sleep(.08);assert len(calls)==count
        engine.send('on','key',48,Instrument(attack=0,decay=0,sustain=15,release=8))
        wait(lambda:engine.peak>.02 and not engine.idle)
        engine.send('off','key')
        time.sleep(.05)
        count=len(calls);time.sleep(.08)
        assert len(calls)>count and not engine.idle  # release tail still renders
        engine.send('panic');wait(lambda:engine.idle and engine.peak==0)
        count=len(calls);time.sleep(.08);assert len(calls)==count
        engine.send('on','again',55,Instrument(release=0))
        wait(lambda:engine.peak>.01 and not engine.idle)
        engine.send('off','again')
        wait(lambda:engine.idle)
        count=len(calls);time.sleep(.08);assert len(calls)==count
        # Result-window previews have no keyboard key-up. A completed gate
        # program and a completed PCM one-shot must still become idle.
        engine.send('on','one-shot',48,Instrument(attack=0,sustain=15,release=0,gate_ticks=2))
        wait(lambda:not engine.idle and engine.peak>.01)
        wait(lambda:engine.idle)
        from sidpulse.audio.media import make_sample
        import numpy as np
        t=np.arange(4000)/8000
        values=np.where(t<.3,0,np.sin(t*2*np.pi*220)*20000).astype('<i2')
        engine.send('sample_on','sample',48,make_sample('delayed hit',values.tobytes(),8000))
        wait(lambda:not engine.idle)
        time.sleep(.15);assert not engine.idle  # preserve quiet lead-in
        wait(lambda:engine.peak>.1)
        wait(lambda:engine.idle)
        count=len(calls);time.sleep(.08);assert len(calls)==count
        engine.send('play',Song(),'song',0,0,None)
        wait(lambda:engine.playback.status=='playing' and engine.playback.frames>0)
        engine.send('pause');wait(lambda:engine.playback.status=='paused' and engine.idle)
        frames=engine.playback.frames;count=len(calls);time.sleep(.08)
        assert engine.playback.frames==frames and len(calls)==count
        engine.send('pause');wait(lambda:engine.playback.frames>frames and not engine.idle)
        assert engine.error is None
    finally:engine.close()


def test_idle_ui_skips_redundant_draws_but_handles_events_immediately(monkeypatch):
    import pygame as pg
    from sidpulse.app import App
    app=App(audio=False,size=(640,480));draws=[];ticks=[0];loops=[0]
    render=app.renderer.render
    def draw(host):draws.append((loops[0],host.page));render(host)
    class Clock:
        def tick(self,fps):ticks[0]+=17;loops[0]+=1
    def events():
        if loops[0]==10:return [pg.event.Event(pg.KEYDOWN,key=pg.K_F4,mod=0,unicode='')]
        return []
    monkeypatch.setattr(pg.time,'Clock',Clock)
    monkeypatch.setattr(pg.time,'get_ticks',lambda:ticks[0])
    monkeypatch.setattr(pg.event,'get',events)
    monkeypatch.setattr(app.renderer,'render',draw)
    try:
        app.run(frames=30)
        assert len(draws)<8 and (10,'instrument') in draws
        draws.clear();loops[0]=0;app.audio.idle=False
        app.run(frames=30);assert len(draws)==30
    finally:app.close()
