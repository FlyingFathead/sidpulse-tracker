"""Explicit native arpeggio row commands; IT effect letters keep their meaning."""
import pygame as pg


def open_dialog(app, voice):
    app.release_audition()
    app.follow_playback = False
    app.pattern_reset_entry = None
    ed = app.editor
    app.dialog = {
        'kind': 'pattern_arpeggio', 'title': f'Arpeggio: row {ed.row:03d}, CH {voice+1}',
        'message': 'Write OFF (0), ON (1), or Inst (R: follow the instrument setting). '
                   'The command persists on this channel across notes and patterns. '
                   'Hold (.) removes this row command and keeps the running state. '
                   'OFF also suppresses Jxy; pitch sequences and vibrato remain active.',
        'button_focus': 4,
        'target': (id(ed), ed.pattern_id, ed.row, voice),
    }


def handle_event(app, event):
    if event.type != pg.KEYDOWN:
        return
    if event.key == pg.K_ESCAPE:
        app.dialog = None
        return
    modes = {pg.K_0: 0, pg.K_1: 1, pg.K_r: -1, pg.K_PERIOD: None}
    if event.key not in modes:
        return
    identity, pattern, row, voice = app.dialog['target']
    ed = app.editor
    app.dialog = None
    if id(ed) != identity or pattern not in ed.song.patterns or row >= len(ed.song.patterns[pattern].rows):
        return
    mode = modes[event.key]
    label = {None: 'hold', 0: 'OFF', 1: 'ON', -1: 'instrument setting'}[mode]
    ed.edit(f'Arpeggio {label}: row {row:03d}, CH {voice+1}',
            [(('patterns', pattern, 'rows', row, voice, 'arp_mode'), mode)])
