"""SQUEEZER v2.0.1 candidate family; v1.0/v2.0 remain independent fallbacks."""
from dataclasses import replace
import hashlib
import json
from pathlib import Path

from .phrase_calls import pack_phrases, PhraseReader


def additional_candidates(records, originals):
    from .squeeze import make_streams, make_register_streams, verify_candidate, COMPACT_PRG_LOAD
    assets = Path(__file__).resolve().parents[1]/'assets'
    manifest = json.loads((assets/'replay-players.json').read_text())
    for mode in ('single','lanes','registers'):
        pool = sorted((item for item in originals if item.mode==mode),key=lambda item:item.size)
        if not pool: continue
        seeds = [pool[0]]
        plain = next((item for item in pool if not item.optimized),None)
        if plain is not None and plain is not seeds[0]: seeds.append(plain)
        streams = make_register_streams(records) if mode=='registers' else make_streams(records,mode=='lanes')
        for seed in seeds:
            # Conservative bound: every packet represents at least one byte.
            if sum(map(len,streams))>4_000_000: continue
            try: packed = pack_phrases(seed.packed,streams)
            except ValueError as exc:
                if str(exc)=='Phrase search packet limit exceeded': continue
                raise
            if not packed.calls: continue
            suffix = '-prg' if seed.load==COMPACT_PRG_LOAD else ''
            name = f'squeeze-phrases-{mode}{suffix}'
            player = (assets/(name+'.bin')).read_bytes(); info = manifest[name]
            if hashlib.sha256(player).hexdigest()!=info['sha256']:
                raise ValueError('Invalid phrase player image')
            cycles,safe = verify_candidate(packed,records,mode=='lanes',registers=mode=='registers',reader_type=PhraseReader)
            yield replace(seed,packed=packed,player=player,gap_address=info['gap'],
                          cycles_bound=cycles,safe_timing=safe,optimized=True,optimizer_version=201)
