"""F11: song order sequence and the complete reusable pattern bank."""
import pygame as pg
from sidpulse.ui.instrument_graphs import button
from sidpulse.ui.themes import palette


def bank_ids(app):
    ids = sorted(app.editor.song.patterns)
    if app.bank_pattern not in ids:
        app.bank_pattern = app.editor.pattern_id if app.editor.pattern_id in ids else ids[0]
    return ids


def move(app, delta=0, edge=None):
    if not commit_entry(app): return
    ed = app.editor
    if app.order_focus == 'bank':
        ids = bank_ids(app)
        index = ids.index(app.bank_pattern) + delta if edge is None else edge
        app.bank_pattern = ids[max(0, min(len(ids)-1, index))]
    else:
        index = app.order_entry_index + delta if edge is None else edge
        app.order_entry_index = max(0, min(min(255,len(ed.song.orders)), index))
        if app.order_entry_index < len(ed.song.orders):
            ed.order = app.order_entry_index
            ed.select_pattern(ed.song.orders[ed.order])


def open_pattern(app):
    if not commit_entry(app): return
    bank_ids(app)
    app.editor.select_pattern(app.bank_pattern)
    app.change_page('pattern')


def begin_entry(app, index=None):
    app.order_focus = 'orders'
    app.order_entry_index = app.order_entry_index if index is None else index
    app.order_draft = ''


def commit_entry(app):
    if app.order_draft is None: return True
    text = app.order_draft
    if text:
        number = int(text)
        if number > 255:
            app.editor.status = 'Pattern number must be 0..255. Escape cancels this edit.'
            return False
        ed = app.editor
        if app.order_entry_index == len(ed.song.orders):
            # Create the referenced pattern and append one order in one undo.
            from copy import deepcopy
            from sidpulse.song.model import Pattern
            patterns = deepcopy(ed.song.patterns)
            patterns.setdefault(number, Pattern())
            ed.edit('Append order', [(("patterns",), patterns), (("orders",), ed.song.orders + [number])])
            ed.order = len(ed.song.orders)-1
            ed.select_pattern(number)
        else:
            ed.order = min(app.order_entry_index, len(ed.song.orders)-1)
            ed.order_edit('set', number)
    app.order_draft = None
    return True


def entry_key(app, event):
    """Consume inline number editing before global Escape/transport commands."""
    if app.order_draft is None: return False
    text = getattr(event, 'unicode', '')
    if event.key == pg.K_ESCAPE:
        app.order_draft = None
    elif event.key == pg.K_RETURN:
        commit_entry(app)
    elif event.key == pg.K_BACKSPACE:
        app.order_draft = app.order_draft[:-1]
    elif len(text)==1 and text in '0123456789' and not event.mod & (pg.KMOD_CTRL|pg.KMOD_ALT):
        if len(app.order_draft)<3: app.order_draft += text
        if len(app.order_draft)==3:
            next_row = min(255, app.order_entry_index+1)
            if commit_entry(app): begin_entry(app,next_row)
    else:
        # Finish a valid number before switching pages, playing, or navigating.
        return not commit_entry(app)
    return True


def handle_key(app, event):
    ed = app.editor
    key = event.key
    if key == pg.K_TAB:
        app.order_focus = 'bank' if app.order_focus == 'orders' else 'orders'
    elif key in (pg.K_UP, pg.K_DOWN, pg.K_PAGEUP, pg.K_PAGEDOWN):
        move(app, {pg.K_UP:-1, pg.K_DOWN:1, pg.K_PAGEUP:-12, pg.K_PAGEDOWN:12}[key])
    elif key in (pg.K_HOME, pg.K_END):
        move(app, edge=0 if key == pg.K_HOME else 255)
    elif app.order_focus == 'bank':
        if key == pg.K_RETURN: open_pattern(app)
    elif key == pg.K_n:
        ed.order = min(app.order_entry_index,len(ed.song.orders)-1)
        ed.order_edit('clone' if event.mod & pg.KMOD_SHIFT else 'new')
        app.order_entry_index = ed.order
    elif key in (pg.K_INSERT, pg.K_DELETE):
        if app.order_entry_index < len(ed.song.orders):
            ed.order = app.order_entry_index
            ed.order_edit('insert' if key == pg.K_INSERT else 'delete')
            app.order_entry_index = ed.order
    elif key == pg.K_RETURN:
        begin_entry(app)
    elif getattr(event,'unicode','') in tuple('0123456789'):
        begin_entry(app)
        entry_key(app,event)


