"""PCM sample controls. Waveform thumbnails are cached, never decoded per frame."""
import pygame as pg
from .instrument_graphs import button
from sidpulse.song.model import note_name


def experimental_warning(r, top):
    """Keep the C64 caveat directly under the sample page title, at any zoom."""
    from . import renderer as c
    import textwrap
    lines = textwrap.wrap('C64 PCM playback is experimental. Results may vary, and playback bugs '
                          'may occur on a real Commodore 64.', max(20, r.cols - 7))
    icon = pg.Rect(round(2*r.cw), round((top-1)*r.rh), r.rh-2, r.rh-2)
    pg.draw.polygon(r.screen, c.YELLOW, (icon.midtop, icon.bottomleft, icon.bottomright))
    mark = r.small_font.render('!', True, c.BG)
    r.screen.blit(mark, mark.get_rect(midbottom=(icon.centerx, icon.bottom)))
    for i, line in enumerate(lines):
        r.text(5, top-1+i, line, c.YELLOW, r.cols-7)
    return top + len(lines)


def details(r, app, left, top, bottom):
    from . import renderer as c
    from sidpulse.audio.media import PLAYABLE_ENCODINGS, sample_bounds
    slot = app.sample_index
    sample = app.selected_sample()
    width = r.cols - left - 2
    short = bottom-top < 24
    step = 1.15 if short else 1.5
    height = 1.0 if short else 1.3
    r.text(left, top, f'PCM SAMPLE {slot:02d}', c.TEXT, width)
    button(r, left + 17, top, 4, '<', 'sample_slot_move', -1)
    button(r, left + 22, top, 4, '>', 'sample_slot_move', 1)
    toggle_width = min(32, width)
    # Narrow views also have sample monitor buttons in the header. Give the
    # import preference its own row there, without overlapping either control.
    compact = width < 66
    button(r, left + width - toggle_width, top + (1.5 if compact else 0), toggle_width,
           ('[x] ' if app.sample_auto_squeeze else '[ ] ') + 'Auto-squeeze on import',
           'sample_auto_squeeze', selected=app.sample_auto_squeeze)
    if compact:
        top += 1.5
    bw = min(30, (width - 1) / 2)
    controls = (('Import / replace...', 'import_sample'), ('Assign instrument...', 'assign_sample'),
                ('Play sample', 'preview_sample'), ('Delete sample', 'delete_sample'),
                ('Squeeze...', 'sample_squeeze'), ('Restore original', 'sample_restore'),
                ('Normalize...', 'sample_normalize'), ('Adjust volume...', 'sample_volume'))
    for i, (label, action) in enumerate(controls):
        button(r, left + (bw + 1) * (i % 2), top + 2 + step * (i // 2), bw, label, action,height=height)
    synthesis_y=top+2+step*4
    button(r, left, synthesis_y, min(width, 62), 'Synthesize audio (create wavetable)...', 'sample_synthesis',height=height)
    nw = (width - 1) / 2
    stacked = nw < 33
    for i, when in enumerate(('before', 'after')):
        enabled = getattr(app, 'sample_normalize_' + when)
        button(r, left if stacked else left + (nw + 1) * i,
               synthesis_y + step + (step * i if stacked else 0), width if stacked else nw,
               ('[x] ' if enabled else '[ ] ') + f'Normalize {when} squeezing',
               'sample_normalization', when, enabled,height=height)
    info_y=synthesis_y+step*(3 if stacked else 2)+.5
    if isinstance(sample, dict) and sample.get('encoding') in PLAYABLE_ENCODINGS:
        rate, frames = sample['sample_rate'], sample['frames']
        bits = {'pcm_s16le_mono':16, 'pcm_s8_mono':8, 'pcm_u4le_mono':4}[sample['encoding']]
        start, end = sample_bounds(sample)
        if app.sample_drag and app.sample_drag['slot'] == slot:
            start, end = app.sample_drag['start'], app.sample_drag['end']
        r.text(left, info_y, sample['name'], c.YELLOW, width)
        r.text(left, info_y+1, f'{rate:,} Hz / {bits}-bit / {(frames * bits + 7) // 8:,} bytes / {frames / rate:.3f}s', c.TEXT, width)
        wave_y=info_y+(2.5 if short else 3)
        wave_height = max(2, bottom-wave_y-5)
        rect = r.well(left, wave_y, width, wave_height).inflate(-4, -4)
        sx = rect.left + start * (rect.width - 1) / frames
        ex = rect.left + end * (rect.width - 1) / frames
        pg.draw.rect(r.screen, c.SELECT, pg.Rect(sx, rect.top, max(1, ex-sx), rect.height))
        cached = getattr(r, '_sample_preview', None)
        # Bounds edits share immutable PCM; dragging never rebuilds the waveform.
        identity = (id(sample['data']), sample['encoding'])
        if cached is None or cached[0] != identity:
            import numpy as np
            from sidpulse.audio.media import sample_data
            values = np.frombuffer(sample_data(sample), '<i2')
            buckets = np.array_split(values, min(512, len(values)))
            peaks = tuple((int(b.min()) / 32768, int(b.max()) / 32768) for b in buckets)
            cached = r._sample_preview = (identity, peaks, sample['data'])
        peaks = cached[1]
        # Cache the raster as well as the peaks. Only the selection and marker
        # overlays change while dragging; no 512-line Python loop per frame.
        bitmap_key = (identity, rect.size, c.CREAM)
        bitmap_cache = getattr(r, '_sample_bitmap', None)
        if bitmap_cache is None or bitmap_cache[0] != bitmap_key:
            bitmap = pg.Surface(rect.size, pg.SRCALPHA).convert_alpha()
            for i, (low, high) in enumerate(peaks):
                x = i * (rect.width - 1) / max(1, len(peaks) - 1)
                pg.draw.line(bitmap, c.CREAM, (x, rect.height//2 - high * (rect.height - 6) / 2),
                             (x, rect.height//2 - low * (rect.height - 6) / 2))
            bitmap_cache = r._sample_bitmap = (bitmap_key, bitmap)
        r.screen.blit(bitmap_cache[1], rect.topleft)
        for x, field, label in ((sx, 'start', 'START'), (ex, 'end', 'END')):
            pg.draw.line(r.screen, c.YELLOW, (x, rect.top), (x, rect.bottom - 1), 2)
            pg.draw.polygon(r.screen, c.YELLOW, [(x-5, rect.top), (x+5, rect.top), (x, rect.top+8)])
            tx = max(rect.left, min(x + 3, rect.right - len(label)*r.cw))
            r.screen.blit(r.small_font.render(label, True, c.YELLOW), (tx, rect.top + 9))
            hit = pg.Rect(round(x) - 9, rect.top, 18, rect.height)
            r.hits.append((hit, 'sample_marker', {'rect':rect, 'field':field}))
        y = wave_y + wave_height + .5
        for i, (field, value) in enumerate((('start', start), ('end', end))):
            button(r, left + i * (bw + 1), y, bw,
                   f'{field.title()}: {value}', 'sample_range', field,height=height)
        button(r, left, y + step, bw, 'Root: ' + note_name(sample.get('root_note', 48)), 'sample_root',height=height)
        r.text(left+bw+1, y+step, f'{(end-start)/rate:.3f}s / {end-start:,} frames', c.TEXT, bw)
    else:
        r.text(left, info_y, 'Import WAV / MP3 / FLAC / OGG / AIFF / M4A.', c.TEXT, width)
        r.text(left, info_y+2, 'Instrument 01 and Sample 01 can coexist.', c.TEXT, width)
    if not short:
        r.text(left, bottom - 2, 'Drag markers | Click values | Ctrl+Backspace: undo', c.TEXT, width)


def instrument(r, app, left, top, bottom):
    from . import renderer as c
    inst = app.editor.song.instruments[app.editor.instrument]
    width = r.cols - left - 2
    button(r, left, top, min(44, width), 'Unmap sample from this instrument' if inst.sample_override else 'Override with sample',
           'pcm_setting', 'sample_override')
    button(r, left, top + 2, min(34, width), f'Sample slot: {inst.sample_slot:02d}', 'pcm_setting', 'sample_slot')
    button(r, left, top + 4, min(34, width), f'Sample gain: {inst.sample_gain}%', 'pcm_setting', 'sample_gain')
    button(r, left, top + 6, min(34, width), 'Import into this slot...', 'import_instrument_sample')
    button(r, left, top + 8, min(34, width), 'Open sample editor (F3)', 'open_instrument_sample')
    sample = app.editor.song.samples.get(str(inst.sample_slot), app.editor.song.samples.get(inst.sample_slot))
    lines = [sample.get('name', 'Stored sample') if sample else 'No sample assigned: override will be silent.',
             'Pattern instrument numbers stay the same.', 'This channel plays PCM in place of SID synthesis.',
             'Root note: F3. Note pitch changes sample speed.',
             'Pitch/arp/vibrato/retrigger/gate commands still work.',
             'SID settings are saved; unmap to edit them again.',
             'C64 PCM: one tracker channel auto-mapped to CH3, ~4 kHz / 4-bit.',
             'DIGI #1: display on; #2: off. WAV/MP3 keeps host quality.']
    import textwrap
    y = top + 10
    for line in lines:
        for part in textwrap.wrap(line, max(10, int(width))):
            if y < bottom:
                r.text(left, y, part, c.TEXT, width)
            y += 1


def draw_squeeze(r, app):
    from . import renderer as c
    d = app.dialog
    r.hits = []
    w = min(66, r.cols - 4); x = (r.cols-w)/2; y = max(1, (r.lines-20)/2)
    r.panel(x, y, w, 20, 'Squeeze PCM sample')
    r.text(x+2, y+2, 'Selected range only. Original remains restorable.', c.TEXT, w-4)
    button(r,x+2,y+4,w-4,f'Sample rate: {d["rate"]:,} Hz','squeeze_setting','rate',d['focus']==0)
    button(r,x+2,y+6,w-4,f'Bit depth: {d["bits"]} bits','squeeze_setting','bits',d['focus']==1)
    for i, when in enumerate(('before', 'after')):
        button(r,x+2,y+8+i*2,w-4,('[x] ' if d['normalize_'+when] else '[ ] ')+f'Normalize {when} squeezing',
               'squeeze_normalization',when,d['focus']==i+2)
    r.text(x+2,y+12,'Normalize before: use the available quantizer range.',c.TEXT,w-4)
    r.text(x+2,y+13,'After: restore peak level at the chosen bit depth.',c.TEXT,w-4)
    r.text(x+2,y+14,'4-bit / 4,000 Hz = about 2,000 packed bytes/sec.',c.TEXT,w-4)
    button(r,x+2,y+16,18,'Squeeze','squeeze_apply',selected=d['focus']==4)
    button(r,x+22,y+16,16,'Cancel','squeeze_cancel',selected=d['focus']==5)
    r.text(x+2,y+18,'Tab/arrows: select | Enter: edit/apply | Esc: cancel',c.TEXT,w-4)


def squeeze_event(app, event):
    import pygame as pg
    d=app.dialog
    def action(name, value=None):
        if name=='squeeze_cancel':app.dialog=None
        elif name=='squeeze_apply':app.apply_sample_squeeze()
        elif name=='squeeze_normalization':
            app.toggle_sample_normalization(value)
            d['normalize_'+value]=getattr(app,'sample_normalize_'+value)
        elif name=='squeeze_setting':
            def accept(text):
                number=int(text)
                if value=='rate' and not 1000<=number<=48000:raise ValueError('Use 1000..48000 Hz.')
                if value=='bits' and number not in (4,8,16):raise ValueError('Use 4, 8 or 16 bits.')
                d[value]=number
            app.text_dialog('Squeeze '+value,str(d[value]),accept,'Rate: 1000..48000 Hz. Depth: 4, 8 or 16 bits.')
            app.dialog['return_dialog']=d
    if event.type==pg.MOUSEBUTTONDOWN and event.button==1:
        for rect,name,value in reversed(app.renderer.hits):
            if rect.collidepoint(event.pos):action(name,value);return
    elif event.type==pg.KEYDOWN:
        if event.key==pg.K_ESCAPE:app.dialog=None
        elif event.key in (pg.K_TAB,pg.K_UP,pg.K_DOWN):d['focus']=(d['focus']+(-1 if event.key==pg.K_UP or event.mod&pg.KMOD_SHIFT else 1))%6
        elif event.key in (pg.K_LEFT,pg.K_RIGHT) and d['focus']<2:
            key='rate' if d['focus']==0 else 'bits'
            options=(4000,6000,8000,11025,22050,44100,48000) if key=='rate' else (4,8,16)
            index=options.index(d[key]) if d[key] in options else 0
            d[key]=options[(index+(-1 if event.key==pg.K_LEFT else 1))%len(options)]
        elif event.key in (pg.K_RETURN,pg.K_SPACE):
            name,value=(('squeeze_setting','rate'),('squeeze_setting','bits'),('squeeze_normalization','before'),
                        ('squeeze_normalization','after'),('squeeze_apply',None),('squeeze_cancel',None))[d['focus']]
            action(name,value)
