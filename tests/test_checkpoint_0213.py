"""Display-grid, effect-status and export-diagnostic regressions."""
from copy import deepcopy
import hashlib
import pytest

from sidpulse.commands.editor import Editor
from sidpulse.export.psid import ExportError, ExportMemoryError, compile_song
from sidpulse.project.format import load, save
from sidpulse.song.model import Cell, Song, Pattern
from sidpulse.ui.pattern_grid import PatternGrid


def test_default_grid_is_backward_compatible():
    grid = PatternGrid()
    assert grid.rows_per_bar == 16
    assert [grid.level(n) for n in (0,1,4,8,15,16)] == [2,0,1,1,0,2]


def test_shuffle_grid_has_12_row_beats_and_48_row_bars():
    grid = PatternGrid(12,4)
    assert [grid.level(n) for n in (0,4,12,24,36,47,48,60,96)] == [2,0,1,1,1,0,2,1,2]
    assert PatternGrid(3,3).rows_per_bar == 9


@pytest.mark.parametrize('field,value', [('rows_per_beat',0),('rows_per_beat',257),('rows_per_beat',True),
                                         ('beats_per_bar',0),('beats_per_bar',33),('beats_per_bar',1.5)])
def test_grid_rejects_invalid_numbers(field,value):
    with pytest.raises(ValueError): PatternGrid(**{field:value})


@pytest.mark.parametrize('bad', [None, [], '12/48', {'rows_per_beat':True}, {'rows_per_beat':0,'beats_per_bar':99}])
def test_optional_invalid_metadata_does_not_block_loading(bad):
    assert PatternGrid.from_metadata(bad) == PatternGrid()


def test_grid_edits_are_display_only_and_preserve_extension_metadata(tmp_path):
    editor=Editor();before=deepcopy(editor.song)
    editor.pattern_grid=editor.pattern_grid.changed('rows_per_beat',direct='12')
    assert editor.pattern_grid==PatternGrid(12,4)
    metadata={'pattern_grid':editor.pattern_grid.metadata({'future_grid_setting':True}), 'unrelated':{'v':1}}
    saved=save(tmp_path/'song.sidpulse',editor.song,metadata)
    song,restored=load(saved)
    assert song==before and restored==metadata
    assert editor.pattern_grid.changed('rows_per_beat',delta=-99).rows_per_beat==1
    assert editor.pattern_grid.changed('beats_per_bar',delta=99).beats_per_bar==32
    with pytest.raises(ValueError): editor.pattern_grid.changed('rows_per_beat',direct='1.5')
    with pytest.raises(ValueError): editor.pattern_grid.changed('rows_per_beat',direct=True)


@pytest.mark.parametrize('code,parameter,executable', [('H',0x34,True),('J',0x47,True),('S',0xD1,True),
                                                      ('Q',0x03,True),('Q',0x13,False),('T',0x76,True),
                                                      ('T',0x10,False),('D',0x10,False)])
def test_effect_feedback_uses_actual_playback_capability(code,parameter,executable):
    text=Editor.effect_edit_label('effect',Cell(effect=code,parameter=parameter))
    assert 'pending' not in text
    assert ('unsupported' not in text)==executable
    assert f'{code}{parameter:02X}' in text


def test_effect_entry_and_parameter_entry_both_use_feedback():
    editor=Editor();editor.column=6
    editor.enter_digit('H')
    assert 'pending' not in editor.status and 'unsupported' not in editor.status
    editor.row=0;editor.column=7;editor.enter_digit('3');editor.enter_digit('4')
    assert 'H34' in editor.status and 'pending' not in editor.status


def test_memory_error_reports_exact_components_and_remains_exporterror():
    error=ExportMemoryError(512,30000,8000)
    assert isinstance(error,ExportError)
    assert error.required_bytes==38512
    assert error.budget_bytes==36864
    assert error.excess_bytes==1648
    assert '38,512' in str(error) and '.sidpulse is unchanged' in str(error)


def test_full_memory_requirement_is_counted_before_writing():
    song=Song(speed=2,tempo=118,export_config={'loop':False})
    song.patterns={0:Pattern(rows=[[Cell(),Cell(),Cell()] for _ in range(256)])}
    song.orders=[0]*34
    before=deepcopy(song)
    # This fits 18,000 ticks but overflows the pointer table + record pool.
    # Dense modulation makes it deterministically exceed the current budget.
    song.patterns[0].rows[0]=[Cell(48,1),Cell(24,2),Cell(60,3)]
    song.instruments[1].pulse_depth=1500;song.instruments[1].pulse_rate=37
    song.instruments[1].vibrato_depth=7;song.instruments[1].vibrato_speed=5
    song.instruments[2].vibrato_speed=3;song.instruments[2].vibrato_depth=4
    song.instruments[3].arpeggio=[0,4,7,12];song.instruments[3].arp_speed=3
    before=deepcopy(song)
    with pytest.raises(ExportMemoryError) as caught: compile_song(song)
    error=caught.value
    assert error.required_bytes==error.player_bytes+error.record_bytes+error.sequence_bytes
    assert error.excess_bytes>0 and song==before


@pytest.mark.parametrize('name,expected', [
    ('first-light','1ae69f68a3fa72355b07832e1983db276ffbae4560f8f213dfcab0ade0518c06'),
    ('first-light-ntsc','8f4f7c186a7b4e9e8626cfecf76c92a851c24d738b147b7a43cc23c7a6b34663'),
    ('autumn-at-five','a0ca3059e6a64f992cf8e377f1e59f472835bbf688dd5736a8d8aa6e89ea4cbc'),
    ('autumn-at-five-ntsc','6da0bd595d242afc32549918b658756f867be80ffecdd59f37553b7f0ed433b4')])
def test_existing_pal_ntsc_exports_remain_byte_identical(name,expected):
    from pathlib import Path
    path=Path(__file__).resolve().parents[1]/'examples'/f'{name}.sidpulse'
    song,_=load(path)
    assert hashlib.sha256(compile_song(song).data).hexdigest()==expected


def test_gui_grid_metadata_and_settings_route_when_pygame_available(tmp_path):
    pytest.importorskip('pygame',reason='pygame-ce required for this UI integration test')
    from sidpulse.app import App
    app=App(audio=False)
    try:
        before=deepcopy(app.editor.song)
        app.page='settings';app.property_index=24;app.change_property(direct='12')
        app.property_index=25;app.change_property(direct='4')
        assert app.editor.pattern_grid==PatternGrid(12,4)
        assert app.editor.song==before
        app.restore_metadata({'pattern_grid':{'rows_per_beat':12,'beats_per_bar':4,'unknown':True}})
        assert app.metadata()['pattern_grid']['unknown'] is True
        app.restore_metadata({})
        assert app.editor.pattern_grid==PatternGrid()
    finally:
        app.close()
