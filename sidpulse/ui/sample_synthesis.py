"""Audition a SID approximation and choose an instrument slot before writing."""
from copy import deepcopy
import pygame as pg

from sidpulse.ui.instrument_graphs import button
from sidpulse.ui.themes import palette
from sidpulse.song.model import note_name


def draw_protection(r, app, left, top, bottom):
    import textwrap
    c=palette(app.appearance);info=app.synthesis_info();frozen=app.instrument_frozen()
    width=r.cols-left-2
    if app.instrument_slot not in app.editor.song.instruments:return top,False
    if not info and not frozen and (left==1 or width>=61):
        button(r,left+44,top-(1.5 if left==1 else 1.25),16,'Freeze','instrument_freeze')
        return top,False
    if not info and not frozen and app.inline_recording_visible:return top,False
    if info:
        text=f'Synthesized from sample {info.get("sample_slot",0):02d}: "{info.get("source_name", "audio")}"'
        lines=textwrap.wrap(text,max(15,int(width)))
        r.rect(left,top,width,.08,c['EDGE'])
        for i,line in enumerate(lines):r.text(left,top+.3+i,line,c['TEXT'],width)
        top+=len(lines)+.6;r.rect(left,top,width,.08,c['EDGE']);top+=.5
    button(r,left,top,min(25,width),'Unfreeze instrument' if frozen else 'Freeze instrument',
           'instrument_freeze',selected=app.instrument_focus=='buttons' and
           app.instrument_buttons()[app.instrument_button % len(app.instrument_buttons())][0]=='instrument_freeze')
    r.text(left+27,top+.15,'FROZEN' if frozen else 'Editable',c['TEXT'],width-27)
    if not frozen or app.inline_recording_visible:return top+2,False
    button(r,left,top+2,min(27,width),'Record automation','pulse_record_arm')
    inst=app.editor.song.instruments[app.editor.instrument]
    lines=['Frozen to protect its settings and tables.',
           'Unfreeze to experiment; refreeze or undo when needed.',
           'Pattern automation still changes the playing sound.',
           'ADSR '+''.join(f'{getattr(inst,key):X}' for key in ('attack','decay','sustain','release'))+
           f' / pulse {inst.pulse_width:03X} / gate {inst.gate_ticks} ticks',
           'Wave table: '+' '.join(f'{w:02X}' for w in (inst.wave_sequence or [inst.waveform])),
           'Pitch table: '+' '.join(f'{p:+d}' for p in (inst.pitch_sequence or [0]))]
    if inst.sample_override:
        lines=lines[:3]+[f'Using PCM sample {inst.sample_slot:02d}, gain {inst.sample_gain}%.']
    y=top+4
    for line in lines:
        for part in textwrap.wrap(line,max(15,int(width))):
            if y>=bottom-1:return top,True
            r.text(left,y,part,c['TEXT'],width);y+=1
        y+=.5
    return top,True


def begin(app):
    from sidpulse.audio.media import PLAYABLE_ENCODINGS
    sample = app.selected_sample()
    if not isinstance(sample, dict) or sample.get('encoding') not in PLAYABLE_ENCODINGS:
        app.notice('Select a sample', 'Import or select a PCM sample in F3 first.');return
    app.release_audition()
    app._start_media_job(sample, {'operation':'synthesize','model':app.editor.song.sid_model,
                                  'clock':app.editor.song.clock,'tempo':app.editor.song.tempo},
                         assignment={'slot':app.sample_index,'synthesis':True,'source':sample})


def show_result(app, result, assignment):
    selected = next((n for n in range(1,100) if n not in app.editor.song.instruments), app.editor.instrument)
    result['instrument']._extra_fields['sample_synthesis']['sample_slot'] = assignment['slot']
    app.dialog = dict(kind='sample_synthesis',title='Synthesize audio (create wavetable)',
                      result=result,source=assignment['source'],source_slot=assignment['slot'],
                      selected=selected,scroll=max(0,selected-6),focus='list',button=0,drag_rect=None)
    app.page = 'samples'


