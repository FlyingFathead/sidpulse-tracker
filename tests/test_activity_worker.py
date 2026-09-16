"""Real worker/telemetry integration with explicitly fake SID and PCM I/O."""
from sidpulse.audio.engine import AudioEngine
from sidpulse.song.model import Song,Instrument
from sidpulse.sid.backend_residfp import CLOCKS


class FakeSID:
    def __init__(self,model,clock='PAL'):
        self.model=model;self.clock_name=clock;self.clock_hz=CLOCKS[clock]
        self.registers=bytearray(25);self.sample_rate=48000;self.voice_scopes=None
    def write(self,reg,val):self.registers[reg]=val
    def clock(self,cycles):pass
    def render(self,frames):return bytes(frames*2)
    def set_muted(self,mask):pass
    def set_model(self,model):self.model=model
    def set_clock(self,clock):self.clock_name=clock;self.clock_hz=CLOCKS[clock]
    def reset(self):self.registers[:]=bytes(25)
    def enable_scopes(self,enabled):pass


def test_worker_publishes_audition_slot_release_and_panic(monkeypatch):
    import sidpulse.audio.engine as module
    import sidpulse.audio.stream as stream
    engine=AudioEngine(Song(),enabled=False,buffer_frames=256)
    monkeypatch.setattr(module,'ReSIDfpBackend',FakeSID)
    snapshots=[]
    class Output:
        callback_error=None;gaps=0;expect_audio=False
        def __init__(self,frames):self.frames=frames
        def needs_block(self):return True
        def write(self,pcm):
            assert len(pcm)==512
            snapshots.append(engine.activity)
            if len(snapshots)==1:engine.commands.put(('off',('test',)))
            elif len(snapshots)==2:engine.commands.put(('panic',()))
            else:engine.stop_event.set()
        def stop(self):pass
        def close(self):pass
        def pause(self):pass
        def unpause(self):pass
    monkeypatch.setattr(stream,'PCMStream',Output)
    engine.commands.put(('on',('test',60,Instrument(),2,14)))
    engine._run()
    assert engine.error is None and not engine.ready
    assert snapshots[0].active==(14,) and snapshots[0].triggers==((14,1),)
    assert snapshots[1].active==() and snapshots[1].triggers==((14,1),)
    assert snapshots[2].enabled is False and snapshots[2].generation==1
    assert not engine.activity.enabled
