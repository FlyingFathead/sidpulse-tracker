"""Serial matched audio/UI/live regression for an update to a PCM-capable release.

Run alone. Both releases use the same SID and PCM songs, buffers and scopes.
The import control defaults on; a separate F3 trial measures its off state.
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
    parser.add_argument('--ui-iterations',type=int,default=300)
    args=parser.parse_args()
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=True)
    if (out/'results.jsonl').exists():raise SystemExit('Choose a fresh output directory')
    songs={name:path.resolve() for name,path in (('sid',args.song),('pcm',args.pcm))}
    originals={name:path.read_bytes() for name,path in songs.items()}
    cpus=sorted(os.sched_getaffinity(0))[:2]
    environment=dict(python=platform.python_version(),platform=platform.platform(),cpus=cpus,
        dependencies={n:importlib.metadata.version(n) for n in ('numpy','pygame-ce','pyresidfp')},
        song_sha256={n:hashlib.sha256(data).hexdigest() for n,data in originals.items()},
        drivers='SDL dummy audio/video',scopes='on',timing='serial, alternating version order',
        limitation='Checks CPU/scheduling, not a physical audio device; brief trials cannot guarantee no dropouts.')
    (out/'environment.json').write_text(json.dumps(environment,indent=2)+'\n')
    benchmark=Path(__file__).with_name('benchmark_releases.py')
    variants=[(version,repo,name) for name in songs for version,repo in
              (('baseline',args.baseline),('candidate',args.candidate))]
    def launch(variant,case,repetition):
        version,repo,name=variant
        task=dict(repo=str(repo.resolve()),song=str(songs[name]),cpus=cpus if case['kind']=='live' else cpus[:1],
                  scopes=True,label=version+'-'+name,repetition=repetition,**case)
        temporary=out/'task.json';temporary.write_text(json.dumps(task))
        run=subprocess.run([sys.executable,str(benchmark),'--worker',str(temporary)],capture_output=True,text=True)
        if run.returncode:raise RuntimeError(run.stderr+'\n'+run.stdout)
        result=json.loads(run.stdout.strip().splitlines()[-1])
        record={k:v for k,v in task.items() if k not in ('repo','song')}
        record['song']=songs[name].name;record.update(result)
        with (out/'results.jsonl').open('a') as stream:stream.write(json.dumps(record)+'\n')
        value=result.get('cpu_ms_per_block',result.get('cpu_ms_per_frame',result.get('audio_process_core_percent')))
        print(f'{case["case"]} {record["label"]} rep {repetition}: {value:.4f}',flush=True)
    for repetition in range(args.repetitions):
        order=variants if repetition%2==0 else variants[::-1]
        for frames in (2048,512):
            for variant in order:
                launch(variant,dict(kind='audio',case=f'audio-{frames}',frames=frames,seconds=20),repetition)
        for size in ((1280,900),(960,1080)):
            for page in ('pattern','info'):
                for variant in order:
                    if variant[2]=='sid':
                        launch(variant,dict(kind='gui',case=f'{page}-{size[0]}x{size[1]}',size=size,page=page,iterations=args.ui_iterations),repetition)
            for page in ('samples','instrument'):
                for variant in order:
                    if variant[2]=='pcm':
                        launch(variant,dict(kind='gui',case=f'pcm-{page}-{size[0]}x{size[1]}',size=size,page=page,
                                            instrument_number=3,auto_squeeze=True,iterations=args.ui_iterations),repetition)
            launch(variants[-1],dict(kind='gui',case=f'pcm-samples-import-off-{size[0]}x{size[1]}',size=size,
                                   page='samples',auto_squeeze=False,iterations=args.ui_iterations),repetition)
            for before,after in ((False,False),(True,True)):
                launch(variants[-1],dict(kind='gui',case=f'pcm-samples-normalize-{int(before)}-{int(after)}-{size[0]}x{size[1]}',
                       size=size,page='samples',normalize_before=before,normalize_after=after,iterations=args.ui_iterations),repetition)
    for repetition in range(args.live_repetitions):
        for frames in (2048,512):
            for variant in (variants if repetition%2==0 else variants[::-1]):
                launch(variant,dict(kind='live',case=f'live-info-{frames}',frames=frames,seconds=12,
                                    size=(960,1080),page='info'),repetition)
        for variant in (variants[2:] if repetition%2==0 else variants[2:][::-1]):
            launch(variant,dict(kind='live',case='live-pcm-export-2048',frames=2048,seconds=12,
                               size=(960,1080),page='info',export_analysis=True),repetition)
        for enabled in ((False,True) if repetition%2==0 else (True,False)):
            launch(variants[-1],dict(kind='live',case=f'live-pcm-synthesis-{int(enabled)}',frames=2048,seconds=12,
                   size=(960,1080),page='info',sample_synthesis=enabled),repetition)
    (out/'task.json').unlink(missing_ok=True)
    assert all(path.read_bytes()==originals[name] for name,path in songs.items())
    print('Complete; input songs unchanged.',flush=True)


if __name__=='__main__':main()
