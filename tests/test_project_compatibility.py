from copy import deepcopy
from dataclasses import replace
import json

import pygame as pg
import pytest

from sidpulse import __version__
from sidpulse.app import App
from sidpulse.commands.editor import Editor
from sidpulse.project.format import encode, decode, save, load, compatibility_warnings, CURRENT_FORMAT
from sidpulse.song.model import Song, Cell, ControlCell
from sidpulse.playback.sequencer import Sequencer
from test_playback import TraceSID


def future_document():
    raw = encode(Song())
    raw['format_version'] = CURRENT_FORMAT + 1
    raw['editor']['saved_with_version'] = '0.9.1'
    raw['future_root'] = {'keep': [1, 2, 3]}
    raw['song']['new_song_feature'] = {'amount': 12}
    pat = raw['song']['patterns'][0]
    pat['new_pattern_feature'] = 'pattern information'
    pat['rows'][0][0]['future_slide'] = {'curve': [0, 100, 20]}
    pat['controls'][0] = {'cutoff': 250, 'future_filter': [1, 4]}
    raw['song']['instruments'][1]['future_shape'] = {'on': True}
    raw['song']['filter']['future_filter_mode'] = 8
    return raw


def test_future_data_survives_load_note_edit_copy_paste_and_native_save(tmp_path):
    raw = future_document()
    song, metadata = decode(raw)
    warnings = '\n'.join(compatibility_warnings(song))
    assert 'newer SIDpulse Tracker 0.9.1' in warnings and f'format {CURRENT_FORMAT+1}' in warnings
    assert '7 unfamiliar field(s)' in warnings
    ed = Editor(song); ed.enter_note(60)
    ed.row = 0; ed.copy(); ed.row = 1; ed.paste()
    saved = save(tmp_path/'future.sidpulse', song, metadata)
    output = json.loads(saved.read_text())
    assert output['format_version'] == CURRENT_FORMAT + 1
    assert output['editor']['saved_with_version'] == __version__
    assert output['future_root'] == raw['future_root']
    assert output['song']['new_song_feature'] == raw['song']['new_song_feature']
    for row in (0, 1):
        assert output['song']['patterns']['0']['rows'][row][0]['future_slide'] == {'curve': [0,100,20]}
    assert output['song']['instruments']['1']['future_shape'] == {'on': True}
    assert output['song']['patterns']['0']['controls']['0']['future_filter'] == [1,4]
    assert load(saved)[0] == song
    ed.history.undo(song); assert song.patterns[0].rows[1][0] == Cell()


def test_newer_app_without_unknown_data_still_warns_and_loads():
    raw = encode(Song()); raw['editor']['saved_with_version'] = '99.0.0'
    song, _ = decode(raw)
    assert 'newer SIDpulse Tracker' in compatibility_warnings(song)[0]
    assert song == Song()


def test_ordinary_saves_use_original_v6_cell_shape_and_stamp_app_version():
    document = encode(Song())
    assert document['format_version'] == 6
    assert set(document) == {'format', 'format_version', 'song', 'editor'}
    assert document['editor']['saved_with_version'] == __version__
    assert set(document['song']['patterns'][0]['rows'][0][0]) == {'note','instrument','effect','parameter'}
    assert all(not key.startswith('_') for key in document['song'])
    assert compatibility_warnings(decode(document)[0]) == ()
    song = Song(); song.patterns[0].rows[1][0].pulse_width = 0
    assert encode(song)['format_version'] == 7


def test_future_project_opens_with_visible_non_destructive_warning(tmp_path):
    path = tmp_path/'future.sidpulse'; path.write_text(json.dumps(future_document()))
    before = path.read_bytes()
    app = App(audio=False)
    try:
        app.open_project(path)
        assert app.dialog['title'] == 'Project compatibility'
        assert 'unfamiliar' in app.dialog['message']
        assert app.editor.song.patterns[0].controls[0].cutoff == 250
        assert path.read_bytes() == before and not app.editor.dirty
    finally:
        app.close()


@pytest.mark.parametrize('page', ['pattern', 'info'])
@pytest.mark.parametrize('status', ['playing', 'paused', 'stopped'])
def test_blue_control_lane_is_visible_in_playback_and_stop_views(page, status):
    app = App(audio=False, size=(1280, 900))
    try:
        app.page = page
        app.audio.playback = replace(app.audio.playback, status=status, filter_values=(300,4,3,16,15,5))
        app.renderer.render(app)
        actions = [action for rect, action, value in app.renderer.hits]
        assert ('control_focus' if page == 'pattern' else 'playback_control') in actions
    finally:
        app.close()


def test_live_control_values_include_running_slide_and_survive_stop():
    song = Song(speed=6)
    song.patterns[0].controls[0] = ControlCell(cutoff=300, resonance=4, routing=3, mode=16, volume=15, slide=5)
    seq = Sequencer(TraceSID()); seq.start(song); seq.render(960*2)
    assert seq.state.filter_values == (315,4,3,16,15,5)
    seq.stop(); assert seq.state.filter_values == (315,4,3,16,15,5)
