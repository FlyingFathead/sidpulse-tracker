from copy import deepcopy
from dataclasses import replace

import pygame as pg
import pytest

from sidpulse.app import App
from sidpulse.commands.editor import Editor
from sidpulse.commands.pattern_fields import FIELDS
from sidpulse.export.psid import RecordingSID, compile_song
from sidpulse.playback.sequencer import Sequencer
from sidpulse.playback.voices import VoicePrograms, supported
from sidpulse.project.format import ProjectError, encode, decode, load, save
from sidpulse.song.model import Cell, Instrument, Pattern, Song, WAVEFORM_KEYS
from sidpulse.ui.effects import lookup_effect
from test_pcm_media import SilentSID, pcm_song
from test_psid import machine, call, trace_song


def modulation_song():
    s=Song(speed=3,export_config={'loop':False})
    s.instruments[1]=Instrument(waveform=0x10,wave_sequence=[0x10,0x80,0x40,0x20,0x10],
                               pitch_sequence=[0,7,2],arpeggio=[0,12])
    s.instruments[2]=replace(s.instruments[1],sync=True,ring=True,wave_sequence_enabled=False)
    s.patterns={0:Pattern(rows=[
        [Cell(48,1),Cell(52,1),Cell(55,1)],
        [Cell(waveform=0x10,effect='Z',parameter=0x11),Cell(waveform=0x80),Cell()],
        [Cell(effect='Z',parameter=0x21),Cell(50,2,waveform=0x20),Cell(effect='H',parameter=0x23)],
        [Cell(50,1,'S',0xD2,waveform=0x40),Cell(waveform=-1),Cell(effect='Z',parameter=0x10)],
    ]),1:Pattern(rows=[
        [Cell(waveform=-1,effect='Z',parameter=0x1F),Cell(effect='Z',parameter=0x20),Cell()],
        [Cell(effect='Q',parameter=2),Cell(48,2,'G',4),Cell(waveform=0x10,effect='Z',parameter=0x21)],
        [Cell(effect='Z',parameter=0x2F),Cell(effect='Z',parameter=0x1F),Cell(waveform=-1)],
    ])}
    s.orders=[0,1]
    return s


def test_held_wave_switch_preserves_gate_and_returns_to_table_at_current_age():
    sid=RecordingSID();p=VoicePrograms(sid)
    inst=Instrument(wave_sequence=[0x10,0x80,0x40,0x20,0x10],sync=True,ring=True,_extra_fields={'editor_frozen':True})
    before=deepcopy(inst)
    p.row(0,Cell(48,1),inst,1);p.row(1,Cell(52,1),inst,1);p.tick(0)
    sid.events.clear()
    p.row(0,Cell(waveform=0x80),inst,1);p.tick(1)
    assert sid.registers[4]==0x87 and sid.registers[11]==0x87
    assert all(value&1 for register,value in sid.events if register==4)
    p.row(0,Cell(),inst,1);p.tick(2)
    assert sid.registers[4]==0x87 and sid.registers[11]==0x47
    p.row(0,Cell(waveform=-1),inst,1);p.tick(0)
    assert sid.registers[4]==0x27  # fourth table entry, not first
    assert p.voices[0].age==4 and inst==before


def test_sync_ring_independent_persistent_off_on_default_and_retrigger():
    sid=RecordingSID();p=VoicePrograms(sid);inst=Instrument(waveform=0x10,sync=True,ring=False)
    p.row(0,Cell(48,1),inst,1);p.tick(0)
    for code,expected in [(0x10,0x11),(0x21,0x15),(0x11,0x17),(0x20,0x13),(0x2F,0x13),(0x1F,0x13)]:
        sid.events.clear();p.row(0,Cell(effect='Z',parameter=code),inst,1);p.tick(0)
        assert sid.registers[4]==expected
        assert all(value&1 for register,value in sid.events if register==4)
    p.row(0,Cell(waveform=0x80,effect='Z',parameter=0x21),inst,1)
    for cell in (Cell(50,1),Cell(52,1,'S',0xD2),Cell(effect='Q',parameter=2)):
        p.row(0,cell,inst,1)
        for tick in range(3):
            p.tick(tick);assert sid.registers[4]==0x87
    p.row(0,Cell(48,2),replace(inst,sync=False,ring=False),2);p.tick(0)
    assert sid.registers[4]==0x85  # sync inherits new instrument; explicit ring survives
    p.row(0,Cell(note=-1),inst,1);p.tick(0)
    p.row(0,Cell(waveform=0x40,effect='Z',parameter=0x10),inst,1);p.tick(0)
    assert sid.registers[4]==0x44  # release gate remains clear


