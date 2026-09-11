from copy import deepcopy
from array import array
import struct
import time
import pygame as pg
import pytest

from sidpulse.app import App
from sidpulse.audio.engine import AudioEngine
from sidpulse.playback.sequencer import Sequencer
from sidpulse.export.psid import compile_song,RecordingSID
from sidpulse.project.format import encode,decode,validate
from sidpulse.song.model import Song,Instrument,Pattern,Cell,ControlCell,example_song
from sidpulse.song.presets import available_presets
from sidpulse.sid.backend_residfp import ReSIDfpBackend,frequency,CLOCKS,set_filter,note_on
from test_psid import machine,call
from test_playback import TraceSID,wait_until


def key(app,k,scan=0,mod=0,up=False):
    app.handle(pg.event.Event(pg.KEYUP if up else pg.KEYDOWN,key=k,scancode=scan,mod=mod,unicode=''))


def click(app,action,value=None):
    app.renderer.render(app)
    rect=next(r for r,a,v in app.renderer.hits if a==action and (value is None or v==value))
    app.handle(pg.event.Event(pg.MOUSEBUTTONDOWN,button=1,pos=rect.center))
    app.handle(pg.event.Event(pg.MOUSEBUTTONUP,button=1,pos=rect.center))


@pytest.fixture
def app():
    result=App(example_song(),audio=False)
    result.change_page('instrument')
    yield result
    result.close()


@pytest.mark.parametrize('slot', [5, 8, 16, 18, 99])
def test_empty_slot_hover_click_resize_and_creation(monkeypatch, slot):
    tracker = App(Song(), audio=False)
    try:
        tracker.change_page('instrument')
        before = deepcopy(tracker.editor.song)
        tracker.select_instrument_slot(number=slot)
        tracker.renderer.render(tracker)
        rect = next(r for r, a, v in tracker.renderer.hits
                    if a == 'choose_instrument' and v == slot)
        monkeypatch.setattr(pg.mouse, 'get_pos', lambda: rect.center)
        tracker.renderer.render(tracker)
        click(tracker, 'choose_instrument', slot)
        for size in [(1440, 1050), (980, 780), (480, 360), (1280, 960)]:
            tracker.handle(pg.event.Event(pg.VIDEORESIZE, w=size[0], h=size[1], size=size))
            tracker.renderer.render(tracker)
        assert tracker.editor.song == before
        assert slot not in tracker.editor.song.instruments
        key(tracker, pg.K_RETURN)
        tracker.renderer.render(tracker)
        assert tracker.dialog['target_slot'] == slot
        click(tracker, 'new_choice', 1)
        tracker.renderer.render(tracker)
        assert tracker.editor.instrument == slot
        assert slot in tracker.editor.song.instruments
    finally:
        tracker.close()


def test_button_focus_keyboard_and_mouse_reach_each_tab(app):
    key(app,pg.K_TAB)
    assert app.instrument_focus=='buttons'
    key(app,pg.K_RIGHT);key(app,pg.K_RETURN)
    assert app.instrument_tab=='motion' and app.property_index==9
    click(app,'instrument_tab','adsr')
    assert app.instrument_tab=='adsr'
    click(app,'instrument_tab','roll')
    assert app.instrument_tab=='roll'
    key(app,pg.K_TAB,mod=pg.KMOD_SHIFT)
    assert app.instrument_focus=='buttons'


def test_bank_add_delete_default_cancel_and_undo_references(app):
    before=deepcopy(app.editor.song)
    click(app,'add_instrument');click(app,'new_choice',1)
    assert app.editor.instrument==10 and len(app.editor.song.instruments)==10
    app.editor.history.undo(app.editor.song);app.editor.repair_cursor()
    assert app.editor.song==before
    app.select_instrument_slot(number=1);app.instrument_focus='list'
    key(app,pg.K_DELETE)
    assert app.dialog['confirm_selected'] is False and 'references' in app.dialog['message']
    key(app,pg.K_RETURN)
    assert app.dialog is None and app.editor.song==before
    click(app,'delete_instrument')
    click(app,'confirm_instrument',True)
    assert 1 not in app.editor.song.instruments
    assert not any(c.instrument==1 for p in app.editor.song.patterns.values() for row in p.rows for c in row)
    validate(app.editor.song)
    app.editor.history.undo(app.editor.song)
    assert app.editor.song==before


