from copy import deepcopy
from dataclasses import replace

import pygame as pg
import pytest

from sidpulse.app import App
from sidpulse.commands.editor import Editor
from sidpulse.export.psid import RecordingSID, compile_song
from sidpulse.playback.sequencer import Sequencer
from sidpulse.playback.voices import VoicePrograms
from sidpulse.project.format import ProjectError, encode, decode, load, save
from sidpulse.song.model import Cell, Instrument, Song, Pattern
from test_graphical_instruments import click, key
from test_pcm_media import SilentSID, pcm_song
from test_psid import call, machine, trace_song


def freq(sid,voice=0):
    return sid.registers[voice*7] | sid.registers[voice*7+1]<<8


def test_off_on_default_persist_across_notes_without_affecting_other_voices_or_programs():
    sid=RecordingSID();p=VoicePrograms(sid)
    inst=Instrument(arpeggio=[12],pitch_sequence=[7])
    before=deepcopy(inst)
    p.row(0,Cell(48,1),inst,1);p.row(1,Cell(48,1),inst,1);p.tick(0)
    assert freq(sid)==p.frequency(67)
    p.row(0,Cell(arp_mode=0),inst,1);p.tick(0)
    assert freq(sid)==p.frequency(55)
    assert freq(sid,1)==p.frequency(67)
    for cell in (Cell(),Cell(48,1),Cell(effect='J',parameter=0x37),Cell(effect='Q',parameter=2),Cell(48,1,'S',0xD2)):
        p.row(0,cell,inst,1)
        for tick in range(3):
            p.tick(tick);assert freq(sid)==p.frequency(55)
    p.row(0,Cell(arp_mode=1),inst,1);p.tick(0)
    assert freq(sid)==p.frequency(67)
    disabled=replace(inst,arpeggio_enabled=False)
    p.row(0,Cell(48,2),disabled,2);p.tick(0)
    assert freq(sid)==p.frequency(67)  # explicit ON overrides F4
    p.row(0,Cell(arp_mode=-1),disabled,2);p.tick(0)
    assert freq(sid)==p.frequency(55)
    p.row(0,Cell(effect='J',parameter=0x37),disabled,2);p.tick(1)
    assert freq(sid)==round(p.frequency(48)*2**(10/12))  # legacy J overrides F4
    p.row(0,Cell(effect='J',parameter=0),disabled,2);p.tick(2)
    assert freq(sid)==round(p.frequency(48)*2**(14/12))  # J00 still recalls J37
    assert inst==before


def automation_song():
    song=Song(speed=3,export_config={'loop':False})
    song.instruments[1]=Instrument(arpeggio=[0,7,12],pitch_sequence=[0,2],vibrato_speed=1,vibrato_depth=2)
    song.instruments[2]=replace(song.instruments[1],arpeggio_enabled=False)
    song.patterns={0:Pattern(rows=[
        [Cell(48,1),Cell(52,1),Cell(55,1)],
        [Cell(arp_mode=0),Cell(effect='H',parameter=0x23),Cell()],
        [Cell(50,1,'J',0x37),Cell(arp_mode=0),Cell(arp_mode=1)],
    ]),1:Pattern(rows=[
        [Cell(effect='J',parameter=0),Cell(),Cell()],
        [Cell(arp_mode=1),Cell(arp_mode=-1),Cell(60,2)],
        [Cell(arp_mode=-1),Cell(57,2,arp_mode=1),Cell(arp_mode=-1)],
    ])}
    song.orders=[0,1]
    return song


def test_order_transition_keeps_override_and_transport_loop_resets_it():
    song=automation_song();song.export_config['loop']=True
    sid=SilentSID();seq=Sequencer(sid);seq.start(song)
    seq.render(960*9+1)
    assert seq.order==1 and seq.programs.voices[0].arp_override is False
    seq.render(960*9)
    assert seq.loops==1 and seq.programs.voices[0].arp_override is None


@pytest.mark.parametrize('clock',['PAL','NTSC'])
@pytest.mark.parametrize('squeeze',[False,True])
def test_exported_sid_executes_arp_automation_with_existing_effects(clock,squeeze):
    song=automation_song();song.clock=clock;before=deepcopy(song)
    result=compile_song(song,squeeze=squeeze)
    cpu,mem=machine(result.data)
    for tick,(expected,tempo) in enumerate(trace_song(song)):
        mem.events=[];call(cpu,0x1000 if tick==0 else 0x1003)
        assert (mem.events[25:] if tick==0 else mem.events)==expected
    assert song==before


