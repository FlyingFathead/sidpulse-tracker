from export_gui_helpers import finish_export_analysis
from copy import deepcopy
import pygame as pg
import pytest
from sidpulse.app import App
from sidpulse.song.model import Song,Instrument,Cell,Pattern,ControlCell,example_song
from sidpulse.playback.voices import VoicePrograms
from sidpulse.export.psid import RecordingSID
from sidpulse.sid.backend_residfp import frequency
from sidpulse.project.format import save,load,encode,decode,ProjectError


def freq(sid,v=0):return sid.registers[v*7]|sid.registers[v*7+1]<<8


def test_instrument_arp_and_pattern_arp_precedence_memory_and_wave_hold():
    sid=RecordingSID();v=VoicePrograms(sid)
    inst=Instrument(arpeggio=[0,4,7],wave_sequence=[128,16,64],pitch_sequence=[12,0])
    v.row(0,Cell(48,1),inst);v.tick(0)
    assert freq(sid)==pytest.approx(frequency(60),abs=1) and sid.registers[4]==129
    v.tick(1);assert freq(sid)==pytest.approx(frequency(52),abs=1) and sid.registers[4]==17
    v.tick(2);assert freq(sid)==pytest.approx(frequency(55),abs=1) and sid.registers[4]==65
    v.row(0,Cell(effect='J',parameter=0x37),inst)
    v.tick(0);assert freq(sid)==frequency(48)
    v.tick(1);assert freq(sid)==pytest.approx(frequency(51),abs=1)
    v.row(0,Cell(effect='J',parameter=0),inst);v.tick(2)
    assert freq(sid)==pytest.approx(frequency(55),abs=1)


def test_gate_delay_cut_retrigger_and_portamento_do_not_create_extra_voices():
    sid=RecordingSID();v=VoicePrograms(sid);inst=Instrument()
    v.row(0,Cell(48,1,'S',0xD2),inst)
    v.tick(0);v.tick(1);assert not sid.registers[4]&1
    v.tick(2);assert sid.registers[4]&1 and freq(sid)==frequency(48)
    v.row(0,Cell(60,1,'G',8),inst);sid.events=[]
    v.tick(0);assert freq(sid)==frequency(48)
    v.tick(1);assert freq(sid)==frequency(48)+32
    assert not any(r==4 for r,x in sid.events)
    v.row(0,Cell(effect='Q',parameter=2),inst);sid.events=[]
    v.tick(0);v.tick(1);assert not any(r==4 for r,x in sid.events)
    v.tick(2);assert [x&1 for r,x in sid.events if r==4]==[0,1]
    v.row(0,Cell(effect='S',parameter=0xC1),inst);v.tick(0);v.tick(1)
    assert sid.registers[4]==0


def test_sid_slides_vibrato_and_pulse_have_observable_bounded_changes():
    sid=RecordingSID();v=VoicePrograms(sid)
    inst=Instrument(pulse_width=800,pulse_depth=500,pulse_rate=4,vibrato_speed=4,vibrato_depth=6,gate_ticks=12)
    v.row(0,Cell(48,1,'F',2),inst);v.tick(0);initial=v.voices[0].freq
    values=[]
    for tick in range(1,13):
        v.tick(tick);values.append((freq(sid),sid.registers[2]|sid.registers[3]<<8))
    assert v.voices[0].freq==initial+12*8
    assert len({f for f,p in values})>8
    assert min(p for f,p in values)>=300 and max(p for f,p in values)==1300
    assert not sid.registers[4]&1
    v.row(0,Cell(effect='E',parameter=0xE2),inst)
    before=v.voices[0].freq;v.tick(0);v.tick(1)
    assert v.voices[0].freq==before-2