def test_order_transition_keeps_overrides_and_song_loop_resets_them():
    s=modulation_song();s.export_config['loop']=True
    seq=Sequencer(SilentSID());seq.start(s);seq.render(960*12+1)
    assert seq.order==1 and seq.programs.voices[0].ring_override is True
    seq.render(960*9)
    assert seq.loops==1
    assert all(v.waveform_override is None and v.sync_override is None and v.ring_override is None for v in seq.programs.voices)


@pytest.mark.parametrize('clock',['PAL','NTSC'])
@pytest.mark.parametrize('squeeze',[False,True])
def test_exported_6510_writes_match_native_waveform_and_macro_playback(clock,squeeze):
    s=modulation_song();s.clock=clock;before=deepcopy(s)
    result=compile_song(s,squeeze=squeeze);cpu,mem=machine(result.data)
    for tick,(expected,_) in enumerate(trace_song(s)):
        mem.events=[];call(cpu,0x1000 if tick==0 else 0x1003)
        assert (mem.events[25:] if tick==0 else mem.events)==expected
    assert s==before


def test_pcm_stays_disconnected_and_keeps_overrides_for_next_sid_note():
    from sidpulse.audio.samples import SamplePrograms
    from sidpulse.export.pcm import record_pcm
    s=pcm_song(rate=4000);inst=s.instruments[1];sid=SilentSID()
    p=SamplePrograms(sid,samples=s.samples)
    p.row(2,Cell(48,1,waveform=0x80,effect='Z',parameter=0x11),inst,1)
    p.row(2,Cell(effect='Z',parameter=0x21),inst,1);p.tick(0)
    assert sid.registers[18]&0xF6==0 and p.pcm[2] is not None
    plain=SamplePrograms(SilentSID(),samples=s.samples)
    plain.row(2,Cell(48,1),inst,1);plain.tick(0)
    assert p.render(512)==plain.render(512)
    p.row(2,Cell(50,2),Instrument(),2);p.tick(0)
    assert sid.registers[18]==0x87 and p.pcm[2] is None
    # The C64 one-shot compiler shares the same PCM isolation.
    before=record_pcm(s)[0]
    for row in s.patterns[0].rows:
        row[2].waveform=0x80;row[2].effect='Z';row[2].parameter=0x11
    assert record_pcm(s)[0]==before


@pytest.mark.parametrize('invalid',[True,False,0,1,2,3,4,-2,0x30,0x11,'T',16.0])
def test_waveform_schema_rejects_invalid_values(invalid):
    raw=encode(Song());raw['song']['patterns'][0]['rows'][0][0]['waveform']=invalid
    with pytest.raises(ProjectError,match='row waveform'):decode(raw)


def test_new_format_only_when_used_and_roundtrip(tmp_path):
    s=modulation_song();assert encode(s)['format_version']==10
    assert load(save(tmp_path/'wave.sidpulse',s))[0]==s
    assert encode(Song())['format_version']==6
    assert encode(pcm_song())['format_version']==8
    s=Song();s.patterns[0].rows[0][0]=Cell(effect='Z',parameter=0x11)
    assert encode(s)['format_version']==10
    for value in range(256):
        expected=value in (0x10,0x11,0x1F,0x20,0x21,0x2F)
        assert supported('Z',value)==expected
        assert bool(lookup_effect('Z',value)['preview_implemented'])==expected
    assert supported('S',0xC2) and supported('S',0xD2)
    assert not supported('W',0x11) and not supported('R',0x11)


