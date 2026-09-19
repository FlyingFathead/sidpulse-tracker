"""Staged SID/PRG-only export options, metrics and project-save continuation."""
from dataclasses import replace
import textwrap
from time import monotonic

import pygame as pg

from sidpulse.export.analysis_job import AnalysisJob, comparison_worker
from sidpulse.export.comparison import Comparison
from sidpulse.export.squeeze import SQUEEZER_VERSIONS, squeezer_version_label
from sidpulse.preferences import (load_squeeze_options, save_squeeze_options,
                                  load_squeeze_comparison, load_squeeze_show_all_versions,
                                  save_preferences)
from sidpulse.ui.fonts import default_font_path
from sidpulse.ui.instrument_graphs import button_frame
from sidpulse.ui.themes import palette
from sidpulse.ui.squeezer_comparison import visible_entries, comparison_columns
from sidpulse.ui.scrollbar import handle_scrollbar, draw_scrollbar

OPTIONS = (
    ('enabled', 'Squeeze song'),
    ('patterns', 'Condense duplicate patterns'),
    ('instruments', 'Condense identical instruments'),
    ('unused', 'Discard unused patterns, instruments and samples'),
    ('streams', 'Pack repeated voice/timing data; choose smaller player'),
)
BUTTONS = (('Analyze', 'analyze'), ('Save + export', 'save'),
           ('Export only', 'export'), ('Cancel', 'cancel'))


def open_dialog(app, kind='sid'):
    if kind not in ('sid', 'prg'):
        raise ValueError('Squeezer applies only to SID and PRG exports')
    # An explicit second open supersedes any unfinished analysis, including one
    # temporarily hidden beneath another modal. Its late result is discarded.
    for job in app.export_jobs:
        job.cancel()
    app.release_audition()
    pg.key.stop_text_input()
    app.dialog = {'kind': 'export_squeezer', 'title': f'Export {kind.upper()} / SIDpulse Tracker File Squeezer',
                  'target': kind, 'options': load_squeeze_options(), 'focus': 8,
                  'result': None, 'source': None, 'scroll': 0, 'ensure_focus': False,
                  'compare': load_squeeze_comparison(), 'comparison': None,
                  'show_all_versions': load_squeeze_show_all_versions()}
    analyze(app)


def analyze(app, *, continue_action=None):
    """Schedule work; the menu/key handler must never run the compiler."""
    dialog = app.dialog
    if dialog.get('busy'):
        return
    dialog['version_open']=False
    dialog.pop('error', None)
    dialog['result'] = None
    dialog['source'] = None
    dialog['comparison'] = None
    dialog['busy'] = True
    dialog['pending_action'] = continue_action
    dialog['analysis_started'] = monotonic()
    dialog['analysis_drawn'] = False
    dialog['phase'] = 'Pre-analyzing...'
    dialog['detail'] = 'Preparing an isolated song snapshot.'
    dialog['focus'] = 8  # Cancel remains the safe, immediately usable action.
    compare = dialog.get('compare', True) and dialog['options'].enabled
    job = AnalysisJob(app.editor.song, dialog['options'], dialog['target'],
                      **({'worker': comparison_worker} if compare else {}))
    dialog['job'] = job
    app.export_jobs.append(job)


def poll_analysis(app):
    """Called by the UI after drawing/flipping a frame, never by the worker."""
    dialog = app.dialog
    # A notice can temporarily wrap the export modal. Other replacements (e.g.
    # the existing quit prompt) abandon it, so cancel those orphan jobs promptly.
    reachable, visited = set(), set()
    view = dialog
    while isinstance(view, dict) and id(view) not in visited:
        visited.add(id(view))
        if view.get('kind') == 'export_squeezer' and view.get('job') is not None:
            reachable.add(view['job'])
        view = view.get('return_dialog')
    for job in app.export_jobs:
        if job not in reachable or not app.running:
            job.cancel()
    if dialog is not None and dialog.get('kind') == 'export_squeezer' and app.running:
        job = dialog.get('job')
        if job is not None:
            # Even a slow process launch cannot hide the first progress frame.
            if dialog.get('analysis_drawn') and not job.started:
                job.start()
            update = job.poll()
            dialog['phase'], dialog['detail'] = update.phase, update.detail
            if update.done:
                dialog.pop('job', None)
                dialog['busy'] = False
                action = dialog.pop('pending_action', None)
                if update.cancelled:
                    dialog['error'] = 'Analysis cancelled. No file was written.'
                elif update.error:
                    dialog['error'] = update.error
                elif update.source != app.editor.song:
                    dialog['error'] = 'The song changed during analysis. Analyze again before exporting.'
                else:
                    dialog['source'] = update.source
                    if isinstance(update.result, Comparison):
                        dialog['comparison'] = update.result
                        best = update.result.preferred(dialog['options'].version)
                        if best is not None:
                            dialog['options'] = replace(dialog['options'], version=best.version)
                            dialog['result'] = best.result
                        else:
                            dialog['error'] = 'No version fits the export memory budget. The project is unchanged.'
                    else:
                        dialog['result'] = update.result
                    if action and dialog['result'] is not None:
                        activate(app, action)
    # Jobs belonging to a dismissed modal are never allowed to deliver into a
    # newer one. Their coordinator owns termination/joins off the UI thread.
    app.export_jobs[:] = [job for job in app.export_jobs if not job.poll().done]


