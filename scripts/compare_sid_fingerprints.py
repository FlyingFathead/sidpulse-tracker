"""Compare eight SID audio/register fixtures from identical native filter tables.

Linux validation helper. Native reSIDfp analog tables are initialized once,
then inherited by serial forked workers. Application workers still use spawn.
"""
import argparse
import json
import multiprocessing as mp
from pathlib import Path

from pcm_fingerprint import main as fingerprint


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('baseline','candidate','out'):
        parser.add_argument('--'+name,required=True,type=Path)
    args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=True)
    from pyresidfp._pyresidfp import SID,ChipModel,SamplingMethod
    for model in (ChipModel.MOS6581,ChipModel.MOS8580):
        warm=SID(model,SamplingMethod.RESAMPLE,985248.,48000.)
        warm.clock(985248)
    context=mp.get_context('fork')
    for label in ('baseline','candidate'):
        child=context.Process(target=fingerprint,args=(['--repo',str(getattr(args,label).resolve()),
                              '--output',str(args.out/(label+'-fingerprints.json'))],))
        child.start();child.join(90)
        if child.is_alive():child.terminate();child.join();raise RuntimeError('Fingerprint timeout')
        if child.exitcode:raise RuntimeError('Fingerprint worker failed')
    before=json.loads((args.out/'baseline-fingerprints.json').read_text())
    after=json.loads((args.out/'candidate-fingerprints.json').read_text())
    assert before==after,'SID audio/register/state fingerprint changed'
    print('Exact raw PCM, conditioned PCM, register writes, clock calls and state match in all 8 fixtures.')


if __name__=='__main__':main()
