"""Short dictionary IDs; all earlier encodings remain independent fallbacks."""
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from .squeeze import StreamCandidate, make_streams, make_register_streams, verify_candidate, COMPACT_PRG_LOAD
from .indexed_packets import pack_indexed, IndexedReader, SLOTS


@dataclass(frozen=True)
class IndexedCandidate(StreamCandidate):
    def image(self, loop):
        image=bytearray(super().image(loop));header=7+2*len(self.packed.starts)
        for i,(count,target) in enumerate(self.packed.dictionary):
            address=self.load+len(self.player)+target
            image[header+i]=count
            image[header+SLOTS+i]=address&255
            image[header+2*SLOTS+i]=address>>8
        return bytes(image)


def additional_candidates(records, originals):
    assets=Path(__file__).resolve().parents[1]/'assets'
    manifest=json.loads((assets/'replay-players.json').read_text())
    for seed in originals:
        if seed.optimizer_version!=201:continue
        streams=make_register_streams(records) if seed.mode=='registers' else make_streams(records,seed.mode=='lanes')
        packed=pack_indexed(seed.packed,streams)
        suffix='-prg' if seed.load==COMPACT_PRG_LOAD else ''
        name=f'squeeze-indexed-{seed.mode}{suffix}';player=(assets/(name+'.bin')).read_bytes();info=manifest[name]
        if hashlib.sha256(player).hexdigest()!=info['sha256']:raise ValueError('Invalid indexed player image')
        if len(player)+len(packed.data)>=seed.size:continue
        cycles,safe=verify_candidate(packed,records,seed.mode=='lanes',registers=seed.mode=='registers',reader_type=IndexedReader)
        yield IndexedCandidate(seed.mode,packed,player,cycles,safe,seed.load,info['gap'],True,optimizer_version=202)