def test_waveform_entry_mask_clipboard_reset_and_undo():
    ed=Editor();ed.column=FIELDS.index('waveform')
    for char,value in WAVEFORM_KEYS.items():
        row=ed.row;ed.enter_digit(char.lower())
        assert ed.pattern.rows[row][0].waveform==value
    ed.row=0;ed.select_field(0,ed.column);ed.copy();ed.voice=2
    ed.paste(scope='automation')
    assert [row[0].waveform for row in ed.pattern.rows]==[row[2].waveform for row in ed.pattern.rows]
    ed.history.undo(ed.song);assert all(row[2].waveform is None for row in ed.pattern.rows)
    ed.anchor=None;ed.selection_end=None;ed.row=20;ed.edit_mask={'waveform'}
    ed.enter_note(48);assert ed.pattern.rows[20][2].waveform==-1
    ed.row=20;ed.clear_field();assert ed.pattern.rows[20][2].waveform is None
    ed.history.undo(ed.song);assert ed.pattern.rows[20][2].waveform==-1
    ed.row=0;ed.voice=0;ed.reset_automation();assert ed.cell.waveform==0x10


@pytest.mark.parametrize('size',[(640,480),(960,1080),(1280,900),(1920,1080)])
def test_w_column_mouse_keyboard_layout_and_legacy_cursor_restore(size):
    app=App(modulation_song(),audio=False,size=size)
    try:
        app.renderer.render(app);before=deepcopy(app.editor.song)
        rect=next(r for r,a,v in app.renderer.hits if a=='select_field' and v==(0,6))
        assert app.screen.get_rect().contains(rect)
        app.handle(pg.event.Event(pg.MOUSEBUTTONDOWN,button=1,pos=rect.center))
        app.handle(pg.event.Event(pg.MOUSEBUTTONUP,button=1,pos=rect.center))
        assert app.editor.column==6 and app.editor.selected_fields(0)=={'waveform'}
        for char,scan in [('t',23),('s',22),('p',19),('n',17),('r',21)]:
            row=app.editor.row
            app.handle(pg.event.Event(pg.KEYDOWN,key=ord(char),unicode=char,scancode=scan,mod=0))
            assert app.editor.pattern.rows[row][0].waveform==WAVEFORM_KEYS[char.upper()]
        assert app.editor.song.instruments==before.instruments
        app.restore_metadata({'column':6});assert app.editor.column==7
        app.restore_metadata({'column':13});assert app.editor.column==14
        app.restore_metadata({'column':6,'pattern_columns_version':2});assert app.editor.column==6
        assert app.metadata()['pattern_columns_version']==2
        app.renderer.render(app)
        assert len(app.renderer.pattern_geometry['voices'])==(3 if size==(1920,1080) else 2)
        for voice,_,_ in app.renderer.pattern_geometry['voices']:
            assert any(a=='select_field' and v==(voice,14) and app.screen.get_rect().contains(r)
                       for r,a,v in app.renderer.hits)
    finally:app.close()


@pytest.mark.parametrize('clock',['PAL','NTSC'])
@pytest.mark.parametrize('squeeze',[False,True])
def test_prg_start_and_first_timer_tick_match_waveform_playback(clock,squeeze):
    from sidpulse.export.prg import compile_prg
    from sidpulse.export.squeeze import COMPACT_PRG_LOAD
    from sidpulse.export.psid import LOAD
    from test_prg import machine as prg_machine, step_until
    s=modulation_song();s.clock=clock
    s.patterns[0].rows[0][0].waveform=0x80
    s.patterns[0].rows[0][0].effect='Z';s.patterns[0].rows[0][0].parameter=0x11
    result=compile_prg(s,squeeze=squeeze);cpu,mem=prg_machine(result.data,clock=='PAL')
    step_until(cpu,lambda:cpu.pc==(COMPACT_PRG_LOAD if squeeze else LOAD))
    mem.events=[];reads=mem.icr_reads
    step_until(cpu,lambda:mem.icr_reads>reads)
    assert mem.events[25:]==next(trace_song(s))[0]
    assert mem[0xD404]==0x83
