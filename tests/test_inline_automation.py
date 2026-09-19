from copy import deepcopy
from dataclasses import replace
import pygame as pg
import pytest
from sidpulse.app import App
from sidpulse.preferences import load_automation_display,save_preferences
from sidpulse.playback.automation_parameters import PARAMETERS
from sidpulse.ui.keyboard import Command
from sidpulse.ui.themes import palette


def key(app,code,mod=0,up=False):
    app.handle(pg.event.Event(pg.KEYUP if up else pg.KEYDOWN,key=code,mod=mod,unicode='',scancode=0))


def click(app,action,value=None):
    app.renderer.render(app)
    rect=next(r for r,a,v in app.renderer.hits if a==action and v==value)
    app.handle(pg.event.Event(pg.MOUSEBUTTONDOWN,button=1,pos=rect.center))
    app.handle(pg.event.Event(pg.MOUSEBUTTONUP,button=1,pos=rect.center))


@pytest.mark.parametrize('saved',[None,0,3,True,'1',{},[]])
def test_new_or_invalid_display_preference_uses_inline(saved):
    save_preferences({'automation_display':saved})
    assert load_automation_display()==2


def test_inline_default_and_legacy_option_survive_preferences_and_reset():
    app=App(audio=False)
    try:
        app.open_automation_recording()
        assert app.automation_display==2 and app.inline_recording_visible and app.dialog is None
        app.close_automation_recording()
        app.execute(Command('automation_display_toggle'));assert load_automation_display()==1
        app.open_automation_recording();assert app.dialog['kind']=='automation_recording'
        from sidpulse.ui.settings_reset import commit
        commit(app);assert app.automation_display==load_automation_display()==2
    finally:app.close()


def test_inline_selectors_click_arrows_and_keyboard_change_only_the_recording_controls(monkeypatch):
    app=App(audio=False,size=(960,1080))
    try:
        before=deepcopy(app.editor.song)
        app.open_automation_recording();app.renderer.render(app)
        assert app.automation_parameter=='pulse_width' and app.pulse_record_voice==0
        assert any(a=='choose_instrument' for _,a,_ in app.renderer.hits)
        click(app,'automation_parameter_step',1);assert app.automation_parameter=='attack'
        click(app,'automation_parameter');click(app,'automation_parameter_pick','release')
        click(app,'automation_channel_step',-1);assert app.pulse_record_voice==2
        click(app,'automation_channel_select');click(app,'automation_channel',1)
        assert app.automation_parameter=='release' and app.pulse_record_voice==1
        app.automation_state['focus']=3
        key(app,pg.K_RIGHT);key(app,pg.K_RIGHT,up=True)
        assert app.pulse_record_value==9
        key(app,pg.K_LEFT,pg.KMOD_SHIFT);key(app,pg.K_LEFT,up=True)
        assert app.pulse_record_value==5
        click(app,'automation_parameter');click(app,'automation_parameter_pick','pulse_width')
        app.automation_state['focus']=3
        key(app,pg.K_RIGHT,pg.KMOD_CTRL);key(app,pg.K_RIGHT,up=True)
        assert app.pulse_record_value==0x801
        assert app.editor.song==before and app.pulse_take is None and app.dialog is None
        # Clicking another bank row remains available while the pane is open.
        click(app,'choose_instrument',2)
        assert app.instrument_slot==2 and app.inline_recording_visible and app.instrument_focus=='list'
        assert app.automation_parameter=='pulse_width' and app.pulse_record_voice==1
    finally:app.close()


@pytest.mark.parametrize('size',[(960,1080),(960,540),(480,360),(640,360)])
@pytest.mark.parametrize('zoom',[1.,2.,3.])
def test_inline_blue_slider_fits_with_empty_instrument_and_custom_color(size,zoom):
    save_preferences({'colors':{'rec_slider':'#168bcf'}})
    app=App(audio=False,size=size,zoom=zoom)
    try:
        app.change_page('instrument');app.select_instrument_slot(number=50)
        app.open_automation_recording();app.toggle_pulse_recording();app.renderer.render(app)
        for rect,action,_ in app.renderer.hits:
            if action.startswith('automation_'):
                assert app.screen.get_rect().contains(rect),action
                assert rect.bottom<=(app.renderer.lines-app.renderer.footer_rows)*app.renderer.rh,action
        rect=next(r for r,a,_ in app.renderer.hits if a=='automation_slider')
        assert bytes((22,139,207)) in pg.image.tobytes(app.screen.subsurface(rect),'RGB')
        assert palette(app.appearance)['REC_SLIDER'] != palette(app.appearance)['SLIDER']
        assert app.dialog is None and app.instrument_slot==50
    finally:app.close()


