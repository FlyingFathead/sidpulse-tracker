from copy import deepcopy
from dataclasses import replace
import pygame as pg
import pytest
from sidpulse.app import App
from sidpulse.preferences import load_appearance, save_preferences
from sidpulse.song.model import Instrument
from sidpulse.ui.keyboard import Command
from sidpulse.ui.themes import palette


def click(app,action,value=None):
    app.renderer.render(app)
    if action=='automation_channel' and not any(a==action and v==value for _,a,v in app.renderer.hits):
        click(app,'automation_channel_select');app.renderer.render(app)
    rect=next(r for r,a,v in app.renderer.hits if a==action and (value is None or v==value))
    app.handle(pg.event.Event(pg.MOUSEBUTTONDOWN,button=1,pos=rect.center))
    app.handle(pg.event.Event(pg.MOUSEBUTTONUP,button=1,pos=rect.center))


@pytest.mark.parametrize('size',[(1920,1080),(960,540),(480,360)])
@pytest.mark.parametrize('display',[1,2])
def test_dedicated_channel_recorder_fits_and_has_only_one_armed_destination(size,display):
    app=App(audio=False,size=size)
    try:
        app.change_page('instrument');before=deepcopy(app.editor.song)
        app.renderer.render(app)
        assert any(a=='pulse_record_arm' for _,a,_ in app.renderer.hits)
        assert not any(a=='pulse_record_target' for _,a,_ in app.renderer.hits)
        app.automation_display=display;app.execute(Command('pulse_record_arm'))
        assert not app.pulse_record_armed
        if display==1:assert app.dialog['kind']=='automation_recording'
        else:assert app.dialog is None and app.inline_recording_visible
        click(app,'automation_channel',2);click(app,'automation_arm')
        assert app.pulse_record_armed and app.pulse_record_voice==2
        app.renderer.render(app)
        arm=next(r for r,a,_ in app.renderer.hits if a=='automation_arm')
        assert bytes(palette(app.appearance)['REC_ARM']) in pg.image.tobytes(app.screen.subsurface(arm),'RGB')
        assert all(app.screen.get_rect().contains(r) for r,a,_ in app.renderer.hits if a.startswith('automation_'))
        click(app,'automation_channel',0)
        assert app.pulse_record_voice==0 and app.pulse_record_armed
        if display==1:click(app,'automation_close')
        else:app.close_automation_recording()
        for page in ('pattern','info'):
            app.change_page(page);app.renderer.render(app)
            labels=[];original=app.renderer.text;control=app.renderer.control_text
            app.renderer.text=lambda x,y,value,*args:labels.append(str(value))
            app.renderer.control_text=lambda rect,value,*args,**kw:labels.append(str(value))
            app.renderer.render(app)
            app.renderer.text=original;app.renderer.control_text=control
            assert sum(label.startswith('CH ') and '(A)' in label for label in labels)==1
        assert app.editor.song==before
    finally:app.close()


def test_record_arm_color_uses_saved_override_and_reset():
    from sidpulse.ui.settings_reset import commit
    save_preferences({'colors':{'rec_arm':'#285f91'}})
    app=App(audio=False)
    try:
        app.open_automation_recording();app.toggle_pulse_recording();app.renderer.render(app)
        rect=next(r for r,a,_ in app.renderer.hits if a=='automation_arm')
        assert bytes((40,95,145)) in pg.image.tobytes(app.screen.subsurface(rect),'RGB')
        assert app.appearance==load_appearance()
        commit(app);assert palette(app.appearance)['REC_ARM']==(181,50,66)
    finally:app.close()