def close_analysis(app):
    """Shutdown hook, including jobs hidden underneath a notice/quit dialog."""
    for job in app.export_jobs:
        job.cancel()
    for job in app.export_jobs:
        if not job.close():
            import logging
            logging.getLogger('sidpulse.export.analysis').error('Export worker shutdown timed out')
    app.export_jobs.clear()


def toggle(app, index):
    dialog = app.dialog
    if dialog.get('busy'):
        return
    options = dialog['options']
    if index and not options.enabled:
        return
    field = OPTIONS[index][0]
    dialog['options'] = replace(options, **{field: not getattr(options, field)})
    dialog['result'] = None
    dialog['comparison'] = None
    dialog.pop('error', None)
    dialog['focus'] = index
    if not dialog['options'].enabled:dialog['version_open']=False


def select_version(app,version):
    dialog=app.dialog
    if dialog.get('busy') or not dialog['options'].enabled:return
    dialog['options']=replace(dialog['options'],version=version)
    comparison = dialog.get('comparison')
    entry = next((e for e in comparison.entries if e.version==version), None) if comparison else None
    if entry is not None and dialog.get('source') == app.editor.song:
        dialog['result'] = entry.result
    else:
        dialog['result']=dialog['source']=None
        dialog['comparison'] = None
    dialog.pop('error',None)
    if entry is not None and entry.error: dialog['error'] = entry.error
    dialog['version_open']=False
    dialog['focus']=9


def toggle_comparison(app):
    dialog = app.dialog
    if dialog.get('busy') or not dialog['options'].enabled: return
    dialog['compare'] = not dialog.get('compare', True)
    dialog['comparison'] = dialog['result'] = dialog['source'] = None
    dialog.pop('error', None)
    dialog['focus'] = 10


def toggle_all_versions(app):
    dialog = app.dialog
    if dialog.get('busy') or dialog.get('comparison') is None: return
    show_all = not dialog.get('show_all_versions', True)
    try:
        save_preferences({'export_show_all_versions': show_all})
    except OSError as exc:
        dialog['error'] = 'Could not save export display preference: ' + str(exc)
        return
    dialog['show_all_versions'] = show_all
    dialog['focus'] = 20
    dialog['ensure_focus'] = True



def activate(app, action):
    dialog = app.dialog
    if action == 'cancel':
        job = dialog.pop('job', None)
        if job is not None:
            job.cancel()
        dialog['pending_action'] = None
        app.dialog = None
        app.after_save = None
        app.sync_file_text_input()
        return
    if dialog.get('busy'):
        return
    if action == 'analyze':
        analyze(app)
        return
    if dialog['result'] is None or dialog['source'] != app.editor.song:
        analyze(app, continue_action=action)
        return
    result = dialog['result']
    if result is None:
        return
    try:
        save_squeeze_options(dialog['options'])
        save_preferences({'export_compare_squeezers': dialog.get('compare', True)})
    except OSError as exc:
        dialog['error'] = 'Could not save export preferences: ' + str(exc)
        return
    kind = dialog['target']
    app.dialog = None
    try:
        if action == 'save':
            app.after_save = lambda: app.prompt_export(result, kind)
            app.save_project()
        else:
            app.prompt_export(result, kind)
    except (OSError, ValueError) as exc:
        # Completion is polled outside App.handle's exception guard. Keep a
        # failed native save/browser continuation recoverable in either path.
        app.after_save = None
        dialog['error'] = 'Could not continue export: ' + str(exc)
        app.dialog = dialog
        app.sync_file_text_input()


