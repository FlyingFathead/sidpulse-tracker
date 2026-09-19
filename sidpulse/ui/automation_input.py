"""Input shared by the inline recorder and the legacy recording window."""
import pygame as pg
from sidpulse.playback.automation_parameters import PARAMETERS
from sidpulse.ui.keyboard import Command
from sidpulse.ui.pressable import begin


def state(app):
    if app.dialog and app.dialog.get('kind') == 'automation_recording':return app.dialog
    return app.automation_state


def activate(app, action, value=None, pos=None):
    current=state(app)
    if action=='automation_parameter_step':
        fields=list(PARAMETERS)
        app.set_recording_parameter(fields[(fields.index(app.automation_parameter)+value)%len(fields)])
    elif action=='automation_parameter':current['parameter_choices']=not current.get('parameter_choices',False)
    elif action=='automation_parameter_pick':
        app.set_recording_parameter(value);current['parameter_choices']=False
    elif action=='automation_channel_step':app.set_recording_channel((app.pulse_record_voice+value)%3)
    elif action=='automation_channel_select':current['channel_choices']=not current.get('channel_choices',False)
    elif action=='automation_channel':
        app.set_recording_channel(value);current['channel_choices']=False
    elif action=='automation_arm':app.toggle_pulse_recording()
    elif action=='automation_close':app.close_automation_recording()
    elif action=='automation_transport':
        if value=='stop':app.panic()
        else:app.start_playback(value)
    elif action=='automation_slider':
        app.pulse_record_value=app.pulse_slider_value(value,pos)
        app.begin_pulse_drag(value,pos)


def focus_action(app, action):
    current=state(app);targets=current.get('targets',[])
    if action.startswith('automation_parameter'):action='automation_parameter'
    elif action.startswith('automation_channel') and app.inline_recording_visible:action='automation_channel_select'
    for i,(name,_) in enumerate(targets):
        if name==action:current['focus']=i;break
    if app.inline_recording_visible:app.instrument_focus='automation'


def focused(app):
    current=state(app);targets=current.get('targets',[])
    return targets[current.get('focus',0)%len(targets)] if targets else (None,None)


def handle_event(app,event):
    legacy=bool(app.dialog and app.dialog.get('kind')=='automation_recording')
    current=state(app)
    if event.type==pg.MOUSEBUTTONDOWN and event.button==1:
        for rect,action,value in reversed(app.renderer.hits):
            if action.startswith('automation_') and rect.collidepoint(event.pos):
                focus_action(app,action)
                if action=='automation_slider':activate(app,action,value,event.pos)
                else:begin(app,rect,Command('automation_control',(action,value)),event.pos)
                return True
        return legacy
    if event.type==pg.KEYUP and event.key in (pg.K_LEFT,pg.K_RIGHT):
        held=app.automation_state.setdefault('slider_keys',set())
        was_held=event.key in held
        held.discard(event.key)
        if not held:app.automation_state['keyboard_touch']=False
        drag=app.instrument_drag
        if drag and drag.get('keyboard'):
            drag.setdefault('keys',set()).discard(event.key)
            if not drag['keys']:app.finish_pulse_drag()
            return True
        if was_held:return True
    if event.type!=pg.KEYDOWN:return False
    if not legacy and app.instrument_focus!='automation':return False
    action,value=focused(app)
    if event.key==pg.K_ESCAPE:
        if current.get('parameter_choices') or current.get('channel_choices'):
            current['parameter_choices']=current['channel_choices']=False
        else:app.close_automation_recording()
    elif event.key in (pg.K_1,pg.K_2,pg.K_3) and not event.mod&(pg.KMOD_CTRL|pg.KMOD_ALT):
        app.set_recording_channel(event.key-pg.K_1)
    elif event.key in (pg.K_LEFT,pg.K_RIGHT):
        direction=-1 if event.key==pg.K_LEFT else 1
        if action=='automation_slider':
            held=app.automation_state.setdefault('slider_keys',set())
            held.add(event.key)
            if app.automation_state.get('keyboard_touch') and not (app.instrument_drag and app.instrument_drag.get('keyboard')):
                return True  # A completed/cancelled pattern pass waits for key release.
            step=(1 if event.mod&pg.KMOD_CTRL else 256 if event.mod&pg.KMOD_SHIFT else 16) if app.recording_info[2]==4095 else (4 if event.mod&pg.KMOD_SHIFT else 1)
            app.adjust_recording_value(direction*step)
            if app.instrument_drag and app.instrument_drag.get('keyboard'):
                app.instrument_drag.setdefault('keys',set()).add(event.key)
                app.automation_state['keyboard_touch']=True
        elif action=='automation_parameter':activate(app,'automation_parameter_step',direction)
        elif action in ('automation_channel_select','automation_channel'):activate(app,'automation_channel_step',direction)
    elif event.key==pg.K_SPACE:app.toggle_pulse_recording()
    elif event.key in (pg.K_F5,pg.K_F6,pg.K_F8):
        activate(app,'automation_transport',{pg.K_F5:'song',pg.K_F6:'pattern',pg.K_F8:'stop'}[event.key])
    elif event.key==pg.K_TAB:
        next_focus=current.get('focus',0)+(-1 if event.mod&pg.KMOD_SHIFT else 1)
        targets=current.get('targets',[])
        if targets:
            if not legacy and not 0<=next_focus<len(targets):
                app.instrument_focus='buttons' if next_focus<0 else 'list'
            current['focus']=next_focus%len(targets)
    elif event.key in (pg.K_RETURN,pg.K_KP_ENTER):
        if action and action!='automation_slider':activate(app,action,value)
    else:
        # Keep ordinary tracker transport/save/page shortcuts available.
        if legacy:
            from sidpulse.ui.keyboard import dispatch
            command=dispatch(event,app.page,app.editor.column,app.keyboard_mapping)
            if command and command.name in ('quick_save','save','save_as','undo','redo','panic','pause','quit'):
                app.execute(command,event)
            return True
        return bool(not event.mod&(pg.KMOD_CTRL|pg.KMOD_ALT) and event.key<pg.K_F1)
    return True