def test_destination_is_independent_of_instrument_24_33_and_pattern_cursor(monkeypatch):
    app=App(audio=False)
    try:
        app.editor.song.instruments.update({24:Instrument(name='24'),33:Instrument(name='33')})
        app.change_page('instrument');app.select_instrument_slot(number=24)
        app.open_automation_recording();app.set_recording_channel(2);app.toggle_pulse_recording();app.dialog=None
        app.select_instrument_slot(number=33);app.editor.voice=0
        app.open_automation_recording();app.renderer.render(app)
        assert app.pulse_record_voice==2 and app.instrument_slot==app.editor.instrument==33
        before=deepcopy(app.editor.song)
        app.audio.ready=True;app.audio.playback=replace(app.audio.playback,status='playing')
        sent=[];monkeypatch.setattr(app.audio,'send',lambda *args:sent.append(args))
        rect,data=next((r,v) for r,a,v in app.renderer.hits if a=='automation_slider')
        app.begin_pulse_drag(data,rect.center)
        assert sent[-1][0]=='pulse_record_start' and sent[-1][2]==2
        app.set_recording_channel(0)
        assert app.pulse_record_voice==2 and app.pulse_take['voice']==2
        assert app.instrument_slot==33 and app.editor.song==before
        app.finish_pulse_drag(cancel=True)
        assert sent[-1][0]=='pulse_record_end' and sent[-1][2] is True
    finally:app.close()


def test_arming_alone_or_stopped_slider_never_edits_song():
    app=App(audio=False)
    try:
        before=deepcopy(app.editor.song)
        app.open_automation_recording();app.renderer.render(app)
        rect,data=next((r,v) for r,a,v in app.renderer.hits if a=='automation_slider')
        app.begin_pulse_drag(data,rect.center)
        assert app.pulse_take is None
        app.toggle_pulse_recording();app.begin_pulse_drag(data,rect.center)
        assert app.pulse_take is None and app.editor.song==before
        app.new_project();assert not app.pulse_record_armed
    finally:app.close()


@pytest.mark.parametrize('size',[(960,1080),(960,540),(480,360)])
@pytest.mark.parametrize('tab',['general','motion','adsr','roll'])
@pytest.mark.parametrize('slot',[1,50])
def test_main_bank_disarm_is_visible_on_every_tab_and_empty_slots(size,tab,slot):
    app=App(audio=False,size=size)
    try:
        app.change_page('instrument');app.select_instrument_slot(number=slot)
        app.instrument_tab=tab;app.set_recording_channel(2);app.toggle_pulse_recording()
        before=deepcopy(app.editor.song)
        app.renderer.render(app)
        rect=next(r for r,a,_ in app.renderer.hits if a=='pulse_record_disarm')
        assert app.screen.get_rect().contains(rect)
        assert bytes(palette(app.appearance)['REC_ARM']) in pg.image.tobytes(app.screen.subsurface(rect),'RGB')
        assert not any(rect.colliderect(r) for r,a,_ in app.renderer.hits if a=='choose_instrument')
        app.handle(pg.event.Event(pg.MOUSEBUTTONDOWN,button=1,pos=rect.center))
        assert app.button_press and app.pulse_record_armed
        app.renderer.render(app)
        app.handle(pg.event.Event(pg.MOUSEBUTTONUP,button=1,pos=rect.center))
        assert not app.pulse_record_armed and app.dialog is None
        assert app.pulse_record_voice==2 and app.instrument_slot==slot
        app.renderer.render(app)
        assert not any(a=='pulse_record_disarm' for _,a,_ in app.renderer.hits)
        assert app.editor.song==before and not app.editor.history.undo_stack
    finally:app.close()


def test_disarm_button_drag_away_cancels_and_keyboard_focus_can_activate():
    app=App(audio=False,size=(960,1080))
    try:
        app.change_page('instrument');app.toggle_pulse_recording();app.renderer.render(app)
        rect=next(r for r,a,_ in app.renderer.hits if a=='pulse_record_disarm')
        app.handle(pg.event.Event(pg.MOUSEBUTTONDOWN,button=1,pos=rect.center))
        app.handle(pg.event.Event(pg.MOUSEBUTTONUP,button=1,pos=(0,0)))
        assert app.pulse_record_armed
        app.instrument_focus='buttons'
        app.instrument_button=app.instrument_buttons().index(('pulse_record_disarm',None))
        app.handle(pg.event.Event(pg.KEYDOWN,key=pg.K_RETURN,mod=0,unicode='',scancode=0))
        assert not app.pulse_record_armed and app.dialog is None
    finally:app.close()