def draw(r, app, top, bottom):
    ed = app.editor; c = palette(app.appearance)
    split = max(22, int(r.cols * .38))
    right = split + 2; width = r.cols-right-1
    button(r, 1, top, 17, 'Order list', 'order_focus', 'orders', app.order_focus=='orders')
    button(r, right, top, min(22,width), 'Pattern bank', 'order_focus', 'bank', app.order_focus=='bank')
    y0 = top + 3.5
    visible = max(1, int(bottom-y0-3))
    r.text(1, top+2, 'Ord', c['TEXT']); r.text(6, top+2, 'Pat', c['TEXT'])
    r.text(12, top+2, 'Name', c['TEXT'], split-13)
    # The order index is outside the recessed pattern-number column.
    r.well(5, y0-.15, 6, visible+.3)
    selected_order = min(app.order_entry_index,min(255,len(ed.song.orders)))
    app.order_entry_index = selected_order
    start = max(0, selected_order-visible+1)
    for n in range(visible):
        i = start+n; y = y0+n
        if i > 255: break
        r.text(1,y,f'{i:03d}',c['TEXT'])
        number = ed.song.orders[i] if i < len(ed.song.orders) else None
        active = i==selected_order
        box = pg.Rect(round(5.2*r.cw),round(y*r.rh),round(5.6*r.cw),r.rh)
        if active: pg.draw.rect(r.screen,c['CREAM'] if app.order_focus=='orders' else c['SELECT'],box)
        color = c['TEXT'] if active and app.order_focus=='orders' else c['YELLOW'] if number is not None else c['DIM']
        value = f'{number:03d}' if number is not None else '---'
        if active and app.order_draft: value = app.order_draft.ljust(3,'_')
        r.control_text(box,value,color)
        if number is not None:
            r.text(12,y,ed.song.patterns[number].name,c['TEXT'],split-13)
            r.hit(1,y,split-1,1,'order',i)
        if i <= len(ed.song.orders): r.hit(5,y,6,1,'order_value',i)
    ids = bank_ids(app); rowx = r.cols-6
    r.text(right,top+2,'Pat   Name',c['TEXT'],width-6)
    r.text(rowx,top+2,'Rows',c['TEXT'],4)
    r.well(right,y0-.15,width,visible+.3)
    start = max(0,ids.index(app.bank_pattern)-visible+1)
    used = set(ed.song.orders)
    for number in ids[start:start+visible]:
        y = y0+ids.index(number)-start
        selected = number==app.bank_pattern
        box = r.rect(right+.2,y,width-.4,1,c['SELECT'] if selected else c['WELL'])
        color = c['CREAM'] if selected else c['ACCENT']
        pattern = ed.song.patterns[number]
        r.control_text(pg.Rect(box.x,box.y,round(5*r.cw),box.height),f'{number:03d}',c['YELLOW'])
        r.text(right+5,y,pattern.name or '(unnamed)',color,width-11)
        r.text(rowx,y,f'{len(pattern.rows):3d}',color,4)
        r.hit(right,y,width,1,'bank_pattern',number)
    chosen = ed.song.patterns[app.bank_pattern]
    y = y0+visible+.65
    label = 'In song' if app.bank_pattern in used else 'Unused'
    r.text(right,y,f'{app.bank_pattern:03d}: {label} | {len(chosen.rows)} rows',c['TEXT'],width)
    r.text(1,y,'Tab: switch panels',c['TEXT'],split-1)
    r.text(1,y+1.15,'3 digits: next order row',c['TEXT'],split-1)
    button(r,right,y+1.15,min(25,width),'Edit pattern (Enter)','bank_open')