def test_presets_include_first_light_are_independent_and_undoable(app):
    presets=available_presets()
    assert [p for _,p in presets[:9]]==list(example_song().instruments.values())
    before=deepcopy(app.editor.song)
    click(app,'choose_presets')
    app.dialog['preset_index']=next(i for i,(_,p) in enumerate(app.dialog['presets']) if p.name=='Rubber saw bass')
    key(app,pg.K_RETURN)
    assert app.editor.instrument==10
    assert app.editor.song.instruments[10]==presets[1][1]
    app.editor.history.undo(app.editor.song)
    assert app.editor.song==before
    app.editor.history.redo(app.editor.song)
    app.editor.song.instruments[10].arpeggio.append(12)
    assert app.editor.song.instruments[2].arpeggio==[] and available_presets()[1][1].arpeggio==[]


@pytest.mark.parametrize('tab,field,maximum',[('general','pulse_width',4095),('motion','pulse_depth',2047),('motion','vibrato_speed',15),('motion','retrigger',255),('adsr','attack',15),('adsr','decay',15),('adsr','sustain',15),('adsr','release',15)])
def test_numeric_slider_drag_is_bounded_and_one_undo(app,tab,field,maximum):
    from sidpulse.ui.instruments import FIELDS
    app.choose_instrument_tab(tab);app.property_index=FIELDS.index(field)
    app.renderer.render(app)
    rect,data=next((r,d) for r,a,d in app.renderer.hits if a=='graph_drag' and d['kind']=='slider' and d['field']==field)
    before=deepcopy(app.editor.song);undo=len(app.editor.history.undo_stack)
    app.handle(pg.event.Event(pg.MOUSEBUTTONDOWN,button=1,pos=(rect.left,rect.centery)))
    app.handle(pg.event.Event(pg.MOUSEMOTION,pos=(rect.centerx,rect.centery),buttons=(1,0,0),rel=(10,0)))
    app.handle(pg.event.Event(pg.MOUSEBUTTONUP,button=1,pos=(rect.right+100,rect.centery)))
    assert getattr(app.editor.song.instruments[1],field)==maximum
    assert len(app.editor.history.undo_stack)==undo+1
    app.editor.history.undo(app.editor.song)
    assert app.editor.song==before


def test_envelope_handle_changes_decay_and_sustain_and_roundtrips(app):
    app.choose_instrument_tab('adsr');app.renderer.render(app)
    rect,data=next((r,d) for r,a,d in app.renderer.hits if a=='graph_drag' and d['kind']=='envelope' and d['field']=='decay')
    graph=data['rect'];before=deepcopy(app.editor.song)
    app.handle(pg.event.Event(pg.MOUSEBUTTONDOWN,button=1,pos=rect.center))
    pos=(round(graph.x+.52*graph.width),round(graph.y+.8*graph.height))
    app.handle(pg.event.Event(pg.MOUSEBUTTONUP,button=1,pos=pos))
    inst=app.editor.song.instruments[1]
    assert inst.decay==15 and inst.sustain==3
    assert decode(encode(app.editor.song))[0]==app.editor.song
    app.editor.history.undo(app.editor.song);assert app.editor.song==before


