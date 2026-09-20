from copy import deepcopy

import pygame as pg
import pytest

from sidpulse.app import App
from sidpulse.export.psid import RecordingSID, compile_song
from sidpulse.playback.voices import VoicePrograms
from sidpulse.project.format import ProjectError, decode, encode, load, save, validate
from sidpulse.song.model import Cell, Instrument, Pattern, Song, INSTRUMENT_PROGRAMS
from sidpulse.song.presets import save_user_preset, user_presets
from test_graphical_instruments import click, key
from test_psid import call, machine, trace_song


PROGRAMS = [
    ('arpeggio', {'arpeggio': [7, 12]}, {'arpeggio': []}),
    ('wave_sequence', {'wave_sequence': [128, 16]}, {'wave_sequence': []}),
    ('pitch_sequence', {'pitch_sequence': [12, 0, -5]}, {'pitch_sequence': []}),
    ('pulse', {'pulse_depth': 512, 'pulse_rate': 2}, {'pulse_depth': 0}),
    ('vibrato', {'vibrato_speed': 4, 'vibrato_depth': 15, 'vibrato_delay': 1}, {'vibrato_depth': 0}),
    ('gate', {'gate_ticks': 2}, {'gate_ticks': 0}),
    ('retrigger', {'retrigger': 2}, {'retrigger': 0}),
]


def writes(inst):
    sid = RecordingSID()
    voice = VoicePrograms(sid)
    voice.trigger(0, 48, inst)
    for tick in range(9):
        voice.tick(tick)
    voice.release(0)
    voice.tick(9)
    return sid.events


@pytest.mark.parametrize('program,parameters,neutral', PROGRAMS)
def test_switch_bypasses_sound_without_erasing_parameters(program, parameters, neutral):
    active = Instrument(**parameters)
    bypassed = deepcopy(active)
    setattr(bypassed, program + '_enabled', False)
    plain = deepcopy(active)
    for field, value in neutral.items():
        setattr(plain, field, value)
    assert writes(bypassed) == writes(plain)
    assert writes(active) != writes(plain)
    for field, value in parameters.items():
        assert getattr(bypassed, field) == value
    setattr(bypassed, program + '_enabled', True)
    assert writes(bypassed) == writes(active)


@pytest.mark.parametrize('program,parameters,neutral', PROGRAMS)
def test_switch_is_saved_in_project_user_preset_and_executed_by_psid(tmp_path, program, parameters, neutral):
    inst = Instrument(**parameters, **{program + '_enabled': False})
    song = Song(instruments={1: inst}, speed=6, export_config={'loop': False},
                patterns={0: Pattern(rows=[[Cell(48, 1), Cell(), Cell()], [Cell(), Cell(), Cell()]])})
    save(tmp_path / 'switches.sidpulse', song)
    assert load(tmp_path / 'switches.sidpulse')[0] == song
    save_user_preset(inst)
    presets, errors = user_presets()
    assert not errors and presets == [('User', inst)]
    result = compile_song(song)
    plain = deepcopy(song)
    setattr(plain.instruments[1], program + '_enabled', True)
    for field, value in neutral.items():
        setattr(plain.instruments[1], field, value)
    assert result.data == compile_song(plain).data
    cpu, memory = machine(result.data)
    for tick, (expected, tempo) in enumerate(trace_song(song)):
        memory.events = []
        call(cpu, 0x1000 if tick == 0 else 0x1003)
        assert (memory.events[25:] if tick == 0 else memory.events) == expected


def test_old_project_defaults_keep_existing_programs_and_switches_are_validated():
    inst = Instrument(arpeggio=[0, 7], gate_ticks=3)
    song = Song(instruments={1: inst})
    old = encode(song)
    old['format_version'] = 4
    for program in INSTRUMENT_PROGRAMS:
        del old['song']['instruments'][1][program + '_enabled']
    assert decode(old)[0] == song
    inst.arpeggio_enabled = 'off'
    with pytest.raises(ProjectError, match='enabled switch must be true or false'):
        validate(song)


def test_all_program_buttons_work_by_mouse_keyboard_and_undo():
    app = App(Song(), audio=False)
    try:
        app.handle(pg.event.Event(pg.VIDEORESIZE, w=1440, h=1050))
        app.change_page('instrument')
        app.choose_instrument_tab('motion')
        before = deepcopy(app.editor.song)
        for program in INSTRUMENT_PROGRAMS:
            click(app, 'toggle_program', program)
            assert getattr(app.editor.song.instruments[1], program + '_enabled') is False
            key(app, pg.K_RETURN)
            assert getattr(app.editor.song.instruments[1], program + '_enabled') is True
        assert app.editor.song == before
        app.instrument_focus = 'buttons'
        app.instrument_button = app.instrument_buttons().index(('save_user_preset', None))
        for program in INSTRUMENT_PROGRAMS:
            key(app, pg.K_RIGHT)
            app.renderer.render(app)
            key(app, pg.K_RETURN)
            assert getattr(app.editor.song.instruments[1], program + '_enabled') is False
        for _ in INSTRUMENT_PROGRAMS:
            key(app, pg.K_BACKSPACE, mod=pg.KMOD_CTRL)
        assert app.editor.song == before
        app.choose_instrument_tab('roll')
        app.editor.song.instruments[1].arpeggio = [0, 7, 12]
        click(app, 'toggle_program', 'arpeggio')
        assert app.editor.song.instruments[1].arpeggio == [0, 7, 12]
        assert not app.editor.song.instruments[1].arpeggio_enabled
        click(app, 'graph_field', 'pitch_sequence')
        click(app, 'toggle_program', 'pitch_sequence')
        assert not app.editor.song.instruments[1].pitch_sequence_enabled
    finally:
        app.close()