def test_v3_roundtrip_all_instrument_controls_notes_and_future_editor_data(tmp_path):
    song=example_song();song.comments+='\nÄäni\nStudio notes: keep this exact. 😀'
    song.instruments[1].macros={'future_extension':{'nested':[1,2,3]}}
    metadata={'unknown_editor':{'future_layout':['foo']},'zoom':1.5}
    path=save(tmp_path/'song.sidpulse',song,metadata)
    restored,meta=load(path)
    assert restored==song and meta==metadata
    assert encode(song)['format_version']==6
    raw=encode(Song());raw['format_version']=2
    for pat in raw['song']['patterns'].values():pat.pop('controls')
    for inst in raw['song']['instruments'].values():
        for key in ('arpeggio','arp_speed','wave_sequence','pitch_sequence','pulse_depth','pulse_rate','vibrato_speed','vibrato_depth','vibrato_delay','gate_ticks','retrigger'):inst.pop(key)
    old,_=decode(raw);assert old.instruments[1].arpeggio==[] and old.patterns[0].controls=={}
    raw['song']['patterns'][0]['surprise_notes']='must not vanish'
    restored, _ = decode(raw)
    assert encode(restored)['song']['patterns'][0]['surprise_notes'] == 'must not vanish'


def test_f4_program_edit_filter_shortcut_notes_and_native_save_export_workflow(tmp_path):
    app=App(example_song(),audio=False)
    def key(k,mod=0):app.handle(pg.event.Event(pg.KEYDOWN,key=k,scancode=0,mod=mod,unicode=''))
    try:
        app.change_page('instrument');app.instrument_focus='properties';key(pg.K_PAGEDOWN)
        assert app.property_index==9
        app.change_property(direct='0 3 7 10');assert app.editor.song.instruments[1].arpeggio==[0,3,7,10]
        key(pg.K_F2,pg.KMOD_CTRL|pg.KMOD_SHIFT);assert app.control_focus and app.page=='pattern'
        key(pg.K_RETURN);app.dialog['callback']('380 A 2 10 F -3');app.dialog=None
        assert app.editor.pattern.controls[0].cutoff==0x380
        assert app.editor.pattern.controls[0].slide==-3
        key(pg.K_TAB);assert not app.control_focus
        key(pg.K_F2,pg.KMOD_CTRL);assert app.dialog['title']=='Pattern length';app.dialog=None
        key(pg.K_F9,pg.KMOD_SHIFT);assert app.dialog['multiline']
        app.dialog['text']='First line';key(pg.K_RETURN,pg.KMOD_SHIFT)
        app.handle(pg.event.Event(pg.TEXTINPUT,text='Second line'));key(pg.K_RETURN)
        assert app.editor.song.comments=='First line\nSecond line'
        original=deepcopy(app.editor.song)
        key(pg.K_e,pg.KMOD_CTRL|pg.KMOD_SHIFT)
        assert app.dialog['kind']=='export_squeezer' and app.dialog['target']=='sid'
        assert app.dialog.get('busy') and app.dialog['result'] is None
        finish_export_analysis(app)
        assert 'error' not in app.dialog and app.dialog['result'] is not None
        assert app.dialog['source']==original
        assert app.dialog['options'].enabled and app.dialog['result'].squeeze_report.enabled
        key(pg.K_s);assert app.page=='files'
        app.file_name=str(tmp_path/'song.sidpulse');app.submit_file()
        assert app.path==tmp_path/'song.sidpulse' and not app.editor.dirty
        assert app.dialog is None and app.page=='files' and app.file_mode=='sid'
        app.file_name=str(tmp_path/'song.sid');app.submit_file()
        assert (tmp_path/'song.sid').read_bytes()[:4]==b'PSID'
        assert load(tmp_path/'song.sidpulse')[0]==original
        assert app.editor.song==original and not app.editor.dirty
    finally:app.close()


def test_resize_and_whole_pattern_row_operations_preserve_filter_alignment():
    from sidpulse.commands.editor import Editor
    song=Song();song.patterns[0].controls={0:ControlCell(cutoff=1),2:ControlCell(cutoff=2)}
    ed=Editor(song);ed.row=1;ed.insert_delete(entire=True)
    assert set(ed.pattern.controls)=={0,3}
    ed.insert_delete(delete=True,entire=True);assert set(ed.pattern.controls)=={0,2}
    ed.history.undo(ed.song);assert set(ed.pattern.controls)=={0,3}