def test_roll_draw_interpolates_missing_mouse_samples_and_undo(app):
    app.choose_instrument_tab('roll');app.graph_low=0
    app.editor.song.instruments[1].arpeggio=[]
    before=deepcopy(app.editor.song);app.renderer.render(app)
    rect,data=next((r,d) for r,a,d in app.renderer.hits if a=='graph_drag' and d['kind']=='roll')
    def pos(step,pitch):return (round(rect.x+(step+.5)*rect.width/16),round(rect.y+(24-pitch+.5)*rect.height/25))
    app.handle(pg.event.Event(pg.MOUSEBUTTONDOWN,button=1,pos=pos(0,0)))
    app.handle(pg.event.Event(pg.MOUSEMOTION,pos=pos(4,12),buttons=(1,0,0),rel=(20,0)))
    app.handle(pg.event.Event(pg.MOUSEBUTTONUP,button=1,pos=pos(4,12)))
    assert app.editor.song.instruments[1].arpeggio==[0,3,6,9,12]
    app.editor.history.undo(app.editor.song);assert app.editor.song==before
    app.editor.history.redo(app.editor.song)
    key(app,pg.K_DELETE);assert app.editor.song.instruments[1].arpeggio==[0,3,6,9]


def test_ctrl_q_buttons_cancel_by_default_and_mouse_discard(app):
    app.editor.edit('Rename',[(('title',),'Unsaved tune')])
    key(app,pg.K_q,20,pg.KMOD_CTRL)
    app.renderer.render(app)
    assert len([h for h in app.renderer.hits if h[1]=='dialog_button'])==3
    key(app,pg.K_RETURN)
    assert app.running and app.dialog is None
    key(app,pg.K_q,20,pg.KMOD_CTRL)
    click(app,'dialog_button',pg.K_d)
    assert not app.running


@pytest.mark.parametrize('clock',['PAL','NTSC'])
def test_clock_preserves_pitch_and_tempo_in_native_and_psid(clock):
    song=Song(clock=clock,speed=2,tempo=150,export_config={'loop':False})
    song.instruments={1:Instrument(waveform=0x10,attack=0,decay=0,sustain=15,release=0)}
    song.patterns={0:Pattern(rows=[[Cell(57,1),Cell(),Cell()]])}
    sid=ReSIDfpBackend(clock=clock);seq=Sequencer(sid);seq.start(song)
    pcm=seq.render(1600)
    assert seq.status=='stopped' and seq.frames==1600
    assert max(array('h',pcm))!=min(array('h',pcm))
    register=frequency(57,CLOCKS[clock])
    assert abs(register*CLOCKS[clock]/2**24-440)<.04
    assert sid.registers[0]|sid.registers[1]<<8==register
    data=compile_song(song).data;cpu,mem=machine(data);call(cpu,0x1000)
    flags=int.from_bytes(data[118:120],'big')
    assert flags&12==(4 if clock=='PAL' else 8)
    assert mem[0xD400]|mem[0xD401]<<8==register
    assert mem[0xDC04]|mem[0xDC05]<<8==round(CLOCKS[clock]*2.5/150)-1
    assert decode(encode(song))[0]==song


def test_whole_song_loop_restarts_programs_filter_tempo_and_counter():
    song=Song(speed=1)
    song.patterns={0:Pattern(rows=[[Cell(48,1),Cell(),Cell()],[Cell(effect='T',parameter=150),Cell(),Cell()]],
                             controls={1:ControlCell(volume=0)})}
    sid=TraceSID();seq=Sequencer(sid);seq.start(song)
    seq.render(1760)
    assert seq.state.loops==1 and seq.order==0 and seq.row==0 and seq.tempo==125
    assert seq.frames==1760 and sid.registers[24]&15==15
    seq.render(1760)
    assert seq.loops==2
    seq.stop();assert seq.status=='stopped'


def test_loop_setting_updates_host_and_export_and_legacy_off_is_preserved(app):
    app.change_page('settings');app.property_index=15
    app.change_property(1)
    assert app.editor.song.export_config['loop'] is False
    raw=encode(app.editor.song);raw['format_version']=3
    assert decode(raw)[0].export_config['loop'] is False
    app.property_index=16;app.change_property(1)
    assert app.editor.song.clock=='NTSC'
    key(app,pg.K_RETURN);assert app.dialog['text']=='NTSC'


