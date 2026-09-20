"""Print deterministic trace hashes for the repository path supplied as argv[1]."""
from pathlib import Path
import sys,json,hashlib
sys.path.insert(0,sys.argv[1])
from sidpulse.project.format import load
from sidpulse.playback.sequencer import Sequencer
class TraceSID:
    sample_rate=48000
    def __init__(self, clock):
        self.clock_hz=985248 if clock=='PAL' else 1022727
        self.registers=bytearray(25);self.frames=0;self.events=[]
    def write(self,r,v):self.registers[r]=v;self.events.append((self.frames,r,v))
    def clock(self,cycles):pass
    def render(self,frames):self.frames+=frames;return bytes(frames*2)
results=[]
for name in ('autumn-at-five-synthwave-mix_v9-pw-sweep.sidpulse','autumn-at-five-synthwave-pcm-drums.sidpulse','synthesized-reference-drums.sidpulse'):
    for clock in ('PAL','NTSC'):
        song=load(Path(sys.argv[1])/'examples'/name)[0];song.clock=clock
        sid=TraceSID(clock);seq=Sequencer(sid);seq.start(song)
        for count in (512,2048,1,431,18001,120007,8192):seq.render(count)
        blob=json.dumps((seq.state.__dict__,sid.events),sort_keys=True).encode()
        results.append(dict(song=name,clock=clock,events=len(sid.events),sha256=hashlib.sha256(blob).hexdigest()))
print(json.dumps(results,indent=2))
