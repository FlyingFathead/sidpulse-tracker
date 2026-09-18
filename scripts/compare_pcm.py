"""Linux analysis only: compare both trees from identical native emulator state.

The pinned emulator's analog dither state/tables can differ between fresh runs.
Warm its tables once, then fork two isolated numerical render jobs from exactly
the same memory state. No SDL, Python worker or audio-device threads are started
before forking. Production playback always uses spawn, never this test technique.
"""
import argparse
import json
import multiprocessing as mp
from pathlib import Path
import sys

from pcm_fingerprint import main as fingerprint


def run(repo, out):
    with open(str(out)+'.log','w') as log:
        sys.stdout=log
        fingerprint(['--repo',repo,'--output',str(out)])


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--baseline',required=True);ap.add_argument('--candidate',required=True)
    ap.add_argument('--output-dir',required=True);a=ap.parse_args();out=Path(a.output_dir)
    from pyresidfp._pyresidfp import SID,ChipModel,SamplingMethod
    # Both analog models initialize their singleton tables in the SID constructor.
    chip=SID(ChipModel.MOS8580,SamplingMethod.RESAMPLE,985248.,48000.)
    chip.clock(985248)
    ctx=mp.get_context('fork')
    for label,repo in [('baseline',a.baseline),('candidate',a.candidate)]:
        child=ctx.Process(target=run,args=(repo,out/f'{label}-pcm-common-state.json'))
        child.start();child.join(90)
        if child.is_alive():child.terminate();child.join();raise RuntimeError('PCM comparison timed out')
        if child.exitcode:raise RuntimeError(f'{label} render failed: {child.exitcode}')
    b=json.loads((out/'baseline-pcm-common-state.json').read_text())
    c=json.loads((out/'candidate-pcm-common-state.json').read_text())
    print('EXACT MATCH:',b==c,'cases:',len(b))
    for x,y in zip(b,c):
        print(x['song'],x['model'],x['clock'],{k:x[k]==y[k] for k in ('raw_sha256','conditioned_sha256','events_sha256','final_state')})
    if b!=c:raise SystemExit(1)


if __name__=='__main__':main()