def test_audition_after_zero_volume_ending_and_live_slider_change():
    song=Song(speed=1,export_config={'loop':False})
    song.patterns={0:Pattern(rows=[[Cell(48,1),Cell(),Cell()]],controls={0:ControlCell(volume=0)})}
    audio=AudioEngine(song)
    try:
        wait_until(lambda:audio.ready or audio.error,4);assert audio.ready,audio.error
        audio.send('play',song,'song',0,0,None)
        wait_until(lambda:audio.playback.frames>=960,4)
        assert audio.playback.status=='stopped'
        audio.send('on','test',48,song.instruments[1],None,1)
        wait_until(lambda:audio.peak>.01,4)
        modified=deepcopy(song);modified.instruments[1].sustain=0;modified.instruments[1].decay=0
        audio.send('update_song',modified)
        wait_until(lambda:audio.peak<.002,4)
        audio.send('off','test')
    finally:audio.close()


def test_enter_opens_presets_and_manual_draft_is_cancel_safe(app):
    before=deepcopy(app.editor.song)
    key(app,pg.K_RETURN)
    assert app.dialog['mode']=='presets'
    key(app,pg.K_RIGHT)
    assert app.dialog['mode']=='manual'
    click(app,'edit_instrument_field',2)
    app.handle(pg.event.Event(pg.TEXTINPUT,text='B'))
    key(app,pg.K_RETURN)
    assert app.dialog['manual'].attack==11 and app.editor.song==before
    key(app,pg.K_LEFT);assert app.dialog['mode']=='presets'
    key(app,pg.K_RIGHT);assert app.dialog['manual'].attack==11
    click(app,'preset_add')
    assert app.editor.song.instruments[10].attack==11
    app.editor.history.undo(app.editor.song);app.editor.repair_cursor();assert app.editor.song==before
    app.select_instrument_slot(number=1);app.instrument_focus='list';key(app,pg.K_RETURN);key(app,pg.K_RIGHT)
    click(app,'edit_instrument_field',6);key(app,pg.K_ESCAPE)
    assert app.dialog['mode']=='manual'
    key(app,pg.K_ESCAPE);assert app.editor.song==before


def test_numeric_focus_keeps_note_keys_and_requires_value_click(app,monkeypatch):
    sent=[]
    monkeypatch.setattr(app.audio,'send',lambda *args:sent.append(args))
    app.choose_instrument_tab('adsr');app.property_index=2
    before=deepcopy(app.editor.song)
    app.handle(pg.event.Event(pg.KEYDOWN,key=pg.K_b,scancode=5,mod=0,unicode='b'))
    app.handle(pg.event.Event(pg.TEXTINPUT,text='b'))
    assert app.dialog is None and app.editor.song==before
    assert any(message[0]=='on' and message[1]==5 for message in sent)
    key(app,pg.K_RETURN);assert app.dialog is None
    click(app,'edit_instrument_field',5)
    app.handle(pg.event.Event(pg.TEXTINPUT,text='F'));key(app,pg.K_RETURN)
    assert app.editor.song.instruments[1].release==15


def test_themes_fonts_persist_and_about_close_button(app):
    from sidpulse.preferences import load_appearance,save_preferences
    before=deepcopy(app.editor.song)
    app.change_page('settings');app.property_index=17;click(app,'setting_edit',17)
    assert app.appearance['theme']=='Charcoal crimson'
    app.property_index=18;app.change_property(direct='19')
    assert load_appearance()['font_size']==19
    save_preferences({'colors':{'slider':'#991122','TEXT':'bad'}})
    app.appearance=load_appearance();app.renderer.render(app)
    assert app.renderer.slider_color==(153,17,34)
    assert app.editor.song==before
    app.dialog={'title':'About SIDpulse Tracker','logo':True}
    app.renderer.render(app)
    close=next(r for r,a,v in app.renderer.hits if a=='dialog_button' and v==pg.K_ESCAPE)
    assert app.screen.get_rect().contains(close)
    click(app,'dialog_button',pg.K_ESCAPE);assert app.dialog is None