def choose(app):
    d=app.dialog;number=d['selected'];inst=deepcopy(d['result']['instrument'])
    app.release_audition()
    def commit():
        from sidpulse.project.format import validate
        instruments=dict(app.editor.song.instruments);instruments[number]=deepcopy(inst)
        probe=deepcopy(app.editor.song);probe.instruments=instruments;validate(probe)
        app.editor.edit(f'Synthesize instrument {number:02d}',[(('instruments',),instruments)])
        app.editor.instrument=app.instrument_slot=number
        app.dialog=None;app.change_page('instrument');app.instrument_tab='general'
        app.instrument_focus='list';app.property_index=0
        app.editor.status=f'Created SID instrument {number:02d}: {inst.name}. Frozen against accidental edits; Unfreeze in F4. Source sample retained.'
    if number in app.editor.song.instruments:
        existing=app.editor.song.instruments[number]
        app.dialog=dict(title='Replace instrument?',
                        message=f'Replace instrument {number:02d}, {existing.name}, with {inst.name}? '
                                'Patterns using this slot will play the new SID sound. This can be undone.',
                        yes=commit,on_cancel=lambda:setattr(app,'dialog',d))
    else:commit()


def activate(app, action):
    d=app.dialog
    if action=='cancel':app.release_audition();app.dialog=None
    elif action=='use':choose(app)
    elif action=='stop':app.panic()
    elif action in ('sample','instrument'):
        if app.audio.playback.status!='stopped':
            app.editor.status='F8 stops the song for synthesis audition.';return
        app.release_audition()
        root=d['result']['details']['root_note']
        if action=='sample':app.audio.send('sample_on','synthesis-source',root,d['source'])
        else:app.audio.send('on','synthesis-result',root,d['result']['instrument'])


def select(d, number):
    d['selected']=max(1,min(99,number));d['focus']='list'
    rows=d.get('rows',10)
    d['scroll']=max(0,min(d['scroll'],d['selected']-1))
    d['scroll']=max(d['scroll'],d['selected']-rows)


def slide(d, y, rect):
    d['scroll']=max(0,min(99-d['rows'],round((y-rect.top)*(99-d['rows'])/max(1,rect.height-1))))


def handle_event(app,event):
    d=app.dialog
    if event.type==pg.MOUSEBUTTONDOWN and event.button==1:
        for rect,action,value in reversed(app.renderer.hits):
            if not rect.collidepoint(event.pos):continue
            if action=='synthesis_slot':select(d,value)
            elif action=='synthesis_action':activate(app,value)
            elif action=='synthesis_scroll':d['drag_rect']=rect.copy();slide(d,event.pos[1],rect)
            return
    elif event.type==pg.MOUSEMOTION and d['drag_rect'] is not None:slide(d,event.pos[1],d['drag_rect'])
    elif event.type==pg.MOUSEBUTTONUP and event.button==1:d['drag_rect']=None
    elif event.type==pg.MOUSEWHEEL:
        d['scroll']=max(0,min(99-d['rows'],d['scroll']-event.y*3))
    elif event.type==pg.KEYDOWN:
        key=event.key
        if key==pg.K_ESCAPE:activate(app,'cancel')
        elif key==pg.K_F8:activate(app,'stop')
        elif key==pg.K_TAB:d['focus']='buttons' if d['focus']=='list' else 'list'
        elif key in (pg.K_UP,pg.K_DOWN,pg.K_PAGEUP,pg.K_PAGEDOWN,pg.K_HOME,pg.K_END):
            target=1 if key==pg.K_HOME else 99 if key==pg.K_END else d['selected']+{
                pg.K_UP:-1,pg.K_DOWN:1,pg.K_PAGEUP:-d['rows'],pg.K_PAGEDOWN:d['rows']}[key]
            select(d,target)
        elif key in (pg.K_LEFT,pg.K_RIGHT) and d['focus']=='buttons':
            d['button']=(d['button']+(-1 if key==pg.K_LEFT else 1))%5
        elif key in (pg.K_RETURN,pg.K_KP_ENTER,pg.K_SPACE):
            activate(app,('sample','instrument','stop','use','cancel')[d['button']] if d['focus']=='buttons' else 'use')


