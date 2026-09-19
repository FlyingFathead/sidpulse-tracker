"""Responsive export results; drawing never invokes the compiler."""
import pygame as pg

from sidpulse.export.squeeze import squeezer_version_label
from sidpulse.ui.instrument_graphs import button_frame


def visible_entries(dialog):
    """Rank all completed candidates without rerunning analysis or changing choice."""
    comparison = dialog.get('comparison')
    if comparison is None: return ()
    selected = dialog['options'].version
    def rank(entry):
        result = entry.result
        if result is None: return (float('inf'),)*3 + (True, -entry.version)
        report = result.squeeze_report
        return (len(result.data), report.resident_bytes,
                report.verified_max_cycles or float('inf'),
                entry.version != selected, -entry.version)
    ordered = tuple(sorted(comparison.entries, key=rank))
    if dialog.get('show_all_versions', True): return ordered
    return tuple(entry for entry in ordered if entry.result is not None)[:3]


def comparison_columns(dialog, width):
    limit = (4 if width >= 700 else 2) if dialog.get('show_all_versions', True) else 3
    return max(1, min(len(visible_entries(dialog)), limit))


def draw_comparison(renderer, app, area, face, line_height, colors, viewport):
    dialog = app.dialog; comparison = dialog['comparison']; screen = renderer.screen
    leaders = {entry.version for entry in comparison.leaders}
    valid = [entry for entry in comparison.entries if entry.result is not None]
    metrics = {}
    for entry in valid:
        report = entry.result.squeeze_report
        metrics[entry.version] = (len(entry.result.data), report.resident_bytes,
                                  report.verified_max_cycles or None)
    minima = [min((m[i] for m in metrics.values() if m[i] is not None), default=None) for i in range(3)]
    columns = comparison_columns(dialog, area.width)
    for index,entry in enumerate(visible_entries(dialog)):
        left = area.x+round((index%columns)*area.width/columns)
        right = area.x+round((index%columns+1)*area.width/columns)-4
        column = pg.Rect(left, area.y+(index//columns)*9*line_height, right-left, 8*line_height)
        is_best = entry.version in leaders
        pg.draw.rect(screen, colors['WELL'], column)
        pg.draw.rect(screen, colors['ACCENT'] if is_best else colors['EDGE'], column, 2)
        old_clip = screen.get_clip(); screen.set_clip(column.inflate(-4,-4).clip(viewport))
        def text(value, row, color):
            label = face.render(value, True, color)
            screen.blit(label, label.get_rect(center=(column.centerx, column.y+(row+.5)*line_height)))
        text('v'+squeezer_version_label(entry.version), 0, colors['CREAM'])
        text(('JOINT BEST' if len(leaders)>1 else 'BEST SIZE') if is_best else 'AVAILABLE' if entry.result else 'DOES NOT FIT', 1,
             colors['ACCENT'] if is_best else colors['CREAM'])
        values = metrics.get(entry.version, (None,None,None))
        for row,(label,value,minimum) in enumerate(zip(('File','RAM','CPU'),values,minima),2):
            text(label+': '+(f'{value:,}' if value is not None else '—'), row,
                 colors['ACCENT'] if value is not None and value==minimum else colors['CREAM'])
        button = pg.Rect(column.x+5,column.y+6*line_height,column.width-10,2*line_height-4)
        selected = entry.version==dialog['options'].version and entry.result is not None
        button_frame(renderer, button, selected)
        text('Use Squeezer', 6, colors['TEXT'] if entry.result else colors['DIM'])
        text('v'+squeezer_version_label(entry.version)+(' ✓' if selected else ''), 6.7,
             colors['TEXT'] if entry.result else colors['DIM'])
        if dialog['focus']==11+index: pg.draw.rect(screen, colors['ACCENT'], button.inflate(-4,-4), 1)
        screen.set_clip(old_clip)
        hit = button.clip(viewport)
        if entry.result is not None and hit.width and hit.height:
            renderer.hits.append((hit, 'squeeze_use_version', entry.version))
