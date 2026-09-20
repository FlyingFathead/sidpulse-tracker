"""Relative sample gain with a linked percentage slider and numeric field."""
import pygame as pg
from sidpulse.ui.instrument_graphs import button, slider_thumb
from sidpulse.ui.themes import palette


def open_dialog(app):
    from sidpulse.audio.media import sample_data
    sample = app.selected_sample()
    try:
        sample_data(sample)
    except ValueError as exc:
        app.notice('Select a sample', str(exc)); return
    app.release_audition()
    pg.key.stop_text_input()
    app.dialog = {'kind':'sample_volume', 'title':'Adjust sample volume',
                  'sample':sample, 'slot':app.sample_index, 'value':100,
                  'focus':0, 'editing':False, 'text':'', 'select_all':False, 'drag_rect':None}


def set_value(d, value):
    d['value'] = max(0,min(200,value))
    d['editing'] = False
    d.pop('error',None)
    pg.key.stop_text_input()


def update_text(d, text):
    d['text'] = text
    if text and 0 <= int(text) <= 200:
        d['value'] = int(text)
        d.pop('error',None)
    else:
        d['error'] = 'Use 0 to 200%.'


def accept_text(d):
    if d['editing'] and (not d['text'] or not 0 <= int(d['text']) <= 200):
        d['error'] = 'Use 0 to 200%.'
        return False
    d['editing'] = False
    d.pop('error',None)
    pg.key.stop_text_input()
    return True


def activate(app, action):
    d = app.dialog
    if action == 'cancel':
        pg.key.stop_text_input()
        app.dialog = None
    elif action == 'ok' and accept_text(d):
        app.dialog = None
        if d['value'] == 100:
            app.editor.status = 'Sample volume unchanged (100%).'
            return
        app._start_media_job(d['sample'], {'operation':'volume', 'percent':d['value']},
                             assignment={'slot':d['slot'], 'instrument':None, 'operation':'Adjust volume'})


def slide(d, x, rect):
    set_value(d,round((x-rect.left)*200/max(1,rect.width-1)))


def handle_event(app, event):
    d = app.dialog
    if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
        for rect,action,value in reversed(app.renderer.hits):
            if not rect.collidepoint(event.pos): continue
            if action == 'volume_slider':
                d['focus']=0;d['drag_rect']=rect.copy()
                slide(d,event.pos[0],rect)
            elif action == 'volume_value':
                d.update(focus=1,editing=True,text=f'{d["value"]:03d}',select_all=True)
                d.pop('error',None)
                pg.key.start_text_input()
                pg.key.set_text_input_rect(rect)
            elif action == 'volume_button': activate(app,value)
            return
    elif event.type == pg.MOUSEMOTION and d['drag_rect'] is not None:
        slide(d,event.pos[0],d['drag_rect'])
    elif event.type == pg.MOUSEBUTTONUP and event.button == 1 and d['drag_rect'] is not None:
        slide(d,event.pos[0],d['drag_rect']);d['drag_rect']=None
    elif event.type == pg.TEXTINPUT and d['editing']:
        text = event.text
        if not text or any(c not in '0123456789' for c in text): return
        old = '' if d['select_all'] else d['text']
        d['select_all']=False
        update_text(d,(old+text)[:3])
    elif event.type == pg.MOUSEWHEEL:
        d['focus']=0;set_value(d,d['value']+event.y)
    elif event.type == pg.KEYDOWN:
        key = event.key
        if key == pg.K_ESCAPE: activate(app,'cancel')
        elif key == pg.K_TAB:
            if accept_text(d): d['focus']=(d['focus']+(-1 if event.mod&pg.KMOD_SHIFT else 1))%4
        elif d['editing'] and key in (pg.K_BACKSPACE,pg.K_DELETE):
            update_text(d,'' if d['select_all'] or key==pg.K_DELETE else d['text'][:-1])
            d['select_all']=False
        elif d['editing'] and key==pg.K_a and event.mod&pg.KMOD_CTRL:
            d['select_all']=True
        elif key in (pg.K_RETURN,pg.K_KP_ENTER):
            activate(app,'cancel' if d['focus']==3 else 'ok')
        elif key in (pg.K_LEFT,pg.K_RIGHT):
            step = -1 if key==pg.K_LEFT else 1
            if d['focus']<2: set_value(d,d['value']+step)
            else: d['focus']=2+(d['focus']-2+step)%2
        elif key in (pg.K_HOME,pg.K_END) and d['focus']<2:
            set_value(d,0 if key==pg.K_HOME else 200)


def draw(r,app):
    d=app.dialog;c=palette(app.appearance);r.hits=[]
    shade=pg.Surface(r.screen.get_size(),pg.SRCALPHA);shade.fill((0,0,0,175));r.screen.blit(shade,(0,0))
    w,h=min(66,r.cols-2),min(15,r.lines-2);x,y=(r.cols-w)/2,(r.lines-h)/2
    r.panel(x,y,w,h)
    frame=pg.Rect(round(x*r.cw),round(y*r.rh),round(w*r.cw),round(h*r.rh))
    pg.draw.rect(r.screen,c['TEXT'],frame,1)
    r.control_text(pg.Rect(frame.x,frame.y+4,frame.width,r.rh),d['title'],c['TEXT'])
    r.text(x+2,y+1.8,f'Sample {d["slot"]:02d}: marked range only',c['TEXT'],w-4)
    track=r.well(x+2,y+3.3,w-4,1.3).inflate(-4,-5)
    proportion=d['value']/200
    pg.draw.rect(r.screen,c['SLIDER'],(track.x,track.y,round(track.width*proportion),track.height))
    slider_thumb(r,track,proportion)
    r.hits.append((track.inflate(0,8),'volume_slider',None))
    if d['focus']==0:pg.draw.rect(r.screen,c['TEXT'],track.inflate(10,12),1)
    r.text(x+2,y+4.9,'0%',c['TEXT']);r.text(x+w-5,y+4.9,'200%',c['TEXT'])
    field=r.well(x+(w-7)/2,y+6.2,7,1.5)
    if d['editing'] and d['select_all']:pg.draw.rect(r.screen,c['SELECT'],field.inflate(-6,-6))
    value=d['text'].ljust(3,'_') if d['editing'] else f'{d["value"]:03d}'
    r.control_text(field,value,c['YELLOW'])
    r.hits.append((field,'volume_value',None))
    if d['focus']==1:pg.draw.rect(r.screen,c['CREAM'],field.inflate(4,4),1)
    r.control_text(pg.Rect(field.x,round((y+7.8)*r.rh),field.width,r.rh),'%',c['TEXT'])
    r.text(x+2,y+9.2,d.get('error','100% = no change. Peaks above full scale are clipped.'),c['TEXT'],w-4)
    bw=(w-5)/2
    for i,(label,action) in enumerate((('OK','ok'),('Cancel','cancel'))):
        button(r,x+2+i*(bw+1),y+h-3,bw,label,'volume_button',action,d['focus']==i+2)
    r.text(x+2,y+h-1.4,'Drag / arrows: adjust | Click number: type',c['TEXT'],w-4)
