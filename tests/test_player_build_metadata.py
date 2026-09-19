"""Canonical build manifest contracts without requiring the external assembler."""
import importlib.util
import json
from pathlib import Path
import hashlib

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('build_players', ROOT/'scripts/build_squeeze_players.py')
build = importlib.util.module_from_spec(spec); spec.loader.exec_module(build)


def test_normal_64tass_label_output_parser(tmp_path):
    path = tmp_path/'labels'
    path.write_text('init = $1007\nstarts\t=\t$1006\nSTREAMS = 26\ngap = $10f3 ; comment\nignored expression = abc\n')
    assert build.read_labels(path) == dict(init=0x1007, starts=0x1006, STREAMS=26, gap=0x10f3)


def test_all_linked_player_assets_match_metadata_and_have_no_full_song_workspace():
    assets = ROOT/'sidpulse/assets'
    manifest = json.loads((assets/'replay-players.json').read_text())
    assert len(manifest) == 22
    for name, info in manifest.items():
        binary = (assets/(name+'.bin')).read_bytes()
        assert len(binary) == info['size']
        assert hashlib.sha256(binary).hexdigest() == info['sha256']
        assert info['load'] <= info['gap'] < info['load']+len(binary)
        assert 0 < info['workspace_bytes'] <= (217 if info.get('phrase_calls') else 139)
        assert binary[0] == binary[3] == 0x4c
        if name.startswith('channel-'):
            assert json.loads((assets/(name+'.json')).read_text()) == info
