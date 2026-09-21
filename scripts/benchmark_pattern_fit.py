"""Serial, matched F2 fit-on/off and F5 checks using the release GUI workload."""
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile

from benchmark_releases import gui, init


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path)
    parser.add_argument('--candidate', type=Path)
    parser.add_argument('--input', type=Path)
    parser.add_argument('--out', type=Path)
    parser.add_argument('--repetitions', type=int, default=5)
    parser.add_argument('--worker', type=Path)
    args = parser.parse_args()
    if args.worker:
        task = json.loads(args.worker.read_text())
        init(task['repo'], task['cpus'])
        with tempfile.TemporaryDirectory(prefix='sidpulse-fit-benchmark-') as config:
            os.environ['SIDPULSE_CONFIG_HOME'] = config
            if task['label'] == 'fit-off':
                from sidpulse.preferences import save_preferences
                save_preferences({'pattern_fit_three': False})
            result = gui(task)
            from sidpulse import __version__
        print(json.dumps({'version': __version__, **result}))
        return
    if not all((args.baseline, args.candidate, args.input, args.out)):
        parser.error('--baseline, --candidate, --input and --out are required')
    args.out.mkdir(parents=True, exist_ok=False)
    source = args.input.read_bytes()
    environment = {
        'python': platform.python_version(), 'platform': platform.platform(),
        'packages': {name: importlib.metadata.version(name)
                     for name in ('pygame-ce', 'pyresidfp', 'numpy')},
        'cpus': [min(os.sched_getaffinity(0))],
        'drivers': 'SDL dummy audio/video; simulated playback for drawing cost',
        'input': args.input.name, 'input_sha256': hashlib.sha256(source).hexdigest(),
        'repetitions': args.repetitions, 'iterations': 200,
    }
    (args.out / 'environment.json').write_text(json.dumps(environment, indent=2) + '\n')
    variants = [('baseline', args.baseline), ('fit-on', args.candidate), ('fit-off', args.candidate)]
    cases = [('pattern', (960,1080)), ('pattern', (800,600)),
             ('pattern', (960,540)), ('pattern', (1280,900)), ('info', (960,1080))]
    with tempfile.TemporaryDirectory(prefix='sidpulse-fit-task-') as temporary:
        taskfile = Path(temporary) / 'task.json'
        with (args.out / 'results.jsonl').open('x') as output:
            for repeat in range(args.repetitions):
                order = variants if repeat % 2 == 0 else variants[::-1]
                for page, size in cases:
                    for label, repo in order:
                        task = dict(repo=str(repo.resolve()), song=str(args.input.resolve()),
                                    cpus=environment['cpus'], iterations=200, page=page,
                                    size=size, scopes=True, label=label, repetition=repeat)
                        taskfile.write_text(json.dumps(task))
                        run = subprocess.run([sys.executable, str(Path(__file__).resolve()),
                                              '--worker', str(taskfile)], capture_output=True, text=True)
                        if run.returncode:
                            raise RuntimeError(run.stdout + run.stderr)
                        result = json.loads(run.stdout.strip().splitlines()[-1])
                        record = {k: v for k, v in task.items() if k not in ('repo', 'song')}
                        record.update(result)
                        output.write(json.dumps(record) + '\n'); output.flush()
                        print(f"{page} {size} {label} #{repeat}: {result['cpu_ms_per_frame']:.3f} ms/frame", flush=True)
    if args.input.read_bytes() != source:
        raise RuntimeError('Benchmark input changed')


if __name__ == '__main__':
    main()
