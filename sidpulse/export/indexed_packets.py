"""SQUEEZER v2.0.2: short IDs for frequent immutable blocks and phrase calls."""
from collections import Counter
from dataclasses import dataclass
from bisect import bisect_right
from .phrase_calls import PhraseStreams

SLOTS=112
FIRST=128-SLOTS


@dataclass(frozen=True)
class IndexedStreams(PhraseStreams):
    dictionary: tuple[tuple[int,int], ...] = ()


def pack_indexed(seed, streams):
    calls=getattr(seed,'calls',{}); phrases=getattr(seed,'phrases',{})
    frequency=Counter((0,target) for site,target in calls.items() if seed.data[site-1]==1)
    frequency.update((seed.data[site-1]&127,target) for site,target in seed.references.items())
    keys=sorted(frequency,key=lambda k:(-(frequency[k]*(2 if k[0] else 3)-3),k))[:SLOTS]
    indices={key:FIRST+i for i,key in enumerate(keys)}
    # The existing immutable bank stays byte-identical; only packet addresses move.
    pos=min((*seed.starts,*phrases)); output=bytearray(seed.data[:pos])
    ranges=[(a,b) for a,b in seed.literal_ranges if b<=pos]
    refs,new_calls,mapping,packet_counts={},{},{},{}
    while pos<len(seed.data):
        start=pos; mapping[start]=len(output); tag=seed.data[pos]
        if tag==0:
            repeat=seed.data[pos+1]; target=calls[pos+2]
            if repeat==1 and (0,target) in indices:output.append(indices[0,target])
            else:
                output.extend((0,repeat));new_calls[len(output)]=target;output.extend(b'\0\0')
            pos+=4
        elif tag==128:output.append(128);pos+=1
        elif tag&128:
            target=seed.references[pos+1];key=(tag&127,target)
            if key in indices:output.append(indices[key])
            else:
                output.append(tag);refs[len(output)]=target;output.extend(b'\0\0')
            pos+=3;packet_counts[start]=1
        else:
            values=seed.data[pos+1:pos+1+tag];packet_counts[start]=0
            for offset in range(0,len(values),FIRST-1):
                part=values[offset:offset+FIRST-1];output.append(len(part));begin=len(output)
                output.extend(part);ranges.append((begin,len(output)));packet_counts[start]+=1
            pos+=tag+1
    mapping[len(seed.data)]=len(output)
    new_phrases={}
    for start,count in phrases.items():
        pos=start;new_count=0
        for _ in range(count):
            new_count+=packet_counts[pos];tag=seed.data[pos];pos+=3 if tag&128 else tag+1
        new_phrases[mapping[start]]=new_count
    packed=IndexedStreams(bytes(output),tuple(mapping[s] for s in seed.starts),refs,tuple(ranges),
        seed.minimum_match,{p:mapping[t] for p,t in new_calls.items()},new_phrases,
        tuple((n,t if n else mapping[t]) for n,t in keys))
    verify_indexed(packed,streams)
    return packed


