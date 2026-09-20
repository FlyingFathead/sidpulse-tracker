from copy import deepcopy
import json
from pathlib import Path
import shutil
import struct

import pytest

from sidpulse.export.pcm import compile_pcm
from sidpulse.export.psid import ExportError
from sidpulse.export.squeeze import SqueezeOptions
from sidpulse.song.model import Cell
from test_pcm_media import pcm_song

pytestmark=pytest.mark.skipif(not shutil.which('ffmpeg'),reason='C64 anti-aliased sample conversion needs FFmpeg')


@pytest.mark.parametrize('clock',['PAL','NTSC'])
@pytest.mark.parametrize('loop',[False,True])
@pytest.mark.parametrize('method',[1,2])
def test_c64_pcm_real_headers_budget_loop_and_source_preservation(clock,loop,method):
    song=pcm_song();song.clock=clock;song.export_config['loop']=loop
    before=deepcopy(song)
    result=compile_pcm(song,squeeze=SqueezeOptions(digi_method=method))
    assert song==before and result.data[:4]==b'RSID'
    assert struct.unpack_from('>H',result.data,8)[0]==0
    assert struct.unpack_from('>H',result.data,12)[0]==0
    assert struct.unpack_from('>I',result.data,18)[0]==0
    assert result.data[124:126]==b'\x01\x08'
    assert result.squeeze_report.verified_calls>=4
    assert result.max_cycles_bound<round((985248 if clock=='PAL' else 1022727)*2.5/127)
    prg=compile_pcm(song,kind='prg',squeeze=SqueezeOptions(digi_method=method))
    assert prg.data[:2]==b'\x01\x08' and prg.data[2:14]==bytes.fromhex('0b080a009e32303631000000')


def test_c64_rejects_pcm_on_wrong_channel_without_losing_notes():
    song=pcm_song();song.patterns[0].rows[0][0]=Cell(48,1)
    with pytest.raises(ExportError,match='CH3'):
        compile_pcm(song)


def test_c64_switches_between_pcm_and_sid_and_preserves_filter_timing():
    from sidpulse.song.model import Instrument,ControlCell
    song=pcm_song(rate=4005)
    song.instruments[2]=Instrument(waveform=128)
    song.patterns[0].rows=[
        [Cell(),Cell(),Cell(48,1)],
        [Cell(effect='T',parameter=32),Cell(),Cell(42,2)],
        [Cell(),Cell(),Cell(55,1)],
        [Cell(),Cell(),Cell(-2)],
    ]
    song.patterns[0].controls[0]=ControlCell(routing=7,volume=9)
    song.patterns[0].controls[2]=ControlCell(routing=4,volume=15)
    result=compile_pcm(song)
    assert result.squeeze_report.verified_calls>=8


@pytest.mark.parametrize('decoder', ['plain', 'phrases', 'indexed'])
@pytest.mark.parametrize('method', [1, 2])
def test_c64_preempted_decoder_matches_independent_cpu(decoder, monkeypatch, method):
    """Interrupt every few instructions, including between ZP pointer stores.

    py65 is independent of the compiler's bounded verifier. The NMI must not
    corrupt music stream pointers, flags or the held sample when preempted.
    """
    mpu=pytest.importorskip('py65.devices.mpu6502').MPU
    from test_pcm_comparison import repeating_song
    import sidpulse.export.pcm as pcm
    from sidpulse.export.pcm_squeeze import candidates
    song=repeating_song()
    def only_decoder(streams, version, cache, progress=None):
        return [c for c in candidates(streams, version, cache, progress) if c.decoder==decoder]
    monkeypatch.setattr(pcm,'candidates',only_decoder)
    result=compile_pcm(song,squeeze=SqueezeOptions(digi_method=method))
    name=('pcm-volume-player' if method==1 else 'pcm-player')+('' if decoder=='plain' else '-'+decoder)+'.json'
    labels=json.loads((Path(__file__).resolve().parents[1]/'sidpulse/assets'/name).read_text())['labels']
    assert decoder=='plain' or ('phrase calls' if decoder=='phrases' else 'dictionary IDs') in result.squeeze_report.algorithm
    traces=[]
    for preempt in (False,True):
        class Memory(list):
            def __init__(self):
                super().__init__([0]*65536);self.events=[];self.in_nmi=False
            def __setitem__(self,address,value):
                if isinstance(address,int) and 0xd400<=address<=0xd418 and not self.in_nmi:
                    self.events.append((address-0xd400,value))
                super().__setitem__(address,value)
        mem=Memory();mem[0x0801:0x0801+len(result.data)-126]=result.data[126:]
        mem[0xfffa]=labels['nmi']&255;mem[0xfffb]=labels['nmi']>>8
        cpu=mpu(memory=mem)
        trace=[]
        for address in [labels['init']]+[labels['play']]*95:
            cpu.sp=255;cpu.stPushWord(0x1ff);cpu.pc=address
            for count in range(15000):
                if cpu.pc==0x200:break
                if preempt and count%7==3:
                    saved=cpu.a,cpu.x,cpu.y,cpu.p,cpu.sp,cpu.pc
                    mem.in_nmi=True;mem[0xdd0d]=0x81
                    cpu.nmi()
                    for _ in range(100):
                        if mem[cpu.pc]==0x40:
                            cpu.step();break
                        cpu.step()
                    assert (cpu.a,cpu.x,cpu.y,cpu.p&~0x10,cpu.sp,cpu.pc)==(saved[0],saved[1],saved[2],saved[3]&~0x10,saved[4],saved[5])
                    mem.in_nmi=False
                cpu.step()
            else:pytest.fail('Preempted music decoder failed to return')
            # NMI naturally ending changes only D418 restoration timing.
            trace.extend((r,v) for r,v in mem.events if r!=24)
            mem.events.clear()
        traces.append(trace)
    assert traces[0]==traces[1]