def test_keyboard_repeat_is_one_gesture_and_mouse_motion_cannot_change_its_value(monkeypatch):
    app=App(audio=False)
    try:
        app.open_automation_recording();app.toggle_pulse_recording();app.renderer.render(app)
        app.audio.ready=True;app.audio.playback=replace(app.audio.playback,status='playing')
        sent=[];monkeypatch.setattr(app.audio,'send',lambda *args:sent.append(args))
        key(app,pg.K_RIGHT);key(app,pg.K_RIGHT)
        assert app.pulse_take['value']==0x820 and not app.pulse_take['pending']
        app.handle(pg.event.Event(pg.MOUSEMOTION,pos=(0,0),buttons=(0,0,0),rel=(0,0)))
        assert app.pulse_take['value']==0x820
        key(app,pg.K_RIGHT,up=True)
        assert app.pulse_take['pending']
        assert [x[0] for x in sent].count('pulse_record_start')==1
        assert [x[0] for x in sent].count('pulse_record_end')==1
    finally:app.close()


def test_start_song_keeps_inline_controls_visible(monkeypatch):
    app=App(audio=False)
    try:
        app.open_automation_recording();app.audio.ready=True
        monkeypatch.setattr(app.audio,'send',lambda *args:None)
        key(app,pg.K_F5)
        assert app.inline_recording_visible and app.dialog is None
        app.audio.playback=replace(app.audio.playback,status='playing')
        key(app,pg.K_F5);assert app.inline_recording_visible
    finally:app.close()


def test_unarmed_slider_tracks_drag_without_changing_song_and_bank_right_focuses_it():
    app=App(audio=False)
    try:
        before=deepcopy(app.editor.song)
        app.open_automation_recording();app.renderer.render(app)
        rect=next(r for r,a,_ in app.renderer.hits if a=='automation_slider')
        app.handle(pg.event.Event(pg.MOUSEBUTTONDOWN,button=1,pos=rect.center))
        app.handle(pg.event.Event(pg.MOUSEMOTION,pos=rect.topright,buttons=(1,0,0),rel=(1,0)))
        app.handle(pg.event.Event(pg.MOUSEBUTTONUP,button=1,pos=rect.topright))
        assert app.pulse_record_value==4095 and app.pulse_take is None
        assert app.instrument_drag is None and app.editor.song==before
        app.instrument_focus='list';key(app,pg.K_RIGHT)
        assert app.instrument_focus=='automation'
        key(app,pg.K_TAB)
        assert app.instrument_focus=='list'
    finally:app.close()


def test_legacy_unarmed_drag_renders_without_treating_it_as_an_instrument_edit():
    app=App(audio=False)
    try:
        app.change_page('instrument');app.automation_display=1
        app.open_automation_recording();app.renderer.render(app)
        rect=next(r for r,a,_ in app.renderer.hits if a=='automation_slider')
        app.handle(pg.event.Event(pg.MOUSEBUTTONDOWN,button=1,pos=rect.center))
        app.renderer.render(app)
        assert 'recording PW' in app.renderer.context_status(app)
        app.handle(pg.event.Event(pg.MOUSEBUTTONUP,button=1,pos=rect.center))
        assert app.instrument_drag is None and app.pulse_take is None
    finally:app.close()


def test_key_hold_cannot_start_a_second_take_after_pattern_pass_finishes(monkeypatch):
    from sidpulse.playback.pulse_recording import PulseSnapshot
    app=App(audio=False)
    try:
        app.open_automation_recording();app.toggle_pulse_recording();app.renderer.render(app)
        app.audio.ready=True;app.audio.playback=replace(app.audio.playback,status='playing')
        sent=[];monkeypatch.setattr(app.audio,'send',lambda *args:sent.append(args))
        key(app,pg.K_RIGHT)
        first=app.pulse_record_serial
        app.audio.pulse_capture=PulseSnapshot(first,app.editor.pattern_id,0,((0,0x810),),done=True,reason='Pattern pass complete')
        app.sync_pulse_recording()
        assert app.pulse_take is None and app.instrument_drag is None
        key(app,pg.K_RIGHT);key(app,pg.K_RIGHT)
        assert app.pulse_record_serial==first and app.pulse_take is None
        key(app,pg.K_RIGHT,up=True);key(app,pg.K_RIGHT)
        assert app.pulse_record_serial==first+1
    finally:app.close()
