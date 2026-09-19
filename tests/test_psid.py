from copy import deepcopy
import struct
import math
import pytest
from py65_nmos import MPU

from sidpulse.export.psid import compile_song,save_export,RecordingSID,ExportError
from sidpulse.playback.sequencer import Sequencer
from sidpulse.song.model import Song,Pattern,Cell,ControlCell,example_song


class Memory(list):
    def __init__(self):
        super().__init__([0]*65536)
        self.events=[];self.writes=[]
    def __setitem__(self,address,value):
        if isinstance(address,int):
            self.writes.append((address,value))
            if 0xD400<=address<=0xD418:self.events.append((address-0xD400,value))
        super().__setitem__(address,value)


def machine(data):
    fields=struct.unpack('>4s7HI',data[:22])
    assert fields==(b'PSID',2,124,0x1000,0x1000,0x1003,1,1,1)
    mem=Memory();mem[0x1000:0x1000+len(data)-124]=data[124:]
    return MPU(memory=mem),mem


def call(cpu,address):
    cpu.pc=address;cpu.stPushWord(0x0200-1)
    before=cpu.processorCycles
    for _ in range(10000):
        if cpu.pc==0x0200:return cpu.processorCycles-before
        cpu.step()
    pytest.fail('6510 routine failed to return')


def trace_song(song):
    sid=RecordingSID(song.clock);seq=Sequencer(sid);seq.start(deepcopy(song),loop=False)
    while True:
        seq._boundary()
        yield [(r,v) for r,v in sid.events if r<25],seq.tempo
        sid.events=[]
        if seq.status!='playing':break
        seq.frames=int(seq.next_tick)


@pytest.mark.parametrize("squeeze", [False, True])
def test_exported_6502_matches_every_ordered_sid_write_of_first_light(squeeze):
    song=example_song();song.export_config["loop"]=False;before=deepcopy(song);result=compile_song(song, squeeze=squeeze)
    assert song==before and result.data==compile_song(song, squeeze=squeeze).data
    assert (5000 if squeeze else 10000)<len(result.data)<(10000 if squeeze else 30000)
    assert result.unique_records<result.ticks//2
    assert result.seconds==pytest.approx(46.08)
    cpu,mem=machine(result.data)
    maximum=0
    for tick,(expected,tempo) in enumerate(trace_song(song)):
        mem.events=[]
        cpu.p |= cpu.DECIMAL  # caller may have been doing BCD arithmetic
        elapsed=call(cpu,0x1000 if tick==0 else 0x1003)
        maximum=max(maximum,elapsed)
        actual=mem.events[25:] if tick==0 else mem.events  # init explicitly zeroes hardware
        assert actual==expected,(tick,actual,expected)
        timer=mem[0xDC04]|mem[0xDC05]<<8
        assert timer==round(985248*2.5/tempo)-1
        assert elapsed<timer
    assert maximum<result.max_cycles_bound
    mem.events=[];call(cpu,0x1003);assert mem.events==[(4,0),(11,0),(18,0)]
    mem.events=[];call(cpu,0x1003);assert not mem.events
    # Only owned RAM, stack, zero page, SID and CIA timer/control are touched.
    player_end=0x1000+result.squeeze_report.player_bytes
    zero_page_end=0xF8+result.squeeze_report.zero_page_bytes
    assert all(0x100<=a<0x200 or 0x1000<=a<player_end or 0xF8<=a<zero_page_end or
               0xD400<=a<=0xD418 or a in (0xDC04,0xDC05,0xDC0E) for a,v in mem.writes)


@pytest.mark.parametrize("squeeze", [False, True])
def test_psid_tempo_changes_gate_delay_effects_and_filter_writes(squeeze):
    song=Song(speed=3,export_config={"loop":False})
    rows=[[Cell(48,1,'J',0x37),Cell(24,2),Cell(36,4)],
          [Cell(effect='E',parameter=2),Cell(effect='T',parameter=150),Cell(effect='Q',parameter=2)],
          [Cell(55,1,'G',0x10),Cell(effect='A',parameter=4),Cell(48,4,'S',0xD2)],
          [Cell(effect='H',parameter=0x34),Cell(effect='F',parameter=0xF2),Cell(effect='S',parameter=0xC2)]]
    song.patterns={0:Pattern(rows=rows,controls={0:ControlCell(0x200,8,2,16,15,4),2:ControlCell(slide=-5)})}
    result=compile_song(song, squeeze=squeeze);cpu,mem=machine(result.data)
    for i,(expected,tempo) in enumerate(trace_song(song)):
        mem.events=[];call(cpu,0x1000 if i==0 else 0x1003)
        assert (mem.events[25:] if i==0 else mem.events)==expected
        assert mem[0xDC04]|mem[0xDC05]<<8==round(985248*2.5/tempo)-1


@pytest.mark.parametrize("squeeze", [False, True])
def test_loop_export_restarts_data_and_psid_flags_match_chip(squeeze):
    song=Song(speed=1);song.sid_model='6581';song.patterns[0].rows=[[Cell(48,1),Cell(),Cell()]]
    song.export_config={'loop':True};result=compile_song(song, squeeze=squeeze)
    assert struct.unpack('>H',result.data[118:120])[0]==0x14
    cpu,mem=machine(result.data);call(cpu,0x1000);first=mem.events[25:]
    for _ in range(3):
        mem.events=[];call(cpu,0x1003);assert mem.events==first


def test_export_rejects_unimplemented_effect_and_control_flow_without_source_loss(tmp_path):
    song=Song();song.patterns[0].rows[0][0]=Cell(effect='P',parameter=0x12)
    with pytest.raises(ExportError,match='row 000, CH 1: P12'):compile_song(song)
    song.patterns[0].rows[0][0]=Cell(effect='B',parameter=0)
    with pytest.raises(ExportError,match='revisits order'):compile_song(song)
    song.patterns[0].rows[0][0]=Cell();song.instruments[1].macros={'future':42}
    with pytest.raises(ExportError,match='extension macro'):compile_song(song)


def test_export_file_backup_and_atomic_failure(tmp_path,monkeypatch):
    result=compile_song(Song());path=save_export(tmp_path/'work.sid',result)
    first=path.read_bytes();song=Song(title='Another title');save_export(path,compile_song(song))
    assert path.with_suffix('.sid.bak').read_bytes()==first
    second=path.read_bytes()
    def fail(*args):raise OSError('Full disk')
    monkeypatch.setattr('sidpulse.export.psid.os.replace',fail)
    with pytest.raises(OSError):save_export(path,result)
    assert path.read_bytes()==second


@pytest.mark.parametrize("squeeze", [False, True])
def test_tempo_32_uses_two_cia_calls_per_tick(squeeze):
    song=Song(tempo=32,speed=1);song.patterns[0].rows=[[Cell(48,1),Cell(),Cell()],[Cell(50,1),Cell(),Cell()]]
    result=compile_song(song, squeeze=squeeze);cpu,mem=machine(result.data)
    call(cpu,0x1000)
    assert mem[0xDC04]|mem[0xDC05]<<8==round(round(985248*2.5/32)/2)-1
    mem.events=[];call(cpu,0x1003);assert not mem.events
    call(cpu,0x1003);assert any(r==4 and v&1 for r,v in mem.events)
