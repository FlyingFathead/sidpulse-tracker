"""Serial, matched v0.2.31 audio/UI/live regression and PCM feature measurements.

Uses benchmark_releases.py workers, including separate UI/audio process CPU,
late callbacks, gaps and missing frames. Run alone, without tests/profilers.
"""
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import subprocess
import sys


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('baseline','candidate','song','pcm','out'):
        parser.add_argument('--'+name,required=True,type=Path)
    parser.add_argument('--repetitions',type=int,default=5)
    parser.add_argument('--live-repetitions',type=int,default=3)
    args=parser.parse_args()
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=True)
    if (out/'results.jsonl').exists():raise SystemExit('Choose a fresh output directory')
    original=args.song.read_bytes();pcm_original=args.pcm.read_bytes()
    common=out/'original-demo.sidpulse';common.write_bytes(original)
    pcm=out/'pcm-demo.sidpulse';pcm.write_bytes(pcm_original)
    off=out/'pcm-overrides-off.sidpulse';document=json.loads(pcm_original)
    for inst in document['song']['instruments'].values():inst['sample_override']=False
    off.write_text(json.dumps(document)+'\n')
    cpus=sorted(os.sched_getaffinity(0))
    environment=dict(python=platform.python_version(),platform=platform.platform(),
                     dependencies={n:importlib.metadata.version(n) for n in ('numpy','pygame-ce','pyresidfp')},
                     cpus=cpus[:2],drivers='SDL dummy audio/video',
                     input_sha256=hashlib.sha256(original).hexdigest(),pcm_sha256=hashlib.sha256(pcm_original).hexdigest(),
                     scopes='enabled in every trial',timing='serial; version order alternated by repetition',
                     limitation='Dummy SDL tests scheduling and CPU, not physical sound hardware or audible device dropouts.')
    (out/'environment.json').write_text(json.dumps(environment,indent=2)+'\n')
    benchmark=Path(__file__).with_name('benchmark_releases.py').resolve()
    variants=[('baseline',args.baseline,common),('candidate',args.candidate,common),
              ('pcm-on',args.candidate,pcm),('pcm-off',args.candidate,off)]
    def launch(variant,case,repetition):
        label,repo,song=variant
        task=dict(repo=str(repo.resolve()),song=str(song),cpus=cpus[:2] if case['kind']=='live' else cpus[:1],
                  scopes=True,label=label,repetition=repetition,**case)
        temporary=out/'task.json';temporary.write_text(json.dumps(task))
        run=subprocess.run([sys.executable,str(benchmark),'--worker',str(temporary)],capture_output=True,text=True)
        if run.returncode:raise RuntimeError(run.stderr+'\n'+run.stdout)
        result=json.loads(run.stdout.strip().splitlines()[-1])
        record={k:v for k,v in task.items() if k not in ('repo','song')}
        record['song']=song.name;record.update(result)
        with (out/'results.jsonl').open('a') as stream:stream.write(json.dumps(record)+'\n')
        number=result.get('cpu_ms_per_block',result.get('cpu_ms_per_frame',result.get('audio_process_core_percent')))
        print(f'{case["kind"]} {case["case"]} {label} rep {repetition}: {number:.4f}',flush=True)
    for repetition in range(args.repetitions):
        order=variants if repetition%2==0 else variants[::-1]
        for frames in (2048,512):
            for variant in order:
                launch(variant,dict(kind='audio',case=f'audio-{frames}',frames=frames,seconds=24),repetition)
        for size in ((1280,900),(960,1080)):
            for page in ('pattern','instrument','info','samples'):
                for variant in (variants[:2] if repetition%2==0 else variants[:2][::-1]):
                    launch(variant,dict(kind='gui',case=f'{page}-{size[0]}x{size[1]}',size=size,page=page,iterations=300),repetition)
            launch(variants[2],dict(kind='gui',case=f'sample-waveform-{size[0]}x{size[1]}',size=size,page='samples',iterations=300),repetition)
    for repetition in range(args.live_repetitions):
        for frames in (2048,512):
            for variant in (variants if repetition%2==0 else variants[::-1]):
                launch(variant,dict(kind='live',case=f'live-info-{frames}',frames=frames,seconds=16,
                                    size=(960,1080),page='info'),repetition)
    (out/'task.json').unlink(missing_ok=True)
    assert args.song.read_bytes()==original and args.pcm.read_bytes()==pcm_original
    print('Complete; input songs unchanged.',flush=True)


if __name__=='__main__':main()
