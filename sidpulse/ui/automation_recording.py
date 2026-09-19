"""Channel-owned PW touch recording, independent of the instrument editor."""
import pygame as pg
from sidpulse.ui.instrument_graphs import button, slider_thumb
from sidpulse.ui.automation_input import handle_event, activate


def draw(r, app):
    from sidpulse.ui.renderer import TEXT, CREAM, REC_ARM, DIM, YELLOW, SLIDER
    r.hits=[]
    shade=pg.Surface(r.screen.get_size(),pg.SRCALPHA);shade.fill((0,0,0,175));r.screen.blit(shade,(0,0))
    w=min(82,r.cols-4);height=20
    x=max(0,(r.cols-w)//2);y=max(0,(r.lines-height)//2)
    r.panel(x,y,w,height,'Record automation')
    r.text(x+2,y+2,f'Parameter: {app.recording_info[0]} ({app.recording_info[1]})',TEXT,w-4)
    width=(w-6)/3
    for voice in range(3):
        selected=app.pulse_record_voice==voice
        armed=selected and app.pulse_record_armed
        label=f'CH {voice+1}'+(' (A)' if armed else '')
        button(r,x+2+voice*(width+1),y+4,width,label,'automation_channel',voice,
               selected=selected,fill=REC_ARM if armed else None)
    label='RECORDING' if app.pulse_take else 'Armed (A)' if app.pulse_record_armed else 'Arm recording'
    button(r,x+2,y+6,20,label,'automation_arm',selected=app.pulse_record_armed,
           fill=REC_ARM if app.pulse_record_armed else None)
    r.text(x+24,y+6.1,f'CH {app.pulse_record_voice+1} / {app.recording_info[1]}',TEXT,w-26)
    value=app.pulse_take['value'] if app.pulse_take else app.pulse_record_value
    maximum=app.recording_info[2]
    r.text(x+2,y+8,f'{app.recording_info[1]} {value:X}   (0..{maximum:X})',YELLOW,w-4)
    slider=r.well(x+2,y+10,w-4,1.2).inflate(-4,-5)
    pg.draw.rect(r.screen,SLIDER,(slider.x,slider.y,round(slider.width*value/maximum),slider.height))
    slider_thumb(r,slider,value/maximum)
    r.hits.append((slider.inflate(0,8),'automation_slider',{'rect':slider,'kind':'slider','field':app.automation_parameter,'maximum':maximum}))
    r.text(x+2,y+12,'Arm, play, then drag. Release keeps one undoable take.',TEXT,w-4)
    r.text(x+2,y+13,'Records this channel, whichever instrument is playing.',DIM,w-4)
    for offset,width,label,action in ((2,12,'Song F5','song'),(15,15,'Pattern F6','pattern'),(31,12,'Stop F8','stop')):
        button(r,x+offset,y+15,width,label,'automation_transport',action)
    button(r,x+2,y+17,12,'Close','automation_close')
    r.text(x+16,y+17.1,app.audio.playback.status.title(),TEXT,w-18)
    r.text(x+2,y+19,'1/2/3: channel | Space: arm | Esc: cancel take / close',DIM,w-4)
    targets=[(a,None if a=='automation_slider' else v) for _,a,v in r.hits if a in ('automation_channel','automation_arm','automation_slider','automation_transport','automation_close')]
    app.dialog['targets']=targets
    if targets:
        focused=targets[app.dialog.get('focus',3)%len(targets)]
        for rect,action,value in r.hits:
            if (action,None if action=='automation_slider' else value)==focused:pg.draw.rect(r.screen,YELLOW,rect.inflate(-4,-4),1)