def test_pcm_pitch_and_digi_export_obey_row_arp_commands():
    from sidpulse.audio.samples import SamplePrograms
    from sidpulse.export.pcm import compile_pcm, record_pcm
    song=pcm_song(rate=4000);song.export_config['loop']=False
    song.instruments[1].arpeggio=[12]
    song.patterns[0].rows=[
        [Cell(),Cell(),Cell(48,1,arp_mode=0)],
        [Cell(),Cell(),Cell(48,1,arp_mode=1)],
        [Cell(),Cell(),Cell(48,1,arp_mode=-1)],
    ]
    sid=SilentSID();p=SamplePrograms(sid,samples=song.samples)
    for mode,ratio in ((0,1),(1,2),(-1,2)):
        p.row(2,Cell(48,1,arp_mode=mode),song.instruments[1],1);p.tick(0)
        assert p.pcm[2]['step']==pytest.approx(4000/48000*ratio,rel=.001)
    before=deepcopy(song);records=record_pcm(song)
    result=compile_pcm(song,kind='prg')
    assert result.squeeze_report.verified_calls>0 and song==before
    # The first baked one-shot differs at normal versus octave-up playback;
    # the compiler's instruction-level verifier checks its exact nibble stream.
    segments=[value for record in records[0] for register,value in record[2] if register==30]
    assert bytes().join(segments[0])!=bytes().join(segments[1])
    assert bytes().join(segments[1])==bytes().join(segments[2])


def test_arp_schema_validation_roundtrip_and_older_save_format(tmp_path):
    song=automation_song()
    assert encode(song)['format_version']==9
    assert load(save(tmp_path/'arp.sidpulse',song))[0]==song
    assert encode(Song())['format_version']==6
    assert encode(pcm_song())['format_version']==8
    for invalid in (True,False,2,-2,'1',1.0):
        raw=encode(song);raw['song']['patterns'][0]['rows'][0][0]['arp_mode']=invalid
        with pytest.raises(ProjectError,match='arpeggio mode'):decode(raw)


def test_arp_field_entry_clipboard_and_undo_preserve_other_commands():
    ed=Editor(automation_song());before=deepcopy(ed.song)
    ed.column=4
    for char,value in [('0',0),('1',1),('R',-1)]:
        row=ed.row;ed.enter_digit(char)
        assert ed.pattern.rows[row][0]==replace(before.patterns[0].rows[row][0],arp_mode=value)
    ed.select_field(0,4);ed.copy();ed.voice=2;ed.row=0
    ed.paste(scope='automation')
    assert [row[2].arp_mode for row in ed.pattern.rows]==[0,1,-1]
    assert [row[2].note for row in ed.pattern.rows]==[row[2].note for row in before.patterns[0].rows]
    for _ in range(4):ed.history.undo(ed.song)
    assert ed.song==before


@pytest.mark.parametrize('size',[(640,480),(960,1080),(1280,900)])
def test_arp_button_and_keyboard_use_spare_column_without_overwriting_fx(size):
    app=App(automation_song(),audio=False,size=size)
    try:
        before=deepcopy(app.editor.song)
        click(app,'pattern_arpeggio',0)
        app.renderer.render(app)
        assert all(app.screen.get_rect().contains(r) for r,a,v in app.renderer.hits if a=='dialog_button')
        key(app,pg.K_RETURN)  # Cancel by default
        assert app.editor.song==before
        click(app,'pattern_arpeggio',0);click(app,'dialog_button',pg.K_0)
        assert app.editor.cell==replace(before.patterns[0].rows[0][0],arp_mode=0)
        assert app.editor.row==0 and app.editor.song.instruments==before.instruments
        app.editor.column=4
        app.handle(pg.event.Event(pg.KEYDOWN,key=pg.K_r,unicode='r',scancode=21,mod=0))
        assert app.editor.pattern.rows[0][0].arp_mode==-1
        app.editor.row=0
        app.handle(pg.event.Event(pg.KEYDOWN,key=pg.K_PERIOD,unicode='.',scancode=55,mod=0))
        assert app.editor.pattern.rows[0][0].arp_mode is None
    finally:app.close()
