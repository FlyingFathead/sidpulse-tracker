"""Mouse editors for existing SID instrument fields; no parallel sound model."""
import math
import pygame as pg

CREAM=(233,232,200); EDGE=(113,82,64); BG=(176,146,119)
TEXT=(12,10,8); DIM=(73,55,40); SELECT=(86,64,58); SLIDER=(169,46,66)
GREEN=(75,178,88); BLUE=(122,170,207); GOLD=(240,217,91)
COLORS=((203,69,87),(235,145,82),GREEN,BLUE)
ADSR=('attack','decay','sustain','release')


def apply_palette(colors):
    global COLORS
    globals().update({k:colors[k] for k in ('BG','EDGE','CREAM','TEXT','DIM','SELECT','SLIDER')})
    COLORS=(colors['SCOPE'],(235,145,82),GREEN,BLUE)


def clamp(value,lo,hi):
    return max(lo,min(hi,value))


def button_frame(r,rect,selected=False,fill=None):
    pg.draw.rect(r.screen,fill if fill is not None else SELECT if selected else BG,rect)
    light,dark=(EDGE,CREAM) if selected else (CREAM,EDGE)
    thick=max(2,round(r.rh/9))
    bevel=rect.inflate(-2,-2)
    pg.draw.line(r.screen,light,bevel.topleft,bevel.topright,thick)
    pg.draw.line(r.screen,light,bevel.topleft,bevel.bottomleft,thick)
    pg.draw.line(r.screen,dark,bevel.bottomleft,bevel.bottomright,thick)
    pg.draw.line(r.screen,dark,bevel.topright,bevel.bottomright,thick)
    pg.draw.rect(r.screen,TEXT,rect,1)


def button(r,x,y,w,label,action,value=None,selected=False,height=1.25,fill=None):
    rect=pg.Rect(round(x*r.cw),round(y*r.rh),round(w*r.cw),round(height*r.rh))
    cache=getattr(r,'button_cache',None)
    if cache is None or rect.width<=0 or rect.height<=0:
        button_frame(r,rect,selected,fill)
        r.control_text(rect,label,CREAM if selected else TEXT)
    else:
        key=(rect.size,str(label),bool(selected),fill)
        # Bevel lines extend past the right/bottom edge at larger thicknesses.
        # Preserve those pixels and the surrounding background through alpha.
        margin=max(2,round(r.rh/9))
        bitmap=cache.get(key)
        if bitmap is None:
            screen=r.screen
            bitmap=pg.Surface((rect.width+2*margin,rect.height+2*margin),pg.SRCALPHA).convert_alpha()
            local=pg.Rect(margin,margin,*rect.size)
            r.screen=bitmap
            try:
                button_frame(r,local,selected,fill)
                r.control_text(local,label,CREAM if selected else TEXT)
            finally:r.screen=screen
            cache[key]=bitmap
            if len(cache)>128:cache.popitem(last=False)
        else:cache.move_to_end(key)
        r.screen.blit(bitmap,rect.move(-margin,-margin))
    r.hits.append((rect,action,value))
    return rect


def slider_thumb(r,slider,proportion):
    w=min(slider.width,max(10,r.cw));h=max(6,slider.height+2)
    thumb=pg.Rect(0,0,w,h)
    thumb.midleft=(slider.left+round(max(0,slider.width-w)*proportion),slider.centery)
    pg.draw.rect(r.screen,BG,thumb)
    pg.draw.line(r.screen,CREAM,thumb.topleft,thumb.topright,2)
    pg.draw.line(r.screen,CREAM,thumb.topleft,thumb.bottomleft,2)
    pg.draw.line(r.screen,EDGE,thumb.bottomleft,thumb.bottomright,2)
    pg.draw.line(r.screen,EDGE,thumb.topright,thumb.bottomright,2)


def grid_value(pos,rect,start,low,high):
    step=start+clamp(int((pos[0]-rect.left)*16/max(1,rect.width)),0,15)
    pitch=high-clamp(int((pos[1]-rect.top)*(high-low+1)/max(1,rect.height)),0,high-low)
    return step,pitch


