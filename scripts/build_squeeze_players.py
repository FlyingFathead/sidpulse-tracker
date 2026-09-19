#!/usr/bin/env python3
"""Rebuild all compact players and linking metadata with installed 64tass.

Export users need no assembler. --check never modifies bundled assets. Code,
link addresses, patch offsets, workspace sizes and hashes are checked together.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile


def read_labels(path):
    labels = {}
    for line in path.read_text(encoding='utf-8').splitlines():
        match = re.match(r'^\s*([A-Za-z_][\w]*)\s*=\s*(\$[0-9a-fA-F]+|\d+)\s*(?:;.*)?$', line)
        if match:
            key, value = match.groups()
            labels[key] = int(value[1:], 16) if value.startswith('$') else int(value)
    return labels


def player_metadata(name, binary, labels, load, streams=None, templates=False):
    if labels['image_end'] != load + len(binary):
        raise ValueError(f'{name}: image_end does not match the assembled size')
    info = dict(load=load, size=len(binary), sha256=hashlib.sha256(binary).hexdigest(), gap=labels['gap'])
    if streams is not None:
        if labels['starts'] != load+6 or labels['loop_song'] != load+6+2*streams:
            raise ValueError(f'{name}: changed entry/header ABI')
        info.update(streams=streams, workspace_start=labels['sequence_lo']-load,
                    workspace_bytes=labels['image_end']-labels['sequence_lo'])
    else:
        info.update(format=1, starts_lo=labels['starts_lo']-load, starts_hi=labels['starts_hi']-load,
                    loop=labels['loop_enabled']-load, workspace_bytes=labels['image_end']-labels['workspace'])
        if templates:
            info.update(template_low=labels['template_low_load']+1-load,
                        template_high=labels['template_high_load']+1-load)
    return info


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--assembler', default='64tass')
    args = parser.parse_args()
    assembler = shutil.which(args.assembler)
    if assembler is None:
        parser.error('64tass is required for rebuilding, not for ordinary export')
    root = Path(__file__).resolve().parents[1]
    assets = root / 'sidpulse' / 'assets'
    jobs = []
    for streams, mode in ((1, 'single'), (5, 'lanes'), (26, 'registers')):
        for address, suffix in ((0x1000, ''), (0x09B4, '-prg')):
            jobs.append((f'squeeze-{mode}{suffix}', 'squeeze_player.asm', address, streams, False))
    for streams, mode in ((1, 'single'), (5, 'lanes'), (26, 'registers')):
        for address, suffix in ((0x1000, ''), (0x09B4, '-prg')):
            jobs.append((f'squeeze-phrases-{mode}{suffix}', 'squeeze_phrases.asm', address, streams, False))
    for streams, mode in ((1, 'single'), (5, 'lanes'), (26, 'registers')):
        for address, suffix in ((0x1000, ''), (0x09B4, '-prg')):
            jobs.append((f'squeeze-indexed-{mode}{suffix}', 'squeeze_indexed.asm', address, streams, False))
    for templates, mode in ((False, 'raw'), (True, 'templates')):
        for address, suffix in ((0x1000, ''), (0x09B4, '-prg')):
            jobs.append((f'channel-{mode}{suffix}', 'player_channels.asm', address, None, templates))
    with tempfile.TemporaryDirectory(prefix='sidpulse-player-build-') as temp:
        outputs, manifest = {}, {}
        for name, source, address, streams, templates in jobs:
            binary = Path(temp) / (name + '.bin')
            labels = Path(temp) / (name + '.labels')
            defines = ['-D', f'PLAYER_LOAD={address}', '-D',
                       f'STREAMS={streams}' if streams is not None else f'TEMPLATES={int(templates)}']
            subprocess.run([assembler, '--nostart', '--normal-labels', '-l', str(labels),
                            *defines, '-o', str(binary), str(root/'sidpulse'/'export'/source)], check=True)
            data = binary.read_bytes()
            info = player_metadata(name, data, read_labels(labels), address, streams, templates)
            if source in ('squeeze_phrases.asm', 'squeeze_indexed.asm'):
                info['phrase_calls'] = True
            if source == 'squeeze_indexed.asm': info['indexed_packets'] = True
            outputs[name + '.bin'] = data
            if streams is None:
                outputs[name + '.json'] = (json.dumps(info, indent=2) + '\n').encode()
            manifest[name] = info
        name = 'prg-loader-squeezed.bin'
        binary = Path(temp)/name
        subprocess.run([assembler, '--nostart', '-o', str(binary),
                        str(root/'sidpulse/export/prg_loader_squeezed.asm')], check=True)
        outputs[name] = binary.read_bytes()
        if len(outputs[name]) != 0x09B4 - 0x0801:
            raise ValueError('PRG wrapper changed size; review music link address')
        outputs['replay-players.json'] = (json.dumps(manifest, indent=2, sort_keys=True)+'\n').encode()
        # Do not partially rewrite outputs because a later assembly job failed.
        for name, data in outputs.items():
            target = assets/name
            if args.check:
                equal = (json.loads(target.read_bytes()) == json.loads(data)
                         if name.endswith('.json') else target.read_bytes() == data)
                if not equal:
                    raise ValueError(f'{name}: bundled bytes/metadata differ from 64tass output')
            else:
                target.write_bytes(data)
            print(f'{name}: {len(data)} bytes {"verified" if args.check else "written"}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
