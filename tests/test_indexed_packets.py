"""Exact streams, shared suffixes, strict dictionaries and independent 6502 checks."""
from dataclasses import replace
from pathlib import Path
import json,random
import pytest
from sidpulse.export.phrase_calls import pack_phrases
from sidpulse.export.stream_packer import pack_streams
from sidpulse.export.indexed_packets import pack_indexed,verify_indexed,IndexedReader,FIRST
from sidpulse.export.squeeze_v202 import IndexedCandidate
from sidpulse.export.squeeze import make_streams,make_register_streams,verify_candidate
from sidpulse.export.replay_verify import ReplayCPU,verify_replay
from test_phrase_calls import literal_seed
from test_channel_squeeze import interleaved

@pytest.mark.parametrize('seed',range(8))
def test_random_blocks_empty_streams_repeats_long_literals_and_determinism(seed):
    rng=random.Random(seed);pieces=[rng.randbytes(50) for _ in range(8)]
    packets=[[rng.choice(pieces) for _ in range(150)],[b'repeat'*20]*600,[],[rng.randbytes(127)]]
    streams=tuple(b''.join(p) for p in packets);original=pack_phrases(literal_seed(packets),streams)
    packed=pack_indexed(original,streams)
    assert packed.dictionary and packed==pack_indexed(original,streams)
    verify_indexed(packed,streams);linked=packed.link(0x20ff)
    for site,target in (packed.calls|packed.references).items():assert int.from_bytes(linked[site:site+2],'little')==0x20ff+target

def test_shared_suffixes_and_long_literal_splitting():
    packets=[[b'A'*127,b'B'*120,b'C'*80]*60,[b'B'*120,b'C'*80]*50]
    streams=tuple(b''.join(p) for p in packets)
    packed=pack_indexed(pack_phrases(literal_seed(packets),streams),streams)
    assert len(packed.phrases)==2 and max(packed.phrases.values())>3
    verify_indexed(packed,streams)

@pytest.mark.parametrize('damage',['bad_id','bad_phrase','nested','missing_return','trailing','bad_literal'])
def test_malformed_dictionary_or_phrase_rejected(damage):
    streams=make_register_streams(interleaved(count=48)*5)
    p=pack_indexed(pack_phrases(pack_streams(streams,8),streams),streams)
    data=bytearray(p.data);dictionary=list(p.dictionary)
    phrase_id=next(i for i,(n,t) in enumerate(dictionary) if not n)
    literal_id=next(i for i,(n,t) in enumerate(dictionary) if n)
    if damage=='bad_id':data[p.starts[0]]=127;p=replace(p,dictionary=())
    elif damage=='bad_phrase':dictionary[phrase_id]=(0,len(data))
    elif damage=='nested':data[dictionary[phrase_id][1]]=FIRST+phrase_id
    elif damage=='missing_return':
        target=dictionary[phrase_id][1]
        for _ in range(p.phrases[target]):
            tag=data[target];target+=1 if FIRST<=tag<128 else 3 if tag&128 else tag+1
        data[target]=1
    elif damage=='trailing':data.extend((1,88))
    else:dictionary[literal_id]=(dictionary[literal_id][0],p.starts[0])
    if damage!='bad_id':p=replace(p,dictionary=tuple(dictionary))
    with pytest.raises((ValueError,KeyError,IndexError)):verify_indexed(replace(p,data=bytes(data)),streams)

@pytest.mark.parametrize('mode',['single','lanes','registers'])
@pytest.mark.parametrize('load',[0x1000,0x09b4])
@pytest.mark.parametrize('loop',[False,True])
def test_independent_6502_cycles_writes_loop_reinit_decimal_and_dictionary(mode,load,loop):
    from py65_nmos import MPU
    from test_psid import Memory,call
    records=interleaved(count=48)*5
    streams=make_register_streams(records) if mode=='registers' else make_streams(records,mode=='lanes')
    packed=pack_indexed(pack_phrases(pack_streams(streams,8),streams),streams)
    assert any(not n for n,_ in packed.dictionary) and any(n for n,_ in packed.dictionary)
    assets=Path(__file__).resolve().parents[1]/'sidpulse/assets';name='squeeze-indexed-'+mode+('-prg' if load!=0x1000 else '')
    info=json.loads((assets/'replay-players.json').read_text())[name];player=(assets/(name+'.bin')).read_bytes()
    bound,safe=verify_candidate(packed,records,mode=='lanes',registers=mode=='registers',reader_type=IndexedReader)
    choice=IndexedCandidate(mode,packed,player,bound,safe,load,info['gap']);image=choice.image(loop)
    checked=verify_replay(image,len(player),records,loop,load=load,gap_address=info['gap'])
    assert checked.measured_max_cycles<bound and checked.stack_bytes<=4
    mem=Memory();mem[load:load+len(image)]=image
    class InstrumentedMPU(MPU):
        def step(self):
            if self.pc==info['gap']:mem.events.append((25,32))
            return super().step()
    independent=InstrumentedMPU(memory=mem);bundled=ReplayCPU(image,len(player),load=load,gap_address=info['gap'])
    addresses=[]
    for traversal in range(2 if loop else 1):
        for index,record in enumerate(records):
            addresses.append(load if not traversal and not index else load+3);addresses.extend([load+3]*record[2])
    if not loop:addresses.extend([load+3]*2)
    addresses.append(load)
    for address in addresses:
        mem.events.clear();mem.writes.clear();independent.p|=independent.DECIMAL
        assert call(independent,address)==bundled.call(address)
        assert mem.events==bundled.events
        assert [(a,v) for a,v in mem.writes if a in (0xdc04,0xdc05,0xdc0e)]==bundled.timer_events
        assert all(0x100<=a<0x200 or load<=a<load+len(player) or a in (0xf8,0xf9,0xdc04,0xdc05,0xdc0e) or 0xd400<=a<=0xd418 for a,_ in mem.writes)
        header=7+2*len(packed.starts)
        assert bytes(mem[load+header:load+header+336])==image[header:header+336]
