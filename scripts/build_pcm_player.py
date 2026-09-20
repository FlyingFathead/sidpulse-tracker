#!/usr/bin/env python3
"""Rebuild the experimental C64 PCM player; exports need no assembler."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

from build_squeeze_players import read_labels


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--assembler', default='64tass')
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    for decoder, suffix in ((1, ''), (201, '-phrases'), (202, '-indexed')):
        for method in (1, 2):
            build(root, args, decoder, suffix, method)


def build(root, args, decoder, suffix, method):
    source = 'pcm_volume_player.asm' if method == 1 else 'pcm_player.asm'
    stem = 'pcm-volume-player' if method == 1 else 'pcm-player'
    with tempfile.TemporaryDirectory() as temporary:
        binary, labels = Path(temporary)/'pcm.bin', Path(temporary)/'pcm.labels'
        subprocess.run([args.assembler, '--nostart', '--normal-labels', '-D', f'DECODER={decoder}', '-l', str(labels),
                        '-o', str(binary), str(root/'sidpulse/export'/source)], check=True)
        data = binary.read_bytes()
        info = dict(load=0x0801, size=len(data), sha256=hashlib.sha256(data).hexdigest(),
                    labels=read_labels(labels))
        assert len(data) == 0x1800-0x0801
        for name, content in [(stem+suffix+'.bin', data),
                              (stem+suffix+'.json', (json.dumps(info, indent=2, sort_keys=True)+'\n').encode())]:
            path = root/'sidpulse/assets'/name
            if args.check:
                if path.read_bytes() != content:
                    raise SystemExit(name+' differs from source; rebuild the PCM player')
            else:
                path.write_bytes(content)


if __name__ == '__main__':
    main()
