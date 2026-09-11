"""Instrument bank and graph editing gestures, sharing the document undo log."""
from copy import deepcopy
import pygame as pg
from sidpulse.song.model import Instrument
from sidpulse.ui.instrument_graphs import ADSR,clamp,grid_value,envelope_value


class InstrumentActions:
    def instrument_buttons(self):
        from sidpulse.ui.instruments import PROGRAM_ROWS
        targets=[('add_instrument',None),('delete_instrument',None),('choose_presets',None)]
        targets += [('instrument_tab',tab) for tab in ('general','motion','roll','adsr')]
        targets.append(('save_user_preset',None))
        if self.instrument_slot in self.editor.song.instruments:
            if self.instrument_tab=='motion':
                targets += [('toggle_program',program) for program in PROGRAM_ROWS.values()]
            elif self.instrument_tab=='roll':
                targets.append(('toggle_program',self.graph_field))
        return targets

    def toggle_instrument_program(self,program):
        from sidpulse.ui.instruments import PROGRAM_ROWS,PROGRAM_LABELS
        if self.instrument_slot not in self.editor.song.instruments:return
        self.finish_instrument_drag()
        inst=self.editor.song.instruments[self.editor.instrument]
        field=program+'_enabled';enabled=not getattr(inst,field)
        self.editor.edit(PROGRAM_LABELS[program]+(' on' if enabled else ' off'),
                         [(('instruments',self.editor.instrument,field),enabled)])
        self.property_index=next(i for i,p in PROGRAM_ROWS.items() if p==program)
        self.instrument_focus='buttons'
        target=('toggle_program',program)
        if target in self.instrument_buttons():self.instrument_button=self.instrument_buttons().index(target)

    def select_instrument_slot(self,delta=0,number=None):
        self.release_audition()
        self.instrument_slot=clamp(self.instrument_slot+delta if number is None else number,1,99)
        if self.instrument_slot in self.editor.song.instruments:self.editor.instrument=self.instrument_slot

    def save_instrument_preset(self):
        if self.instrument_slot not in self.editor.song.instruments:
            self.editor.status='Choose an existing instrument to save as a user preset.';return
        from sidpulse.song.presets import save_user_preset
        path=save_user_preset(self.editor.song.instruments[self.editor.instrument])
        self.editor.status='User preset saved: '+path.name

    def open_new_instrument(self,mode='choice'):
        self.open_presets()
        if self.instrument_slot not in self.editor.song.instruments:self.dialog['target_slot']=self.instrument_slot
        self.dialog['mode']=mode;self.dialog['choice_index']=0
        self.dialog['manual']=Instrument('New instrument')

    def chooser_source(self,source):
        from sidpulse.song.presets import built_in_catalog,user_presets
        self.release_audition();d=self.dialog;d['source']=source;d['preset_index']=0
        if source=='builtin':d['presets']=built_in_catalog()
        else:
            d['presets'],errors=user_presets()
            if errors:self.editor.status='Invalid user presets: '+'; '.join(errors)

    def add_instrument(self,preset=None,target=None):
        self.finish_instrument_drag()
        self.release_audition()
        ed=self.editor
        number=target if target is not None and target not in ed.song.instruments else self.instrument_slot if self.instrument_slot not in ed.song.instruments else next((i for i in range(1,100) if i not in ed.song.instruments),None)
        if number is None:
            ed.status='Instrument bank is full (99 slots).'
            return
        instruments=deepcopy(ed.song.instruments)
        instruments[number]=deepcopy(preset) if preset is not None else Instrument(f'Instrument {number:02d}')
        ed.edit('Add preset '+preset.name if preset is not None else 'Add instrument',[(('instruments',),instruments)])
        ed.instrument=number;self.instrument_slot=number
        self.instrument_focus='properties'
        self.instrument_tab='general';self.property_index=0

    def open_presets(self):
        from sidpulse.song.presets import built_in_catalog
        self.finish_instrument_drag();self.release_audition()
        self.dialog={'title':'Add SID instrument','presets':built_in_catalog(),'preset_index':0,
                     'mode':'presets','manual':None,'manual_index':0,'chooser_focus':'fields','chooser_button':0,'catalog_button':0,'source':'builtin',
                     'target_slot':self.instrument_slot if self.instrument_slot not in self.editor.song.instruments else None}

    def add_preset(self,preset):
        self.add_instrument(preset)

    def chooser_mode(self,mode):
        d=self.dialog;self.release_audition();d['mode']=mode;d['chooser_focus']='fields'
        if mode=='manual' and d['manual'] is None:
            d['manual']=deepcopy(d['presets'][d['preset_index']][1]) if d['presets'] else Instrument('New instrument')

    def chooser_add(self):
        d=self.dialog
        if d['mode']=='presets' and not d['presets']:return
        preset=d['manual'] if d['mode']=='manual' else d['presets'][d['preset_index']][1]
        self.dialog=None;self.add_instrument(preset,d.get('target_slot'))

    def manual_entry(self,index,initial=None):
        from sidpulse.ui.instruments import FIELDS
        d=self.dialog;field=FIELDS[index];d['manual_index']=index;inst=d['manual']
        value=getattr(inst,field)
        def accept(text):
            if field=='name':new=text
            elif type(value) is bool:new=text.lower() in ('on','true','1','yes')
            else:
                new=int(text.lstrip('$'),16);limit=4095 if field=='pulse_width' else 15
                if field=='waveform':
                    if new not in (16,32,64,128):raise ValueError('Use 10, 20, 40 or 80 hexadecimal')
                elif not 0<=new<=limit:raise ValueError(f'Use 0..{limit:X} hexadecimal')
            setattr(inst,field,new)
        self.text_dialog('Manual: '+field, str(value) if type(value) is not int else f'{value:X}',accept,'SID values are hexadecimal. This draft is added only with Add instrument.')
        self.dialog['return_dialog']=d
        if initial is not None:
            self.dialog.update(text=initial,select_all=False,ignore_initial_text=initial)

    def manual_slider(self,pos):
        d=self.dialog;drag=d.get('manual_drag')
        if not drag:return
        lo,hi=drag.get('lo',0),drag.get('hi',15);rect=drag['rect']
        setattr(d['manual'],drag['field'],clamp(round(lo+(pos[0]-rect.x)*(hi-lo)/max(1,rect.width-1)),lo,hi))

    def preset_event(self,event):
        from sidpulse.ui.keyboard import NOTE_SCANCODES
        from sidpulse.ui.instruments import FIELDS
        d=self.dialog
        if d['mode']=='choice':
            choice=None
            if event.type==pg.KEYDOWN:
                if event.key==pg.K_ESCAPE:self.dialog=None;return
                if event.key in (pg.K_LEFT,pg.K_RIGHT,pg.K_TAB):d['choice_index']=(d['choice_index']+(-1 if event.key==pg.K_LEFT else 1))%3
                elif event.key==pg.K_RETURN:choice=d['choice_index']
            elif event.type==pg.MOUSEBUTTONDOWN and event.button==1:
                for rect,action,value in reversed(self.renderer.hits):
                    if rect.collidepoint(event.pos):
                        if action=='new_choice':choice=value
                        elif action=='preset_cancel':self.dialog=None
                        break
            if choice==0:self.chooser_mode('presets')
            elif choice==1:
                self.dialog=None;self.add_instrument(target=d.get('target_slot'))
            elif choice==2:self.chooser_mode('manual')
            return
        if event.type==pg.MOUSEMOTION and d.get('manual_drag'):
            self.manual_slider(event.pos);return
        if event.type==pg.MOUSEBUTTONUP and event.button==1:
            self.manual_slider(event.pos);d.pop('manual_drag',None);return
        if event.type==pg.KEYUP:
            self.audio.send('off',f'preset-{event.scancode}');self.held.discard(event.scancode)
        elif event.type==pg.MOUSEWHEEL:
            if d['mode']=='presets':d['preset_index']=clamp(d['preset_index']-event.y,0,len(d['presets'])-1)
            else:d['manual_index']=clamp(d['manual_index']-event.y,0,8)
        elif event.type==pg.KEYDOWN:
            catalog=([('chooser_source','builtin'),('chooser_source','user')]+[('preset_category',c) for c in dict.fromkeys(c for c,_ in d['presets'])]) if d['mode']=='presets' else [('manual_blank',None)]
            if d['chooser_focus']=='catalog' and event.key in (pg.K_LEFT,pg.K_RIGHT,pg.K_UP,pg.K_DOWN,pg.K_RETURN):
                if event.key==pg.K_RETURN:
                    action,value=catalog[d['catalog_button']%len(catalog)]
                    if action=='chooser_source':self.chooser_source(value)
                    elif action=='manual_blank':d['manual']=Instrument('New instrument')
                    else:d['preset_index']=next(i for i,(c,_) in enumerate(d['presets']) if c==value)
                else:d['catalog_button']=(d['catalog_button']+(-1 if event.key in (pg.K_LEFT,pg.K_UP) else 1))%len(catalog)
                return
            if event.key==pg.K_ESCAPE:self.release_audition();self.dialog=None
            elif event.key==pg.K_TAB:
                groups=('fields','catalog','buttons');d['chooser_focus']=groups[(groups.index(d['chooser_focus'])+(-1 if event.mod&pg.KMOD_SHIFT else 1))%3]
            elif event.key in (pg.K_LEFT,pg.K_RIGHT):
                if d['chooser_focus']=='buttons':d['chooser_button']=1-d['chooser_button']
                else:self.chooser_mode('presets' if event.key==pg.K_LEFT else 'manual')
            elif event.key in (pg.K_UP,pg.K_DOWN,pg.K_PAGEUP,pg.K_PAGEDOWN):
                self.release_audition();delta={pg.K_UP:-1,pg.K_DOWN:1,pg.K_PAGEUP:-8,pg.K_PAGEDOWN:8}[event.key]
                field='preset_index' if d['mode']=='presets' else 'manual_index'
                d[field]=clamp(d[field]+delta,0,len(d['presets'])-1 if d['mode']=='presets' else 8)
            elif event.key==pg.K_RETURN:
                if d['chooser_focus']=='buttons' and d['chooser_button']==1:self.release_audition();self.dialog=None
                elif d['mode']=='presets' or d['chooser_focus']=='buttons' or event.mod&pg.KMOD_CTRL:self.chooser_add()
                # Parameter typing is opened only by clicking its value field.
            elif event.key==pg.K_F8:self.panic()
            elif getattr(event,'scancode',0) in NOTE_SCANCODES and not event.mod&(pg.KMOD_ALT|pg.KMOD_CTRL|pg.KMOD_SHIFT):
                if d['mode']=='presets' and not d['presets']:return
                if self.audio.playback.status!='stopped':self.editor.status='F8 stops playback for preset audition.';return
                if event.scancode not in self.held:
                    inst=d['manual'] if d['mode']=='manual' else d['presets'][d['preset_index']][1]
                    self.audio.send('on',f'preset-{event.scancode}',min(95,self.editor.octave*12+NOTE_SCANCODES[event.scancode]),inst)
                    self.held.add(event.scancode)
        elif event.type==pg.MOUSEBUTTONDOWN and event.button==1:
            for rect,action,value in reversed(self.renderer.hits):
                if not rect.collidepoint(event.pos):continue
                if action=='chooser_mode':self.chooser_mode(value)
                elif action=='chooser_source':self.chooser_source(value)
                elif action=='preset_category':
                    self.release_audition();d['preset_index']=next(i for i,(category,_) in enumerate(d['presets']) if category==value)
                elif action=='preset_select':self.release_audition();d['preset_index']=value
                elif action=='preset_add':self.chooser_add()
                elif action=='preset_cancel':self.release_audition();self.dialog=None
                elif action=='manual_blank':d['manual']=Instrument('New instrument')
                elif action=='edit_instrument_field':self.manual_entry(value)
                elif action=='property':d['manual_index']=value
                elif action=='toggle_instrument_field':setattr(d['manual'],FIELDS[value],not getattr(d['manual'],FIELDS[value]))
                elif action=='waveform':d['manual'].waveform=value
                elif action=='graph_drag':
                    d['manual_drag']=value;d['manual_index']=value['index'];self.manual_slider(event.pos)
                break

    def confirm_delete_instrument(self):
        self.finish_instrument_drag()
        self.release_audition()
        ed=self.editor;number=self.instrument_slot
        if number not in ed.song.instruments:
            ed.status='This instrument slot is already empty.';return
        if len(ed.song.instruments)==1:
            ed.status='Keep at least one instrument. Add another before deleting this one.'
            return
        replacement=min(i for i in ed.song.instruments if i!=number)
        count=sum(c.instrument==number for p in ed.song.patterns.values() for row in p.rows for c in row)
        def remove():
            instruments=deepcopy(ed.song.instruments);instruments.pop(number)
            updates=[(('instruments',),instruments)]
            for pid,pat in ed.song.patterns.items():
                for row,cells in enumerate(pat.rows):
                    for voice,cell in enumerate(cells):
                        if cell.instrument==number:
                            updates.append((('patterns',pid,'rows',row,voice,'instrument'),replacement))
            ed.edit(f'Delete instrument {number:02d}',updates)
            ed.instrument=replacement;self.instrument_slot=number
        self.dialog={'title':'Delete instrument?',
                     'message':f'Are you sure you want to delete instrument {number:02d} ? '
                               + (f'{count} pattern references will use instrument {replacement:02d}. Notes remain. ' if count else 'No pattern references. ')
                               +'This can be undone.',
                     'confirm_instrument':remove,'confirm_selected':False}

    def choose_instrument_tab(self,tab):
        if self.instrument_slot not in self.editor.song.instruments:self.open_new_instrument();return
        self.finish_instrument_drag()
        self.instrument_tab=tab;self.instrument_focus='properties'
        if tab=='motion':self.property_index=9
        elif tab=='general':self.property_index=0
        elif tab=='adsr':self.property_index=2

    def finish_instrument_drag(self,cancel=False):
        gesture=self.instrument_drag
        if gesture is None:return
        self.instrument_drag=None
        inst=self.editor.song.instruments[gesture['instrument']]
        updates=[]
        for field,before in gesture['before'].items():
            after=deepcopy(getattr(inst,field));setattr(inst,field,before)
            updates.append((('instruments',gesture['instrument'],field),after))
        self.editor.history.revision+=1
        if not cancel:self.editor.edit('Draw instrument '+gesture['field'],updates)

    def begin_instrument_drag(self,data,pos):
        self.finish_instrument_drag()
        inst=self.editor.song.instruments[self.editor.instrument]
        fields=ADSR if data['kind']=='envelope' else (data['field'],)
        self.instrument_drag={**data,'instrument':self.editor.instrument,
                              'before':{f:deepcopy(getattr(inst,f)) for f in fields},'last':None}
        self.instrument_focus='properties'
        if 'index' in data:self.property_index=data['index']
        self.update_instrument_drag(pos)

    def update_instrument_drag(self,pos):
        drag=self.instrument_drag
        if not drag:return
        inst=self.editor.song.instruments[drag['instrument']]
        field=drag['field'];rect=drag['rect']
        if drag['kind']=='roll':
            step,pitch=grid_value(pos,rect,drag['start'],drag['low'],drag['high'])
            values=list(getattr(inst,field))
            if len(values)<=step:values.extend([0]*(step+1-len(values)))
            # Interpolate skipped mouse samples so a fast sweep has no holes.
            if drag['last'] is not None:
                old_step,old_pitch=drag['last']
                lo,hi=sorted((old_step,step))
                for i in range(lo,hi+1):
                    values[i]=round(old_pitch+(pitch-old_pitch)*(i-old_step)/(step-old_step)) if step!=old_step else pitch
            values[step]=pitch;drag['last']=(step,pitch)
            self.graph_step=step;updates={field:values}
        elif drag['kind']=='slider':
            lo,hi=drag.get('lo',0),drag.get('hi',15)
            updates={field:clamp(round(lo+(pos[0]-rect.x)*(hi-lo)/max(1,rect.width-1)),lo,hi)}
        else:updates=envelope_value(pos,rect,field)
        changed=False
        for key,value in updates.items():
            if getattr(inst,key)!=value:setattr(inst,key,value);changed=True
        if changed:self.editor.history.revision+=1

    def graph_edit_sequence(self,values,label):
        self.editor.edit(label,[(('instruments',self.editor.instrument,self.graph_field),values)])
        self.graph_step=min(self.graph_step,max(0,len(values)-1))

    def roll_key(self,event):
        inst=self.editor.song.instruments[self.editor.instrument]
        values=list(getattr(inst,self.graph_field));key=event.key
        if key in (pg.K_LEFT,pg.K_RIGHT):
            self.graph_step=clamp(self.graph_step+(-1 if key==pg.K_LEFT else 1),0,63)
            self.graph_page=self.graph_step//16
        elif key in (pg.K_UP,pg.K_DOWN):
            if len(values)<=self.graph_step:values.extend([0]*(self.graph_step+1-len(values)))
            values[self.graph_step]=clamp(values[self.graph_step]+(-1 if key==pg.K_DOWN else 1),-48,48)
            self.graph_edit_sequence(values,'Adjust pitch step')
            note=values[self.graph_step]
            if note<self.graph_low:self.graph_low=clamp(note,-48,24)
            if note>self.graph_low+24:self.graph_low=clamp(note-24,-48,24)
        elif key==pg.K_INSERT:
            if len(values)<64:
                values.insert(min(self.graph_step,len(values)),0);self.graph_edit_sequence(values,'Insert pitch step')
        elif key==pg.K_DELETE:
            if self.graph_step<len(values):
                values.pop(self.graph_step);self.graph_edit_sequence(values,'Delete pitch step')
        else:return False
        return True

    def graph_length_dialog(self):
        field=self.graph_field;number=self.editor.instrument
        inst=self.editor.song.instruments[number]
        def accept(text):
            size=int(text)
            if not 0<=size<=64:raise ValueError('Length must be 0..64 steps')
            values=getattr(self.editor.song.instruments[number],field)
            values=(values+[0]*size)[:size]
            self.editor.edit('Resize '+field,[(('instruments',number,field),values)])
            self.graph_step=min(self.graph_step,max(0,size-1));self.graph_page=self.graph_step//16
        self.text_dialog('Sequence length',str(len(getattr(inst,field))),accept,'0 disables the program. New steps start at the base note.')

    def instrument_action(self,action,value,pos):
        if action=='toggle_program':self.toggle_instrument_program(value)
        elif action=='edit_instrument_field':
            self.property_index=value;self.instrument_focus='properties'
            self.page_key(pg.event.Event(pg.KEYDOWN,key=pg.K_RETURN,mod=0,value_click=True))
        elif action=='toggle_instrument_field':
            self.property_index=value;self.change_property(1)
        elif action=='edit_program':
            if value=='wave_sequence':
                self.property_index=11;self.change_property()
            else:
                self.choose_instrument_tab('roll');self.graph_field=value
        elif action=='choose_presets':self.open_presets()
        elif action=='add_instrument':self.open_new_instrument()
        elif action=='new_instrument_mode':
            if value=='blank':self.add_instrument()
            else:self.open_new_instrument(value)
        elif action=='save_user_preset':self.save_instrument_preset()
        elif action=='delete_instrument':self.confirm_delete_instrument()
        elif action=='instrument_tab':
            if self.instrument_slot in self.editor.song.instruments:self.choose_instrument_tab(value)
        elif action=='graph_drag':self.begin_instrument_drag(value,pos)
        elif action=='graph_field':
            self.graph_field=value;self.graph_step=0;self.graph_page=0
        elif action=='graph_page':
            self.graph_page=clamp(self.graph_page+value,0,3);self.graph_step=self.graph_page*16
        elif action=='graph_range':self.graph_low=clamp(self.graph_low+value,-48,24)
        elif action=='graph_length':self.graph_length_dialog()
        elif action=='graph_clear':self.graph_edit_sequence([],'Clear '+self.graph_field)
        elif action=='graph_rate':
            rate=self.editor.song.instruments[self.editor.instrument].arp_speed
            self.editor.edit('Set arp rate',[(('instruments',self.editor.instrument,'arp_speed'),clamp(rate+value,1,255))])
        else:return False
        return True
