"""Autosave controls: On/Off, minutes slider, editable folder, create/retry."""
import pygame as pg
from sidpulse.ui.instrument_graphs import button, slider_thumb
from sidpulse.ui.themes import palette


def open_dialog(app):
    app.release_audition()
    app.dialog = {'kind':'autosave_settings', 'title':'Autosave settings',
                  'enabled':app.autosave.enabled, 'minutes':app.autosave.minutes,
                  'directory':str(app.autosave.directory), 'focus':0, 'drag':None}


def activate(app, action):
    d=app.dialog
    if action=='toggle': d['enabled']=not d['enabled']
    elif action=='cancel': app.dialog=None
    elif action=='folder':
        def accept(value):
            if not value.strip(): raise ValueError('Choose a folder for autosaves')
            d['directory']=value
        app.text_dialog('Autosave folder',d['directory'],accept,'Choose a writable folder. Create folder checks it before applying.')
        app.dialog['return_dialog']=d
    elif action=='create':
        from pathlib import Path
        import tempfile
        try:
            folder=Path(d['directory']).expanduser()
            folder.mkdir(parents=True,exist_ok=True)
            with tempfile.TemporaryFile(dir=folder) as check:check.write(b'write check')
            d['message']='Folder is ready. OK applies these settings.'
        except OSError as exc:
            app.notice('Autosave folder unavailable',str(exc),return_dialog=d)
    elif action=='ok':
        try: app.autosave.configure(d['enabled'],d['minutes'],d['directory'])
        except (OSError,ValueError) as exc:
            app.notice('Autosave settings could not be saved',str(exc),return_dialog=d)
            return
        app.dialog=None
        app.show_autosave_warning()


def handle_event(app,event):
    d=app.dialog
    actions=('toggle','slider','folder','create','ok','cancel')
    def slide(x,rect):d['minutes']=max(1,min(60,round(1+(x-rect.x)*59/max(1,rect.width-1))))
    if event.type==pg.MOUSEBUTTONDOWN and event.button==1:
        for rect,action,value in reversed(app.renderer.hits):
            if rect.collidepoint(event.pos) and action=='autosave_control':
                d['focus']=actions.index(value)
                if value=='slider': d['drag']=rect.copy();slide(event.pos[0],rect)
                else: activate(app,value)
                break
    elif event.type==pg.MOUSEMOTION and d['drag'] is not None:slide(event.pos[0],d['drag'])
    elif event.type==pg.MOUSEBUTTONUP:d['drag']=None
    elif event.type==pg.KEYDOWN:
        if event.key==pg.K_ESCAPE:activate(app,'cancel')
        elif event.key==pg.K_TAB:d['focus']=(d['focus']+(-1 if event.mod&pg.KMOD_SHIFT else 1))%len(actions)
        elif event.key in (pg.K_LEFT,pg.K_RIGHT):
            delta=-1 if event.key==pg.K_LEFT else 1
            if d['focus']==1:d['minutes']=max(1,min(60,d['minutes']+delta))
            else:d['focus']=(d['focus']+delta)%len(actions)
        elif event.key in (pg.K_RETURN,pg.K_SPACE):
            if actions[d['focus']]!='slider':activate(app,actions[d['focus']])


def draw(r,app):
    d=app.dialog;c=palette(app.appearance);r.hits=[]
    shade=pg.Surface(r.screen.get_size(),pg.SRCALPHA);shade.fill((0,0,0,175));r.screen.blit(shade,(0,0))
    w,h=min(82,r.cols-2),min(19,r.lines-2);x,y=(r.cols-w)/2,(r.lines-h)/2
    r.panel(x,y,w,h,'Autosave settings')
    actions=('toggle','slider','folder','create','ok','cancel')
    def control(xx,yy,ww,label,action):
        return button(r,xx,yy,ww,label,'autosave_control',action,d['focus']==actions.index(action))
    control(x+2,y+2,22,'Autosave '+('ON' if d['enabled'] else 'OFF'),'toggle')
    r.text(x+2,y+4,f'Interval: {d["minutes"]} minute'+('' if d['minutes']==1 else 's'),c['TEXT'],w-4)
    track=r.well(x+2,y+5.5,w-4,1.3).inflate(-4,-5);p=(d['minutes']-1)/59
    pg.draw.rect(r.screen,c['SLIDER'],(track.x,track.y,round(track.width*p),track.height));slider_thumb(r,track,p)
    r.hits.append((track.inflate(0,8),'autosave_control','slider'))
    if d['focus']==1:pg.draw.rect(r.screen,c['TEXT'],track.inflate(10,12),1)
    r.text(x+2,y+7,'Folder (click to change)',c['TEXT'],w-4)
    field=r.well(x+2,y+8.3,w-4,1.3);r.control_text(field,d['directory'],c['YELLOW'],align='left')
    r.hits.append((field,'autosave_control','folder'))
    if d['focus']==2:pg.draw.rect(r.screen,c['TEXT'],field.inflate(4,4),1)
    control(x+2,y+10,25,'Create folder / Retry','create')
    r.text(x+2,y+12,d.get('message','Recovery copies keep unsaved edits separate from your project.'),c['TEXT'],w-4)
    control(x+2,y+h-3,12,'OK','ok');control(x+16,y+h-3,14,'Cancel','cancel')
    r.text(x+2,y+h-1.4,'Tab: controls | Arrows: adjust | Enter: choose',c['TEXT'],w-4)
