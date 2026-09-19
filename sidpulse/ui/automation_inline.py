"""Recording display 2: controls inside F4, alongside the instrument bank."""
import pygame as pg
from sidpulse.playback.automation_parameters import PARAMETERS
from sidpulse.ui.instrument_graphs import button, slider_thumb
from sidpulse.ui.pressable import pressed
from sidpulse.ui.automation_input import focused


def draw(r,app,left,top,bottom):
    from sidpulse.ui.renderer import TEXT,YELLOW,REC_ARM,REC_SLIDER,DIM,SELECT
    state=app.automation_state
    width=r.cols-left-2
    parameter_width=max(22,width*.57)
    channel_x=left+parameter_width+1
    channel_width=width-parameter_width-1
    r.text(left,top,'Automate what',TEXT,parameter_width)
    r.text(channel_x,top,'On channel',TEXT,channel_width)
    y=top+1.2
    def control(x,y,w,label,action,value=None,selected=False,fill=None):
        button(r,x,y,w,label,action,value,
               selected=selected or pressed(app,'automation_control',(action,value)),fill=fill,height=1.1)
    if state.get('parameter_choices'):
        step=parameter_width/len(PARAMETERS)
        for i,(field,(_,code,_)) in enumerate(PARAMETERS.items()):
            control(left+i*step,y,step-.3,code,'automation_parameter_pick',field,field==app.automation_parameter)
    else:
        control(left,y,3,'◀','automation_parameter_step',-1)
        control(left+3.5,y,parameter_width-7,app.recording_info[0],'automation_parameter')
        control(left+parameter_width-3,y,3,'▶','automation_parameter_step',1)
    if state.get('channel_choices'):
        for voice in range(3):
            control(channel_x+voice*channel_width/3,y,channel_width/3-.3,str(voice+1),'automation_channel',voice,
                    voice==app.pulse_record_voice,REC_ARM if app.pulse_record_armed and voice==app.pulse_record_voice else None)
    else:
        control(channel_x,y,3,'◀','automation_channel_step',-1)
        control(channel_x+3.5,y,channel_width-7,f'CH {app.pulse_record_voice+1}','automation_channel_select',
                fill=REC_ARM if app.pulse_record_armed else None)
        control(channel_x+channel_width-3,y,3,'▶','automation_channel_step',1)
    maximum=app.recording_info[2];digits=3 if maximum==4095 else 1
    value=app.pulse_take['value'] if app.pulse_take else app.pulse_record_value
    y=top+2.7
    r.text(left,y,f'{app.recording_info[1]}  {value:0{digits}X}   (0..{maximum:X})',YELLOW,width-21)
    label='Disarm' if app.pulse_record_armed else 'Arm recording'
    control(left+width-20,y-.05,20,label,'automation_arm',selected=app.pulse_record_armed,
            fill=REC_ARM if app.pulse_record_armed else None)
    slider=r.well(left,top+4,width,1.2).inflate(-4,-5)
    pg.draw.rect(r.screen,REC_SLIDER,(slider.x,slider.y,round(slider.width*value/maximum),slider.height))
    slider_thumb(r,slider,value/maximum)
    r.hits.append((slider.inflate(0,6),'automation_slider',{'rect':slider,'kind':'slider','field':app.automation_parameter,'maximum':maximum}))
    state['targets']=[('automation_parameter',None),('automation_channel_select',None),('automation_arm',None),('automation_slider',None)]
    if app.instrument_focus=='automation':
        action,_=focused(app)
        for rect,name,_ in r.hits:
            if name==action:pg.draw.rect(r.screen,REC_SLIDER,rect.inflate(4,4),2)
    if top+6<bottom:
        r.text(left,top+5.7,'Arrows: adjust | Tab: select | F5/F6: play | F8: stop',DIM,width)
    if top+8<bottom:
        r.text(left,top+7,'Drag or hold an arrow key while armed and playing.',TEXT,width)
        r.text(left,top+8,'Release keeps the take. Esc during recording cancels.',TEXT,width)