def test_empty_slot_chooser_targets_slot_and_user_presets_persist(app):
    from sidpulse.song.presets import user_presets,built_in_catalog,CATEGORIES
    before=deepcopy(app.editor.song)
    app.select_instrument_slot(number=9);key(app,pg.K_DOWN)
    assert app.instrument_slot==10 and 10 not in app.editor.song.instruments
    key(app,pg.K_RETURN);assert app.dialog['mode']=='choice'
    click(app,'new_choice',1)
    assert app.editor.instrument==10 and len(app.editor.song.instruments)==10
    app.editor.song.instruments[10].name='My pulse ä'
    click(app,'save_user_preset')
    presets,errors=user_presets();assert not errors and presets[0][1].name=='My pulse ä'
    app.select_instrument_slot(number=27);app.instrument_focus='list'
    key(app,pg.K_RETURN);key(app,pg.K_RETURN)
    key(app,pg.K_TAB);key(app,pg.K_RIGHT);key(app,pg.K_RETURN)
    assert app.dialog['source']=='user'
    key(app,pg.K_TAB);key(app,pg.K_RETURN)
    assert app.editor.instrument==27 and app.editor.song.instruments[27].name=='My pulse ä'
    assert list(dict.fromkeys(c for c,_ in built_in_catalog()))==list(CATEGORIES)
    for _,preset in built_in_catalog():validate(Song(instruments={1:preset}))
    assert len(built_in_catalog())==39


def test_playing_still_allows_f2_note_edit_without_audition(app):
    from dataclasses import replace
    app.change_page('pattern')
    app.audio.playback=replace(app.audio.playback,status='playing')
    key(app,pg.K_z,29)
    assert app.editor.song.patterns[0].rows[0][0].note==48
    assert not app.held


def test_general_envelope_and_sliders_update_each_other(app):
    from sidpulse.ui.instrument_graphs import envelope_points
    app.choose_instrument_tab('general'); app.renderer.render(app)
    rect, data = next((r,d) for r,a,d in app.renderer.hits
                      if a=='graph_drag' and d['kind']=='envelope' and d['field']=='attack')
    graph = data['rect']
    inst = app.editor.song.instruments[1]
    before = deepcopy(app.editor.song)
    app.handle(pg.event.Event(pg.MOUSEBUTTONDOWN,button=1,pos=rect.center))
    app.handle(pg.event.Event(pg.MOUSEBUTTONUP,button=1,
                             pos=(round(graph.x+.26*graph.width),graph.top)))
    assert inst.attack == 15
    app.renderer.render(app)
    slider, data = next((r,d) for r,a,d in app.renderer.hits
                        if a=='graph_drag' and d['kind']=='slider' and d['field']=='attack')
    app.handle(pg.event.Event(pg.MOUSEBUTTONDOWN,button=1,pos=slider.midleft))
    app.handle(pg.event.Event(pg.MOUSEBUTTONUP,button=1,pos=slider.midleft))
    assert inst.attack == 0
    app.renderer.render(app)
    handle, data = next((r,d) for r,a,d in app.renderer.hits
                        if a=='graph_drag' and d['kind']=='envelope' and d['field']=='attack')
    expected = envelope_points(data['rect'],inst)[1]
    assert abs(handle.centerx-expected[0]) <= 1
    app.editor.history.undo(app.editor.song); assert app.editor.song.instruments[1].attack == 15
    app.editor.history.undo(app.editor.song); assert app.editor.song == before