def draw(r,app):
    d=app.dialog;c=palette(app.appearance);r.hits=[]
    shade=pg.Surface(r.screen.get_size(),pg.SRCALPHA);shade.fill((0,0,0,175));r.screen.blit(shade,(0,0))
    w,h=min(82,r.cols-2),min(32,r.lines-2);x,y=(r.cols-w)/2,(r.lines-h)/2
    r.panel(x,y,w,h,d['title'])
    info=d['result']['details'];inst=d['result']['instrument']
    r.text(x+2,y+2,f'Sample {d["source_slot"]:02d}: {d["source"]["name"]}',c['YELLOW'],w-4)
    r.text(x+2,y+3,f'{info["kind"].title()} approximation / {info["model"]} / audition {note_name(info["root_note"])} / tempo {info["tempo"]}',c['TEXT'],w-4)
    r.text(x+2,y+4,'Audition, then choose a slot. Unfreeze in F4 to experiment.',c['TEXT'],w-4)
    bw=(w-7)/3
    for i,(label,action) in enumerate((('Play sample','sample'),('Play instrument','instrument'),('Stop (F8)','stop'))):
        button(r,x+2+i*(bw+1),y+6,bw,label,'synthesis_action',action,d['focus']=='buttons' and d['button']==i)
    r.text(x+2,y+8,'SLOT  INSTRUMENT',c['TEXT'],w-24)
    r.text(x+w-20,y+8,'TYPE',c['TEXT'],16)
    rows=d['rows']=max(1,int(h-15));d['scroll']=max(0,min(99-rows,d['scroll']))
    area=r.well(x+2,y+9,w-4,rows)
    for i,n in enumerate(range(d['scroll']+1,min(100,d['scroll']+rows+1))):
        current=app.editor.song.instruments.get(n)
        if n==d['selected']:r.rect(x+2.2,y+9+i,w-5.4,1,c['SELECT'])
        r.text(x+2.5,y+9+i,f'{n:02d}    '+(current.name if current else '(empty slot)'),c['YELLOW'] if n==d['selected'] else c['CREAM'],w-26)
        kind=f'PCM {current.sample_slot:02d}' if current and current.sample_override else 'SID' if current else 'Empty'
        r.text(x+w-20,y+9+i,kind,c['TEXT'] if n==d['selected'] else c['CREAM'],15)
        r.hit(x+2,y+9+i,w-6,1,'synthesis_slot',n)
    track=pg.Rect(area.right-r.cw,area.top+3,r.cw-2,area.height-6)
    pg.draw.rect(r.screen,c['BG'],track)
    thumb_h=max(8,round(track.height*rows/99))
    thumb=pg.Rect(track.x,track.y+round((track.height-thumb_h)*d['scroll']/max(1,99-rows)),track.width,thumb_h)
    pg.draw.rect(r.screen,c['CREAM'],thumb);r.hits.append((track,'synthesis_scroll',None))
    r.text(x+2,y+h-5,f'Destination {d["selected"]:02d} / '+inst.name,c['TEXT'],w-4)
    bw=(w-5)/2
    for i,(label,action) in enumerate((('Use selected slot','use'),('Cancel','cancel'))):
        button(r,x+2+i*(bw+1),y+h-3.5,bw,label,'synthesis_action',action,d['focus']=='buttons' and d['button']==i+3)
    r.text(x+2,y+h-1.8,'Arrows / wheel: slots | Tab: buttons | Esc: cancel',c['TEXT'],w-4)
