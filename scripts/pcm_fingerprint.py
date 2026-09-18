"""Fingerprint native PCM and ordered SID writes/cycle calls across source trees."""
import argparse
import hashlib
import json
from pathlib import Path
import sys


def main(argv=None):
    ap=argparse.ArgumentParser();ap.add_argument('--repo',required=True);ap.add_argument('--output',required=True)
    args=ap.parse_args(argv);sys.path.insert(0,str(Path(args.repo).resolve()))
    from sidpulse.sid.backend_residfp import ReSIDfpBackend,set_filter
    from sidpulse.project.format import load
    from sidpulse.playback.sequencer import Sequencer
    from sidpulse.audio.output import OutputConditioner
    class RecordedSID(ReSIDfpBackend):
        def __init__(self,*a,**kw):self.events=[];super().__init__(*a,**kw)
        def write(self,r,v):self.events.append(('w',r,v));super().write(r,v)
        def clock(self,c):self.events.append(('c',c));super().clock(c)
    results=[]
    for name in ('first-light','autumn-at-five'):
        for model in ('6581','8580'):
            for clock in ('PAL','NTSC'):
                song=load(Path(args.repo)/'examples'/f'{name}.sidpulse')[0]
                song.sid_model=model;song.clock=clock
                sid=RecordedSID(model,clock=clock);set_filter(sid,song.filter);sid.render(48000);sid.events=[]
                seq=Sequencer(sid);seq.start(song);conditioner=OutputConditioner();conditioner.target=1
                raw=hashlib.sha256();conditioned=hashlib.sha256()
                remaining=48000*12;i=0
                partitions=(1,17,1024,2048,3,256,8192,512)
                while remaining:
                    n=min(remaining,partitions[i%len(partitions)]);i+=1;remaining-=n
                    pcm=seq.render(n);raw.update(pcm);conditioned.update(conditioner.process(pcm))
                result=dict(song=name,model=model,clock=clock,frames=48000*12,
                            raw_sha256=raw.hexdigest(),conditioned_sha256=conditioned.hexdigest(),
                            events_sha256=hashlib.sha256(json.dumps(sid.events).encode()).hexdigest(),
                            events=len(sid.events),final_state=vars(seq.state))
                results.append(result);print(json.dumps(result),flush=True)
    Path(args.output).write_text(json.dumps(results,indent=2)+'\n')


if __name__=='__main__':main()