from sidpulse.ui.envelope import envelope_points, envelope_value, attack_caption


def draw_envelope(r,app,left,top,width,height):
    inst=app.editor.song.instruments[app.editor.instrument]
    compact = height < 8
    title = ('ADSR / '+attack_caption(inst.attack,app.editor.song.clock) if compact
             else "ADSR — schematic / drag handles")
    r.control_text(pg.Rect(left*r.cw,top*r.rh,width*r.cw,r.rh),title,TEXT)
    graph_height = max(2.5,height-2.5) if compact else max(4,height-4)
    graph=r.well(left,top+1.5,width,graph_height).inflate(-max(16,r.cw+4),-r.rh)
    for i in range(5):
        y=graph.y+i*graph.height/4
        pg.draw.line(r.screen,(35,39,38),(graph.x,y),(graph.right,y))
    points=envelope_points(graph,inst)
    for i in range(4):
        a,b=points[i:i+2]
        curve=[]
        for j in range(33):
            t=j/32
            shape=t if i in (0,2) else (1-math.exp(-4*t))/(1-math.exp(-4))
            curve.append((a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*shape))
        pg.draw.lines(r.screen,COLORS[i],False,curve,max(2,round(r.rh/10)))
        p=points[i+1]
        handle=pg.Rect(0,0,max(12,r.cw),max(12,r.cw));handle.center=p
        pg.draw.rect(r.screen,COLORS[i],handle)
        pg.draw.rect(r.screen,CREAM,handle,1)
        r.hits.append((handle.inflate(8,8),'graph_drag',{'kind':'envelope','field':ADSR[i],'rect':graph.copy()}))
        r.text((a[0]+b[0])/2/r.cw-.5,(graph.bottom+4)/r.rh,ADSR[i][0].upper(),TEXT)
    if not compact:
        r.text(left,top+height-1,attack_caption(inst.attack,app.editor.song.clock),TEXT,width)
    return graph


def draw_adsr(r,app,left,top,bottom):
    inst=app.editor.song.instruments[app.editor.instrument]
    width=r.cols-left-2
    if bottom-top<12 or width<28:
        r.text(left,top,'ADSR: enlarge window or reduce zoom',CREAM)
        return
    draw_envelope(r,app,left,top,width,bottom-top-7)
    sy=bottom-7
    for i,field in enumerate(ADSR):
        y=sy+i*1.3
        value=getattr(inst,field)
        r.text(left,y,field.title(),TEXT)
        r.control_text(r.well(left+9,y,3,1.1),f'{value:02X}',GOLD)
        r.hit(left+9,y,3,1.1,'edit_instrument_field',i+2)
        slider=r.well(left+13,y,width-14,1).inflate(-3,-3)
        pg.draw.rect(r.screen,SLIDER,(slider.x,slider.y,round(slider.width*value/15),slider.height))
        slider_thumb(r,slider,value/15)
        r.hits.append((slider.inflate(0,6),'graph_drag',{'kind':'slider','field':field,'rect':slider.copy(),'index':i+2}))
    r.text(left,bottom-1,'Schematic rate controls 00..0F; A00 is fastest, not zero time.',TEXT,width)
    # Stage widths expose the 16 rate settings, not a misleading common time axis.



