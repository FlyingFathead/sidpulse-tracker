"""Review and atomically apply sample-to-SID replacements before C64 export."""
from copy import deepcopy
import textwrap
import pygame as pg

from sidpulse.ui.instrument_graphs import button
from sidpulse.ui.themes import palette
from sidpulse.song.model import note_name

ACTIONS = ('sample', 'instrument', 'stop', 'use', 'cancel')


def begin(app, export_dialog):
    app.release_audition()
    app._start_media_job(app.editor.song, {'operation': 'synthesize_all'},
                         assignment={'batch_synthesis': True, 'return_dialog': export_dialog})
    app.dialog['return_dialog'] = export_dialog


def show_result(app, result, assignment, source):
    app.dialog = assignment['return_dialog']
    if source != app.editor.song:
        raise ValueError('The song changed during synthesis. Try again; no instruments were replaced.')
    app.dialog = dict(kind='sample_synthesis_batch', title='Review synthesized instruments',
                      result=result, source=source, return_dialog=assignment['return_dialog'],
                      selected=0, scroll=0, focus='list', button=3)


def activate(app, action):
    d = app.dialog
    if action == 'cancel':
        app.release_audition()
        app.dialog = d['return_dialog']
    elif action == 'stop':
        app.panic()
    elif action == 'use':
        if d['source'] != app.editor.song:
            app.notice('Song changed', 'The song changed after fitting. Cancel and synthesize again; no replacements were applied.', return_dialog=d)
            return
        from sidpulse.project.format import validate
        from sidpulse.ui.export_squeezer import analyze
        instruments = dict(app.editor.song.instruments)
        for proposal in d['result']['proposals']:
            instruments[proposal['number']] = deepcopy(proposal['result']['instrument'])
        probe = deepcopy(app.editor.song)
        probe.instruments = instruments
        validate(probe)
        app.release_audition()
        app.editor.edit('Synthesize all PCM instruments', [(('instruments',), instruments)])
        app.dialog = d['return_dialog']
        app.dialog['pcm'] = False
        app.dialog.pop('pcm_source_channel', None)
        # Reanalyze the fitted song. Export/save remains an explicit action in
        # the original menu, so the user can review ordinary SID export metrics.
        analyze(app)
        app.editor.status = (f'Replaced {len(d["result"]["proposals"])} PCM instruments with frozen SID fits. '
                             'Source samples retained; one Undo restores all. Review export, then save/export.')
    elif action in ('sample', 'instrument'):
        if app.audio.playback.status != 'stopped':
            app.editor.status = 'F8 stops the song for synthesis audition.'
            return
        app.release_audition()
        p = d['result']['proposals'][d['selected']]
        root = p['result']['details']['root_note']
        if action == 'sample':
            bank = d['source'].samples
            source = bank.get(str(p['slot']), bank.get(p['slot']))
            app.audio.send('sample_on', 'synthesis-source', root, source)
        else:
            app.audio.send('on', 'synthesis-result', root, p['result']['instrument'])


def select(d, index):
    d['selected'] = max(0, min(len(d['result']['proposals'])-1, index))
    d['focus'] = 'list'
    d['scroll'] = min(d['scroll'], d['selected'])
    d['scroll'] = max(d['scroll'], d['selected']-d.get('rows', 1)+1)


def handle_event(app, event):
    d = app.dialog
    if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
        for rect, action, value in reversed(app.renderer.hits):
            if not rect.collidepoint(event.pos):
                continue
            if action == 'batch_slot': select(d, value)
            elif action == 'batch_action': activate(app, value)
            return
    elif event.type == pg.MOUSEWHEEL:
        select(d, d['selected']-event.y)
    elif event.type == pg.KEYDOWN:
        key = event.key
        if key == pg.K_ESCAPE: activate(app, 'cancel')
        elif key == pg.K_F8: activate(app, 'stop')
        elif key == pg.K_TAB: d['focus'] = 'buttons' if d['focus'] == 'list' else 'list'
        elif key in (pg.K_HOME, pg.K_END):
            select(d, 0 if key == pg.K_HOME else len(d['result']['proposals'])-1)
        elif key in (pg.K_UP, pg.K_DOWN, pg.K_PAGEUP, pg.K_PAGEDOWN):
            select(d, d['selected']+{pg.K_UP:-1, pg.K_DOWN:1,
                                    pg.K_PAGEUP:-d.get('rows',1), pg.K_PAGEDOWN:d.get('rows',1)}[key])
        elif key in (pg.K_LEFT, pg.K_RIGHT) and d['focus'] == 'buttons':
            d['button'] = (d['button']+(-1 if key == pg.K_LEFT else 1)) % len(ACTIONS)
        elif key in (pg.K_RETURN, pg.K_KP_ENTER, pg.K_SPACE):
            activate(app, ACTIONS[d['button']] if d['focus'] == 'buttons' else 'instrument')


