"""Real SDL GUI regressions. Skipped, not simulated, without pygame-ce."""
from copy import deepcopy
import pytest
pg=pytest.importorskip('pygame')
from sidpulse.app import App
from sidpulse.song.model import Song,Instrument,Cell
from sidpulse.audio.activity import ActivitySnapshot
from sidpulse.ui.keyboard import Command

@pytest.fixture
def app():
    s=Song();s.instruments[7]=Instrument('Played but not selected');s.samples={'7':{'name':'Sample 7'}}
    a=App(s,audio=False);yield a;a.close()


def click(a,action,value):
    a.renderer.render(a)
    rect=next(r for r,k,v in a.renderer.hits if (k,v)==(action,value))
    a.handle(pg.event.Event(pg.MOUSEBUTTONDOWN,button=1,pos=rect.center))
    a.handle(pg.event.Event(pg.MOUSEBUTTONUP,button=1,pos=rect.center))


def test_dot_uses_audio_slot_and_does_not_steal_row_click(app):
    app.audio.ready=True;app.audio.activity=ActivitySnapshot(1,True,(7,),((7,1),),(7,))
    app.change_page('instrument');app.instrument_slot=1;app.renderer.render(app)
    r=next(r for r,a,v in app.renderer.hits if a=='activity_indicator' and v==('instrument',7))
    color=app.screen.get_at(r.center)[:3];assert color[1]>180
    inactive=next(r for r,a,v in app.renderer.hits if a=='activity_indicator' and v==('instrument',1))
    assert app.screen.get_at(inactive.center)[:3]==(66,76,62)
    click(app,'activity_indicator',('instrument',7));assert app.instrument_slot==7
    app.change_page('samples');app.renderer.render(app)
    r=next(r for r,a,v in app.renderer.hits if a=='activity_indicator' and v==('sample',7))
    assert app.screen.get_at(r.center)[:3]==(66,76,62)


def test_audition_row_message_includes_source_id(app,monkeypatch):
    app.editor.pattern.rows[0][0]=Cell(48,7);app.editor.voice=0;app.editor.row=0
    calls=[];monkeypatch.setattr(app.audio,'send',lambda *args:calls.append(args))
    app.execute(Command('audition_cell'),pg.event.Event(pg.KEYDOWN,scancode=33))
    call=next(c for c in calls if c[0]=='on')
    assert call[-2:]==(0,7)


def test_attack_handle_reaches_left_edge_with_one_undo(app):
    app.change_page('instrument');app.choose_instrument_tab('adsr')
    app.editor.song.instruments[1].attack=8;before=deepcopy(app.editor.song)
    app.renderer.render(app)
    handle,data=next((r,v) for r,k,v in app.renderer.hits if k=='graph_drag' and v['kind']=='envelope' and v['field']=='attack')
    g=data['rect']
    app.handle(pg.event.Event(pg.MOUSEBUTTONDOWN,button=1,pos=handle.center))
    app.handle(pg.event.Event(pg.MOUSEBUTTONUP,button=1,pos=(g.left,g.top)))
    assert app.editor.song.instruments[1].attack==0
    app.renderer.render(app)
    handle,data=next((r,v) for r,k,v in app.renderer.hits if k=='graph_drag' and v['kind']=='envelope' and v['field']=='attack')
    assert abs(handle.centerx-data['rect'].left)<=1
    app.execute(Command('undo'));assert app.editor.song==before


def test_f11_loop_and_f12_are_same_flag_and_no_repeat_toggle(app):
    app.change_page('orders');flag=app.editor.song.export_config.get('loop',True)
    click(app,'song_loop',None);assert app.editor.song.export_config['loop']==(not flag)
    app.change_page('settings');app.property_index=15
    app.page_key(pg.event.Event(pg.KEYDOWN,key=pg.K_RETURN,mod=0));assert app.editor.song.export_config['loop']==flag
    app.change_page('orders')
    event=pg.event.Event(pg.KEYDOWN,key=pg.K_l,unicode='l',mod=0,scancode=15)
    for _ in range(4):app.handle(event)
    assert app.editor.song.export_config['loop']==(not flag)
    app.handle(pg.event.Event(pg.KEYUP,key=pg.K_l,mod=0,scancode=15));app.handle(event)
    assert app.editor.song.export_config['loop']==flag