def draw_roll(r,app,left,top,bottom):
    inst=app.editor.song.instruments[app.editor.instrument]
    field=app.graph_field;values=getattr(inst,field)
    width=r.cols-left-2
    if width<47 or bottom-top<14:
        r.text(left,top,'Arp / pitch: enlarge window or reduce zoom',CREAM)
        return
    button(r,left,top,12,'Arpeggio','graph_field','arpeggio',field=='arpeggio')
    button(r,left+13,top,10,'Pitch','graph_field','pitch_sequence',field=='pitch_sequence')
    r.text(left+24,top,'Length',TEXT,7)
    length=r.well(left+31,top,5,1.25)
    r.control_text(length,f'{len(values):02d}',GOLD)
    r.hits.append((length,'graph_length',None))
    button(r,left+37,top,8,'Clear','graph_clear')
    button(r,left,top+2,5,'<','graph_page',-1)
    button(r,left+6,top+2,5,'>','graph_page',1)
    start=app.graph_page*16
    r.text(left+12,top+2,f'Steps {start+1:02d}-{start+16:02d}',TEXT)
    button(r,left+27,top+2,9,'Pitch -','graph_range',-12)
    button(r,left+37,top+2,9,'Pitch +','graph_range',12)
    from sidpulse.ui.instruments import PROGRAM_LABELS
    enabled=getattr(inst,field+'_enabled')
    button(r,left,top+4,23,PROGRAM_LABELS[field]+(' on' if enabled else ' off'),
           'toggle_program',field,enabled)
    r.text(left+24,top+4,'Off keeps drawn steps',TEXT,width-24)
    low=app.graph_low;high=low+24
    area=r.well(left,top+6,width,bottom-top-11)
    piano=pg.Rect(area.x+2,area.y+2,r.cw*7,area.height-4)
    grid=pg.Rect(piano.right,piano.top,area.right-piano.right-3,piano.height)
    old=r.screen.get_clip();r.screen.set_clip(area.inflate(-2,-2))
    piano_labels=[]
    for pitch in range(high,low-1,-1):
        row=high-pitch
        y=grid.y+round(row*grid.height/25)
        height=max(1,round((row+1)*grid.height/25)+grid.y-y)
        black=pitch%12 in (1,3,6,8,10)
        pg.draw.rect(r.screen,(23,29,31) if black else (34,39,41),(grid.x,y,grid.width,height))
        pg.draw.rect(r.screen,(42,46,48) if black else (191,190,165),(piano.x,y,piano.width,height))
        if pitch%12==0 or height>=r.small_font.get_linesize() or pitch%12 in (4,7):
            from sidpulse.song.model import note_name
            note=app.editor.octave*12+pitch
            label=f'{note_name(note)} {pitch:+d}'
            glyph=r.small_font.render(label,True,CREAM if black else (10,12,12))
            piano_labels.append((glyph,(piano.x+2,clamp(y+(height-glyph.get_height())//2,piano.top,piano.bottom-glyph.get_height()))))
        pg.draw.line(r.screen,(66,73,70) if pitch==0 else (45,50,49),(grid.x,y),(grid.right,y))
    for glyph,pos in piano_labels:r.screen.blit(glyph,pos)
    for i in range(17):
        x=grid.x+round(i*grid.width/16)
        pg.draw.line(r.screen,(91,86,68) if i%4==0 else (51,57,54),(x,grid.top),(x,grid.bottom))
    for i in range(start,min(start+16,len(values))):
        value=values[i];x=grid.x+(i-start)*grid.width/16
        y=grid.y+(high-clamp(value,low,high))*grid.height/25
        tile=pg.Rect(round(x+2),round(y+1),max(2,round(grid.width/16)-3),max(2,round(grid.height/25)-1))
        pg.draw.rect(r.screen,(GOLD if i==app.graph_step else GREEN) if enabled else (145,145,135),tile)
        if not low<=value<=high:pg.draw.rect(r.screen,(230,107,93),tile,2)
    r.screen.set_clip(old)
    r.hits.append((grid,'graph_drag',{'kind':'roll','field':field,'rect':grid,'start':start,'low':low,'high':high}))
    y=bottom-4
    if field=='arpeggio':
        button(r,left,y,5,'-','graph_rate',-1)
        r.text(left+6,y,f'{inst.arp_speed} ticks / step; repeats',TEXT)
        button(r,left+34,y,5,'+','graph_rate',1)
    else:r.text(left,y,'1 tick / step; final pitch holds',TEXT)
    value=values[app.graph_step] if app.graph_step<len(values) else 0
    r.text(left,bottom-2,f'Step {app.graph_step+1:02d}: {value:+d} semitones | Draw: left drag',TEXT,width)
    r.text(left,bottom-1,'Arrows: step/pitch | Ins/Del: step | Ctrl+Bksp: undo',DIM,width)


def draw_fields(r,app,left,top,bottom,motion,full_wave=False,right=None):
    from sidpulse.ui.instruments import FIELDS,LABELS,LIMITS,SEQUENCES,PROGRAM_ROWS,PROGRAM_LABELS,display
    inst=app.editor.song.instruments[app.editor.instrument]
    first,last=(9,len(FIELDS)) if motion else (0,9)
    count=max(1,int((bottom-top)/1.4))
    indexes=[i for i in range(first,last) if not (full_wave and i==1)]
    selected=indexes.index(app.property_index) if app.property_index in indexes else 0
    start=max(0,min(len(indexes)-count,selected-count+1))
    key = 'instrument-fields'
    start=r.scroll_start(key,start,(motion,full_wave,selected),len(indexes),count)
    edge=(r.cols-2 if right is None else right)
    width=edge-left-(2 if len(indexes)>count else 0)
    for row,index in enumerate(indexes[start:start+count]):
        field=FIELDS[index];value=getattr(inst,field);y=top+row*1.4
        r.hit(left,y,width,1.3,'property',index)
        if app.property_index==index:r.rect(left,y,width,1.25,SELECT)
        if motion and index in PROGRAM_ROWS:
            program=PROGRAM_ROWS[index];enabled=getattr(inst,program+'_enabled')
            button(r,left,y,23,PROGRAM_LABELS[program]+(' on' if enabled else ' off'),
                   'toggle_program',program,enabled)
        else:
            r.control_text(pg.Rect((left+.5)*r.cw,y*r.rh,min(23,width)*r.cw,1.25*r.rh),
                           LABELS[index],CREAM if app.property_index==index else TEXT,align='left',padding=0)
        x=left+24
        if type(value) is int and field!='waveform':
            lo,hi=LIMITS.get(field,(0,4095 if field=='pulse_width' else 15))
            label=str(value) if motion else f'{value:03X}' if field=='pulse_width' else f'{value:02X}'
            r.control_text(r.well(x,y,7,1.1),label,GOLD,align='left')
            r.hit(x,y,7,1.1,'edit_instrument_field',index)
            if width>=43:
                slider=r.well(left+32,y,width-32,1.1).inflate(-3,-4)
                proportion=(value-lo)/(hi-lo)
                pg.draw.rect(r.screen,SLIDER,(slider.x,slider.y,round(slider.width*proportion),slider.height))
                slider_thumb(r,slider,proportion)
                r.hits.append((slider.inflate(0,6),'graph_drag',{'kind':'slider','field':field,'rect':slider,'lo':lo,'hi':hi,'index':index}))
        elif type(value) is bool:
            button(r,x,y,9,'ON' if value else 'OFF','toggle_instrument_field',index,value)
        elif field=='waveform':
            for i,(wave,label) in enumerate(((16,'Tri'),(32,'Saw'),(64,'Pulse'),(128,'Noise'))):
                button(r,x+i*8,y,7,label,'waveform',wave,value==wave)
        elif field in SEQUENCES:
            if field == 'wave_sequence':
                r.control_text(r.well(x,y,max(5,width-24),1.1),display(inst,field),GOLD,align='left')
                r.hit(x,y,max(5,width-24),1.1,'edit_instrument_field',index)
            else:
                button(r,x,y,8,'Draw','edit_program',field)
                r.control_text(r.well(x+9,y,max(1,width-33),1.1),display(inst,field),GOLD,align='left')
                r.hit(x+9,y,max(1,width-33),1.1,'edit_instrument_field',index)
        else:
            r.control_text(r.well(x,y,max(5,width-24),1.1),value,GOLD,align='left')
            r.hit(x,y,max(5,width-24),1.1,'edit_instrument_field',index)

    r.scroll_bar(key,edge-1.5,top,count*1.4,len(indexes),count)
