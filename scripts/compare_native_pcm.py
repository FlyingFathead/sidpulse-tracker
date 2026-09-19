"""Compare native PCM from identical initialized emulator state, serially."""
import sys,json,hashlib,multiprocessing as mp
import argparse
from pathlib import Path

def render(repo,label,out,stress):
    sys.path.insert(0,str(repo))
    from sidpulse.sid.backend_residfp import ReSIDfpBackend
    from sidpulse.project.format import load
    from sidpulse.playback.sequencer import Sequencer
    from sidpulse.audio.output import OutputConditioner
    class TraceSID(ReSIDfpBackend):
        def __init__(self,*a,**k):self.events=[];super().__init__(*a,**k)
        def write(self,r,v):self.events.append(('w',r,v));super().write(r,v)
        def clock(self,c):self.events.append(('c',c));super().clock(c)
    rows=[]
    paths=sorted((repo/'examples').glob('*.sidpulse'))+[stress]
    for path in paths:
        source=path.read_bytes();song,_=load(path)
        sid=TraceSID(song.sid_model,clock=song.clock,voice_scopes=False);sid.render(48000);sid.events.clear()
        seq=Sequencer(sid);seq.start(song);conditioner=OutputConditioner();conditioner.target=1
        seconds=200 if path==stress else 12;remaining=seconds*48000
        raw=hashlib.sha256();conditioned=hashlib.sha256();index=0
        while remaining:
            frames=min(remaining,(1,17,1024,2048,3,256,8192,512)[index%8]);index+=1;remaining-=frames
            pcm=seq.render(frames);raw.update(pcm);conditioned.update(conditioner.process(pcm))
        rows.append(dict(song=path.name,source_sha256=hashlib.sha256(source).hexdigest(),seconds=seconds,
                         raw_sha256=raw.hexdigest(),conditioned_sha256=conditioned.hexdigest(),
                         events_sha256=hashlib.sha256(json.dumps(sid.events).encode()).hexdigest(),final_state=vars(seq.state)))
        assert path.read_bytes()==source
    (out/(label+'.json')).write_text(json.dumps(rows,indent=2)+'\n')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('baseline','candidate','input','out'):
        parser.add_argument('--'+name,required=True,type=Path)
    args=parser.parse_args();out=args.out;out.mkdir(parents=True,exist_ok=True)
    if any((out/(label+'.json')).exists() for label in ('baseline','candidate')):
        parser.error('Use a fresh output directory')
    # Test isolation only: inherit initialized native tables so both versions
    # start identically. The application audio/export workers still use spawn.
    from pyresidfp._pyresidfp import SID,ChipModel,SamplingMethod
    warm=SID(ChipModel.MOS8580,SamplingMethod.RESAMPLE,985248.,48000.);warm.clock(985248)
    ctx=mp.get_context('fork')
    for label in ('baseline','candidate'):
        child=ctx.Process(target=render,args=(getattr(args,label).resolve(),label,out.resolve(),args.input.resolve()))
        child.start();child.join(90)
        if child.is_alive():child.terminate();child.join();raise RuntimeError('Native PCM timeout')
        if child.exitcode:raise RuntimeError('Native PCM child failed')
    a=json.loads((out/'baseline.json').read_text());b=json.loads((out/'candidate.json').read_text())
    assert a==b,'Native PCM differs'
    print('Exact native PCM, conditioned PCM, SID-write/cycle and state match:',len(a),'songs')