def handle_event(app, event):
    dialog = app.dialog
    if handle_scrollbar(dialog,event):
        dialog['version_open'] = False
        return
    if event.type == pg.MOUSEWHEEL:
        dialog['scroll'] -= event.y * dialog.get('line_height', 20) * 3
    elif event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
        for rect, action, value in reversed(app.renderer.hits):
            if rect.collidepoint(event.pos):
                if action == 'squeeze_option':
                    toggle(app, value)
                elif action == 'squeeze_button':
                    activate(app, value)
                elif action == 'squeeze_version':
                    dialog['version_open']=not dialog.get('version_open',False)
                    dialog['version_choice']=dialog['options'].version
                    dialog['focus']=9
                elif action == 'squeeze_version_pick':select_version(app,value)
                elif action == 'squeeze_compare':toggle_comparison(app)
                elif action == 'squeeze_show_all':toggle_all_versions(app)
                elif action == 'squeeze_use_version':
                    select_version(app,value)
                    dialog['focus']=11+next(i for i,e in enumerate(visible_entries(dialog)) if e.version==value)
                return
        dialog['version_open']=False
    elif event.type == pg.KEYDOWN:
        key = event.key
        if dialog.get('version_open'):
            if key==pg.K_ESCAPE:dialog['version_open']=False
            elif key in (pg.K_UP,pg.K_DOWN,pg.K_LEFT,pg.K_RIGHT):
                position=SQUEEZER_VERSIONS.index(dialog.get('version_choice',dialog['options'].version))
                direction=-1 if key in (pg.K_UP,pg.K_LEFT) else 1
                dialog['version_choice']=SQUEEZER_VERSIONS[(position+direction)%len(SQUEEZER_VERSIONS)]
            elif key in (pg.K_RETURN,pg.K_KP_ENTER,pg.K_SPACE):
                select_version(app,dialog.get('version_choice',dialog['options'].version))
            elif key==pg.K_TAB:dialog['version_open']=False
            return
        if key == pg.K_ESCAPE:
            activate(app, 'cancel')
        elif key in (pg.K_a, pg.K_s, pg.K_e):
            activate(app, {pg.K_a: 'analyze', pg.K_s: 'save', pg.K_e: 'export'}[key])
        elif key in (pg.K_TAB, pg.K_DOWN, pg.K_UP, pg.K_LEFT, pg.K_RIGHT):
            choices = ([20]+[11+i for i,e in enumerate(visible_entries(dialog)) if e.result is not None]
                       if dialog.get('comparison') else [])
            available = [8] if dialog.get('busy') else ([0,9,10,*range(1,5),*choices,*range(5,9)] if dialog['options'].enabled else [0, 5, 6, 7, 8])
            step = -1 if key in (pg.K_UP, pg.K_LEFT) or (key == pg.K_TAB and getattr(event, 'mod', 0) & pg.KMOD_SHIFT) else 1
            position = available.index(dialog['focus']) if dialog['focus'] in available else 0
            dialog['focus'] = available[(position + step) % len(available)]
            dialog['ensure_focus'] = True
        elif key in (pg.K_RETURN, pg.K_KP_ENTER, pg.K_SPACE):
            index = dialog['focus']
            if index==9:
                dialog['version_open']=True;dialog['version_choice']=dialog['options'].version
            elif index==10:toggle_comparison(app)
            elif index==20:toggle_all_versions(app)
            elif index>=11 and dialog.get('comparison'):
                version=visible_entries(dialog)[index-11].version
                select_version(app,version)
                dialog['focus']=11+next(i for i,e in enumerate(visible_entries(dialog)) if e.version==version)
            elif index < 5:
                toggle(app, index)
            else:
                activate(app, BUTTONS[index - 5][1])
        elif key in (pg.K_HOME, pg.K_END):
            dialog['scroll'] = 0 if key==pg.K_HOME else dialog.get('scroll_max',0)
            dialog['ensure_focus'] = False
        elif key in (pg.K_PAGEUP, pg.K_PAGEDOWN):
            dialog['scroll'] += (-1 if key == pg.K_PAGEUP else 1) * dialog.get('line_height', 20) * 5