def panel(r, title, height):
    r.hits = []
    shade = pg.Surface(r.screen.get_size(), pg.SRCALPHA)
    shade.fill((0,0,0,175)); r.screen.blit(shade,(0,0))
    w, h = min(84,r.cols-2), min(height,r.lines-2)
    x, y = (r.cols-w)/2, (r.lines-h)/2
    r.panel(x,y,w,h,title)
    return x,y,w,h


def draw_confirm(r, app):
    d = app.dialog; c = palette(app.appearance)
    x,y,w,h = panel(r,d['title'],25)
    px,py = round((x+2.8)*r.cw), round((y+2)*r.rh)
    radius = max(7,round(r.rh*.6))
    pg.draw.polygon(r.screen,c['YELLOW'],[(px,py-radius),(px-radius,py+radius),(px+radius,py+radius)])
    heading = ('DIGI #1: display on / SID mix volume changes' if d.get('digi_method', 1) == 1 else
               'DIGI #2: display and sprites blanked')
    r.text(x+4.5,y+1.6,heading,c['TEXT'],w-7)
    lines = textwrap.wrap(d['message'],max(10,int(w-5)))
    for i,line in enumerate(lines):
        r.text(x+2,y+3.5+i,line,c['TEXT'],w-4)
    from sidpulse.ui.dialogs import choices, focus
    for i,(label,key) in enumerate(choices(d)):
        button(r,x+2,y+h-7+i*1.8,w-4,label,'dialog_button',key,i==focus(d))
    r.text(x+2,y+h-1.2,'Tab / arrows: choose | Enter: activate | Esc: cancel',c['TEXT'],w-4)


def draw(r, app):
    d = app.dialog; c = palette(app.appearance)
    x,y,w,h = panel(r,d['title'],32)
    proposals = d['result']['proposals']
    r.text(x+2,y+2,f'{len(proposals)} PCM instruments -> SID wavetable fits',c['YELLOW'],w-4)
    r.text(x+2,y+3,'Audition replacements. Numbers and source samples stay.',c['TEXT'],w-4)
    bw = (w-6)/3
    for i,(label,action) in enumerate((('Play sample','sample'),('Play instrument','instrument'),('Stop (F8)','stop'))):
        button(r,x+2+i*(bw+1),y+5,bw,label,'batch_action',action,d['focus']=='buttons' and d['button']==i)
    r.text(x+2,y+7,'INST  NAME / SOURCE SAMPLE',c['TEXT'],w-4)
    rows = d['rows'] = max(1,int(h-18))
    d['scroll'] = max(0,min(max(0,len(proposals)-rows),d['scroll']))
    r.well(x+2,y+8,w-4,rows)
    for i,index in enumerate(range(d['scroll'],min(len(proposals),d['scroll']+rows))):
        p = proposals[index]
        if index == d['selected']: r.rect(x+2.2,y+8+i,w-4.4,1,c['SELECT'])
        r.text(x+2.5,y+8+i,f'{p["number"]:02d}    {p["result"]["instrument"].name} / PCM {p["slot"]:02d}',
               c['YELLOW'] if index==d['selected'] else c['CREAM'],w-5)
        r.hit(x+2,y+8+i,w-4,1,'batch_slot',index)
    p = proposals[d['selected']]; info = p['result']['details']
    for i,line in enumerate((f'Sample {p["slot"]:02d}: {info["source_name"]}',
                             f'{info["kind"].title()} fit / {info["model"]} / {note_name(info["root_note"])} / tempo {info["tempo"]}',
                             'Approximation; PCM gain/pitch programs are replaced.',
                             'Apply replaces all listed slots; one Undo restores all.')):
        r.text(x+2,y+h-9+i,line,c['TEXT'],w-4)
    bw = (w-5)/2
    for i,(label,action) in enumerate((('Apply all + review export','use'),('Cancel','cancel'))):
        button(r,x+2+i*(bw+1),y+h-4,bw,label,'batch_action',action,d['focus']=='buttons' and d['button']==i+3)
    r.text(x+2,y+h-2,'Arrows / wheel: instrument | Tab: buttons | Esc: cancel',c['TEXT'],w-4)