class IndexedReader:
    """Independent strict decoder; shared IDs never imply recursive phrases."""
    def __init__(self,packed):
        self.packed=packed;n=len(packed.starts)
        self.positions=list(packed.starts);self.sources=[0]*n;self.left=[0]*n
        self.repeats=[0]*n;self.returns=[0]*n;self.cycles=0

    def read(self,stream):
        data=self.packed.data
        if not self.left[stream]:
            pos=self.positions[stream]
            if not 0<=pos<len(data):raise ValueError('Indexed stream out of bounds')
            if data[pos]==128:
                if not self.repeats[stream]:raise ValueError('Return outside indexed phrase')
                self.repeats[stream]-=1;site=self.returns[stream]
                pos=self.packed.calls[site+2] if self.repeats[stream] else site+(4 if data[site]==0 else 1)
                self.cycles+=210
            if not 0<=pos<len(data):raise ValueError('Indexed continuation out of bounds')
            tag=data[pos];entry=None
            if FIRST<=tag<128:
                index=tag-FIRST
                if index>=len(self.packed.dictionary):raise ValueError('Invalid dictionary ID')
                entry=self.packed.dictionary[index]
            if tag==0 or entry is not None and entry[0]==0:
                if self.repeats[stream]:raise ValueError('Nested indexed phrase')
                if tag==0:
                    if pos+4>len(data) or not data[pos+1]:raise ValueError('Invalid indexed call')
                    target=self.packed.calls[pos+2];repeat=data[pos+1]
                else:target=entry[1];repeat=1
                if target not in self.packed.phrases:raise ValueError('Invalid indexed phrase target')
                self.returns[stream]=pos;self.repeats[stream]=repeat;pos=target;self.cycles+=230
                tag=data[pos];entry=None
                if FIRST<=tag<128:
                    index=tag-FIRST
                    if index>=len(self.packed.dictionary):raise ValueError('Invalid body dictionary ID')
                    entry=self.packed.dictionary[index]
            if entry is not None:
                count,source=entry
                if not count:raise ValueError('Nested indexed phrase')
                self.positions[stream]=pos+1
            else:
                count=tag&127
                if not count or FIRST<=tag<128:raise ValueError('Empty or nested indexed phrase')
                if tag&128:source=self.packed.references[pos+1];self.positions[stream]=pos+3
                else:source=pos+1;self.positions[stream]=source+count
            if source<0 or source+count>len(data):raise ValueError('Indexed literal out of bounds')
            self.sources[stream],self.left[stream]=source,count
            self.cycles+=280
        else:self.cycles+=80
        value=data[self.sources[stream]];self.sources[stream]+=1;self.left[stream]-=1
        return value


def verify_indexed(packed, originals):
    if len(originals)!=len(packed.starts) or len(packed.dictionary)>SLOTS:raise ValueError('Invalid indexed header')
    beginnings=[a for a,_ in packed.literal_ranges]
    def literal(target,length,before):
        index=bisect_right(beginnings,target)-1
        if index<0:raise ValueError('Missing indexed literal')
        begin,end=packed.literal_ranges[index]
        if not begin<=target<target+length<=end<=before:raise ValueError('Indexed reference outside immutable literals')
    for position,target in packed.references.items():
        if not 1<=position<len(packed.data)-1 or packed.data[position-1]<=128:raise ValueError('Invalid indexed reference')
        literal(target,packed.data[position-1]&127,position-1)
    bank_end=min((*packed.starts,*packed.phrases))
    for count,target in packed.dictionary:
        if count:
            if not 1<=count<=127:raise ValueError('Invalid dictionary length')
            literal(target,count,bank_end)
        elif target not in packed.phrases:raise ValueError('Invalid dictionary phrase')
    for position,target in packed.calls.items():
        if (not 2<=position<len(packed.data)-1 or packed.data[position-2]!=0
                or not packed.data[position-1] or target not in packed.phrases or target>=position-2):raise ValueError('Invalid indexed call link')
    for start,count in packed.phrases.items():
        if not 1<=count<=1152:raise ValueError('Invalid indexed phrase size')
        pos=start
        for _ in range(count):
            if not 0<=pos<len(packed.data):raise ValueError('Truncated indexed phrase')
            tag=packed.data[pos]
            if FIRST<=tag<128:
                if tag-FIRST>=len(packed.dictionary) or not packed.dictionary[tag-FIRST][0]:raise ValueError('Nested dictionary phrase')
                pos+=1
            elif not tag&127:raise ValueError('Nested or empty indexed phrase')
            else:pos+=3 if tag&128 else tag+1
        if pos>=len(packed.data) or packed.data[pos]!=128:raise ValueError('Missing indexed return')
    reader=IndexedReader(packed)
    for channel,stream in enumerate(originals):
        if bytes(reader.read(channel) for _ in stream)!=stream:raise ValueError('Indexed packing changed decoded data')
        if reader.left[channel]:raise ValueError('Indexed packet exceeds stream')
        pos=reader.positions[channel]
        if reader.repeats[channel]:
            if reader.repeats[channel]!=1 or pos>=len(packed.data) or packed.data[pos]!=128:raise ValueError('Indexed phrase exceeds stream')
            site=reader.returns[channel];pos=site+(4 if packed.data[site]==0 else 1)
        end=packed.starts[channel+1] if channel+1<len(packed.starts) else len(packed.data)
        if pos!=end:raise ValueError('Unconsumed indexed packets')