def draw_progress(screen, rect, colors, elapsed):
    """Indeterminate activity, not a made-up percentage or a draggable slider."""
    pg.draw.rect(screen, colors['WELL'], rect)
    pg.draw.line(screen, colors['EDGE'], rect.topleft, rect.topright, 2)
    pg.draw.line(screen, colors['EDGE'], rect.topleft, rect.bottomleft, 2)
    pg.draw.line(screen, colors['CREAM'], rect.bottomleft, rect.bottomright, 2)
    pg.draw.line(screen, colors['CREAM'], rect.topright, rect.bottomright, 2)
    inner = rect.inflate(-6, -6)
    if inner.width <= 0 or inner.height <= 0:
        return
    segment_width = max(1, inner.width // 4)
    # A solid slider-colour segment sweeps back and forth. No knob, ticks, or %.
    travel = 1.0 - abs((max(0.0, elapsed) % 2.4) / 1.2 - 1.0)
    segment = pg.Rect(inner.x + round((inner.width - segment_width) * travel),
                      inner.y, segment_width, inner.height)
    pg.draw.rect(screen, colors['SLIDER'], segment)


def draw(r, app):
    """Pixel-bounded modal; body scrolls instead of losing controls at high zoom."""
    dialog = app.dialog
    colors = palette(app.appearance)
    screen = r.screen
    r.hits = []
    shade = pg.Surface(screen.get_size(), pg.SRCALPHA)
    shade.fill((0, 0, 0, 175))
    screen.blit(shade, (0, 0))
    width = min(screen.get_width() - 16, max(620, min(1000, 88 * r.cw)))
    size = max(10, min(r.layout.font_size, 18, round(width / 54)))
    face = pg.font.Font(default_font_path(), size)
    face.set_bold(True)
    small = pg.font.Font(default_font_path(), max(10, size - 2))
    line_height = face.get_linesize() + 4
    dialog['line_height'] = line_height
    columns = 4 if width >= 620 else 2
    button_rows = 4 // columns
    footer = (button_rows + 2) * line_height
    body_lines = 33 if dialog.get('compare', True) and dialog.get('comparison') else 23
    frame = pg.Rect(0, 0, width, min(screen.get_height() - 16, body_lines * line_height + footer))
    frame.center = screen.get_rect().center
    pg.draw.rect(screen, colors['PANEL'], frame)
    pg.draw.rect(screen, colors['TEXT'], frame, 1)
    inner = frame.inflate(-24, -12)
    title = face.render(f'SIDpulse Tracker / SQUEEZER v{squeezer_version_label(dialog["options"].version)}', True, colors['TEXT'])
    header_clip = screen.get_clip()
    screen.set_clip(inner)
    screen.blit(title, (inner.x, inner.y))
    sub = small.render(f'{dialog["target"].upper()} export only. Editable .sidpulse and preview are unchanged.', True, colors['TEXT'])
    screen.blit(sub, (inner.x, inner.y + line_height))
    screen.set_clip(header_clip)
    busy = dialog.get('busy', False)
    progress_height = 3 * line_height if busy else 0
    if busy:
        elapsed = max(0.0, monotonic() - dialog['analysis_started'])
        area = pg.Rect(inner.x, inner.y + 2 * line_height, inner.width, progress_height)
        screen.set_clip(area)
        timer = small.render(f'{elapsed:.1f}s elapsed', True, colors['TEXT'])
        phase = face.render(dialog.get('phase', 'Pre-analyzing...'), True, colors['TEXT'])
        phase_clip = pg.Rect(area.x, area.y, max(1, area.width - timer.get_width() - 12), line_height)
        screen.set_clip(phase_clip)
        screen.blit(phase, (area.x, area.y))
        screen.set_clip(area)
        screen.blit(timer, (area.right - timer.get_width(), area.y))
        bar = pg.Rect(area.x, area.y + line_height, area.width, max(12, line_height - 4))
        draw_progress(screen, bar, colors, elapsed)
        detail = small.render(dialog.get('detail', ''), True, colors['TEXT'])
        screen.blit(detail, (area.x, area.y + 2 * line_height))
        screen.set_clip(header_clip)
        dialog['progress_rect'] = bar
        dialog['analysis_drawn'] = True
    else:
        dialog.pop('progress_rect', None)
    body = pg.Rect(inner.x, inner.y + 2 * line_height + progress_height + 6, inner.width,
                   max(line_height, inner.height - footer - 2 * line_height - progress_height - 6))
    scrollbar_track = pg.Rect(body.right-14,body.y,14,body.height)
    body.width -= 22
    capacity = max(20, body.width // max(1, face.size('M')[0]))
    rows, option_bounds = [], {}
    position = 0

    def add(text, color=None, option=None):
        nonlocal position
        begin = position
        for line in textwrap.wrap(text, capacity, break_long_words=True) or ['']:
            rows.append((position, line, colors['TEXT'] if color is None else color))
            position += line_height
        if option is not None:
            option_bounds[option] = (begin, position)
        position += 3

    for index, (field, label) in enumerate(OPTIONS):
        checked = getattr(dialog['options'], field)
        enabled = not busy and (index == 0 or dialog['options'].enabled)
        add(('' if index == 0 else '  ') + ('[x] ' if checked else '[ ] ') + label,
            colors['TEXT'] if enabled else colors['DIM'], index)
        if index==0 and dialog['options'].enabled:
            add(f'  Squeezer version: [ v{squeezer_version_label(dialog["options"].version)}  ▾ ]',
                colors['DIM'] if busy else colors['TEXT'],9)
            add('  '+('[x] ' if dialog.get('compare', True) else '[ ] ')+'Compare available versions',
                colors['DIM'] if busy else colors['TEXT'],10)
    position += line_height // 2
    comparison_top = None
    if dialog.get('compare', True) and dialog.get('comparison') is not None:
        entries = visible_entries(dialog)
        add('All versions: ranked by file size, RAM, then cycles' if dialog.get('show_all_versions', True) else
            'Top 3: ranked by file size, RAM, then cycles')
        add(('[x] ' if dialog.get('show_all_versions', True) else '[ ] ')+'Show all versions', option=20)
        if dialog.get('result') is not None and not any(e.version==dialog['options'].version for e in entries):
            add(f'Selected v{squeezer_version_label(dialog["options"].version)} is outside Top 3. Show all to compare it.')
        leaders = dialog['comparison'].leaders
        if len(leaders)>1:
            measured = all(e.result.squeeze_report.verified_max_cycles for e in leaders)
            add('Joint best: '+('same size, RAM and measured cycles.' if measured else 'tied on available measurements; CPU unmeasured.'))
            add('Current version kept if tied; otherwise the newest tied version is selected.')
        comparison_top = position
        card_columns = comparison_columns(dialog, body.width)
        comparison_rows = (len(entries)+card_columns-1)//card_columns
        position += 9*line_height*comparison_rows
        for index,entry in enumerate(entries):
            if entry.result is not None:
                option_bounds[11+index] = (comparison_top+(index//card_columns*9+6)*line_height,
                                         comparison_top+(index//card_columns*9+8)*line_height)
        add('File/RAM: bytes. CPU: measured maximum C64 cycles/call; lower is better.')
        add('CPU excludes VIC/IRQ overhead. A dash means no measured result.')
    result = dialog['result']
    if result is not None:
        report = result.squeeze_report
        original_file = report.original_payload_bytes + report.original_wrapper_bytes + (2 if dialog['target'] == 'prg' else 124)
        percent = 100 * report.saved_bytes / original_file if original_file else 0
        add(f'File: {original_file:,} -> {len(result.data):,} bytes ({percent:.1f}% saved)')
        add(f'Resident RAM: {report.original_resident_bytes:,} -> {report.resident_bytes:,} bytes')
        add(f'Player/state: {report.player_bytes:,} | Song: {report.song_data_bytes:,} | Wrapper: {report.wrapper_bytes:,}')
        add(f'Zero page: {report.zero_page_bytes} | Stack: <= {report.stack_bytes} | {report.algorithm}')
        add(('Packed tick/write verification passed. ' if report.verified_calls else 'Legacy replay selected. ') +
            f'Conservative maximum: {result.max_cycles_bound:,} cycles/call.')
        if report.fallback_reason:
            add(report.fallback_reason)
        counts = report.cleanup
        add(f'Export-copy cleanup: {counts.duplicate_patterns} duplicate patterns, '
            f'{counts.duplicate_instruments} identical instruments; '
            f'{counts.unused_patterns}/{counts.unused_instruments}/{counts.unused_samples} unused patterns/instruments/samples.')
    elif busy:
        add('Analysis is running. Cancel / Esc stops it without saving or exporting.')
    else:
        add('Choose Analyze to measure these settings, or export to analyze and continue.')
    if dialog.get('error'):
        add(dialog['error'], colors['TEXT'])
    else:
        add('Source banks are not stored in the old export either. The main RAM saving comes from packed playback data.')
        add('S: save the editable project + export | E: export only | A: analyze')
    if dialog.pop('ensure_focus', False) and dialog['focus'] in option_bounds:
        start, end = option_bounds[dialog['focus']]
        if start < dialog['scroll']:
            dialog['scroll'] = start
        elif end > dialog['scroll'] + body.height:
            dialog['scroll'] = end - body.height
    dialog['scroll'] = max(0, min(max(0, position - body.height), dialog['scroll']))
    old_clip = screen.get_clip()
    screen.set_clip(body)
    for offset, line, color in rows:
        screen.blit(face.render(line, True, color), (body.x, body.y + offset - dialog['scroll']))
    for index, (begin, end) in option_bounds.items():
        rect = pg.Rect(body.x, body.y + begin - dialog['scroll'], body.width, end - begin)
        if dialog['focus'] == index and (index<11 or index==20):
            pg.draw.rect(screen, colors['TEXT'], rect, 1)
        hit = rect.clip(body)
        if hit.height and not busy and (index<11 or index==20):
            action = 'squeeze_show_all' if index==20 else 'squeeze_version' if index==9 else 'squeeze_compare' if index==10 else 'squeeze_option'
            r.hits.append((hit, action, index))
    if comparison_top is not None:
        from sidpulse.ui.squeezer_comparison import draw_comparison
        draw_comparison(r, app, pg.Rect(body.x, body.y+comparison_top-dialog['scroll'], body.width, 8*line_height),
                        small, line_height, colors, body)
    screen.set_clip(old_clip)
    draw_scrollbar(r,dialog,scrollbar_track,position,body.height,colors, prefix="squeeze_scroll")
    top = inner.bottom - footer + line_height
    bw = (inner.width - (columns - 1) * 8) / columns
    for index, (label, action) in enumerate(BUTTONS):
        rect = pg.Rect(round(inner.x + (index % columns) * (bw + 8)),
                       top + (index // columns) * (line_height + 4), round(bw), line_height + 1)
        enabled = not busy or action == 'cancel'
        button_frame(r, rect, enabled and dialog['focus'] == index + 5)
        text = small.render(label, True, colors['TEXT'] if enabled else colors['DIM'])
        screen.blit(text, text.get_rect(center=rect.center))
        if enabled:
            r.hits.append((rect, 'squeeze_button', action))
    hint = small.render('Analyzing in background | Esc: cancel' if busy else
                        'Tab/arrows: select | Space: toggle | Wheel/PgUp/PgDn: scroll | Esc: cancel',
                        True, colors['TEXT'])
    # The hint may be clipped on tiny windows; all actual controls stay reachable.
    screen.set_clip(inner)
    screen.blit(hint, (inner.x, inner.bottom - small.get_linesize()))
    screen.set_clip(old_clip)
    if dialog.get('version_open') and not busy and 9 in option_bounds:
        start,end=option_bounds[9]
        width=min(body.width,face.size('v2.0.1  (new)')[0]+32)
        left=body.x+min(body.width-width,face.size('  Squeezer version: ')[0])
        top=min(body.bottom-len(SQUEEZER_VERSIONS)*line_height,body.y+end-dialog['scroll'])
        top=max(body.top,top)
        for index,version in enumerate(SQUEEZER_VERSIONS):
            rect=pg.Rect(left,top+index*line_height,width,line_height)
            selected=version==dialog.get('version_choice',dialog['options'].version)
            button_frame(r,rect,selected)
            label=small.render('v'+squeezer_version_label(version)+('  (new)' if version==SQUEEZER_VERSIONS[0] else '  (original)' if version==1 else ''),True,
                               colors['CREAM'] if selected else colors['TEXT'])
            screen.blit(label,label.get_rect(center=rect.center))
            r.hits.append((rect,'squeeze_version_pick',version))
