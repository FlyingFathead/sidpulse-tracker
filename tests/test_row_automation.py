from copy import deepcopy
from dataclasses import replace
import time

import pygame as pg
import pytest

from sidpulse.app import App
from sidpulse.commands.editor import Editor, FIELDS, CURSOR_HINTS
from sidpulse.export.psid import compile_song
from sidpulse.playback.sequencer import Sequencer
from sidpulse.project.format import encode, decode, load, save, ProjectError
from sidpulse.song.model import Song, Cell, Pattern, ENVELOPE_FIELDS
from test_playback import TraceSID, wait_until
from test_psid import machine, call, trace_song


def song():
    result = Song(speed=4, export_config={'loop': False})
    result.patterns[0].rows = [[Cell() for _ in range(3)] for _ in range(16)]
    result.patterns[0].rows[0] = [Cell(48, 1), Cell(52, 1), Cell(55, 1)]
    return result


def pulse(sid, voice=0):
    return sid.registers[voice*7+2] | sid.registers[voice*7+3] << 8


def test_pw_changes_held_voice_and_survives_notes_then_restores_default():
    source = song()
    source.patterns[0].rows[1][0].pulse_width = 0x123
    source.patterns[0].rows[2][0] = Cell(50, 1)
    source.patterns[0].rows[3][0].pulse_width = 0
    source.patterns[0].rows[4][0].pulse_width = -1
    source.patterns[0].rows[5][0].pulse_width = 4095
    before = deepcopy(source)
    sid = TraceSID(); seq = Sequencer(sid); seq.start(source)
    seq.render(1)
    assert pulse(sid) == 0x800
    for expected in (0x123, 0x123, 0, 0x800, 4095):
        seq.render(3840)
        assert pulse(sid) == expected
        assert pulse(sid, 1) == pulse(sid, 2) == 0x800
    assert source == before


def test_adsr_overrides_work_on_blank_rows_without_a_gate_trigger():
    source = song()
    source.patterns[0].rows[1][0] = Cell(attack=2, decay=3, sustain=4, release=5)
    source.patterns[0].rows[2][0].sustain = 0
    source.patterns[0].rows[3][0] = Cell(**dict.fromkeys(ENVELOPE_FIELDS, -1))
    sid = TraceSID(); seq = Sequencer(sid); seq.start(source)
    seq.render(1); sid.events.clear()
    seq.render(3840)
    assert sid.registers[5:7] == bytes((0x23, 0x45))
    assert not any(register == 4 for _, register, value in sid.events)
    assert sid.registers[12:14] == sid.registers[19:21] == bytes((8, 0xC5))
    seq.render(3840); assert sid.registers[6] == 5
    seq.render(3840); assert sid.registers[5:7] == bytes((8, 0xC5))


def test_adsr_overrides_survive_retrigger_and_lookahead_cannot_mutate_them():
    source = song()
    source.patterns[0].rows[0][0] = Cell(48, 1, attack=2, sustain=7)
    source.patterns[0].rows[2][0] = Cell(52, 1, sustain=4, effect='S', parameter=0xD2)
    sid = TraceSID(); seq = Sequencer(sid); seq.start(source)
    seq.render(1)
    assert seq.programs.voices[0].envelope == {'attack': 2, 'sustain': 7}
    seq.render(7679)
    assert seq.row == 2 and seq.programs.voices[0].envelope['sustain'] == 4
    seq.render(1920)
    assert seq.programs.voices[0].note == 52 and sid.registers[5:7] == bytes((0x28, 0x45))


def test_channel_overrides_leave_presets_intact_and_reset_to_current_instrument():
    source = song()
    source.instruments[2] = replace(source.instruments[1], pulse_width=0x400, attack=4, sustain=6)
    source.patterns[0].rows[0][0] = Cell(48, 1, pulse_width=0x222, attack=2, sustain=3)
    source.patterns[0].rows[1][0] = Cell(50, 2)
    source.patterns[0].rows[2][0] = Cell(pulse_width=-1, attack=-1, sustain=-1)
    before = deepcopy(source)
    sid = TraceSID(); seq = Sequencer(sid); seq.start(source); seq.render(1)
    seq.render(3840)
    assert pulse(sid) == 0x222 and sid.registers[5:7] == bytes((0x28, 0x35))
    seq.render(3840)
    assert pulse(sid) == 0x400 and sid.registers[5:7] == bytes((0x48, 0x65))
    assert source == before


@pytest.mark.parametrize('field,invalid', [('pulse_width', 4096), ('pulse_width', -2),
                                         ('attack', 16), ('sustain', True), ('release', -2)])
def test_invalid_automation_is_rejected(field, invalid):
    document = encode(song())
    document['song']['patterns'][0]['rows'][0][0][field] = invalid
    with pytest.raises(ProjectError):
        decode(document)


def test_schema7_roundtrip_and_old_cells_get_empty_automation(tmp_path):
    source = song()
    source.patterns[0].rows[1][2] = Cell(pulse_width=0, attack=0, decay=15, sustain=-1, release=2)
    assert load(save(tmp_path/'automation.sidpulse', source))[0] == source
    raw = encode(song()); raw['format_version'] = 6
    for rows in raw['song']['patterns'].values():
        for row in rows['rows']:
            for cell in row:
                for field in ('pulse_width', *ENVELOPE_FIELDS):
                    cell.pop(field, None)
    assert decode(raw)[0] == song()


def test_editor_keeps_legacy_columns_and_handles_new_fields_and_undo():
    editor = Editor(song())
    assert FIELDS[:9] == ('note', 'note', 'instrument', 'instrument', 'expression', 'expression', 'effect', 'parameter', 'parameter')
    editor.column = 13
    for digit in 'A3F': editor.enter_digit(digit)
    assert editor.pattern.rows[0][0].pulse_width == 0xA3F
    assert (editor.row, editor.column) == (1, 13)
    editor.enter_digit('R'); assert editor.pattern.rows[1][0].pulse_width == -1
    editor.row = 1; editor.clear_field(); assert editor.pattern.rows[1][0].pulse_width is None
    editor.history.undo(editor.song); assert editor.pattern.rows[1][0].pulse_width == -1
    for column, field in enumerate(ENVELOPE_FIELDS, 9):
        editor.row, editor.column = 2, column
        editor.enter_digit('F'); assert getattr(editor.pattern.rows[2][0], field) == 15
        editor.row = 3; editor.enter_digit('R'); assert getattr(editor.pattern.rows[3][0], field) == -1
    editor.voice, editor.column = 0, 15
    editor.move(columns=1); assert (editor.voice, editor.column) == (1, 0)


@pytest.mark.parametrize('squeeze', [False, True])
@pytest.mark.parametrize('clock', ['PAL', 'NTSC'])
def test_6502_export_executes_all_three_voices_automation(squeeze, clock):
    source = song(); source.clock = clock
    for row in range(1, 16):
        for voice in range(3):
            source.patterns[0].rows[row][voice] = Cell(pulse_width=(row*223+voice*13)%4096,
                                                       attack=row%16, sustain=(15-row)%16)
    source.patterns[0].rows[-1][0] = Cell(pulse_width=-1, attack=-1, sustain=-1)
    exported = compile_song(source, squeeze=squeeze)
    cpu, memory = machine(exported.data)
    for tick, (expected, _) in enumerate(trace_song(source)):
        memory.events.clear(); call(cpu, 0x1000 if tick == 0 else 0x1003)
        assert (memory.events[25:] if tick == 0 else memory.events) == expected


def test_audio_clock_records_rows_even_without_any_ui_poll_and_stops_before_wrap():
    source = song(); sid = TraceSID(); seq = Sequencer(sid); seq.start(deepcopy(source), 'pattern')
    seq.render(1); seq.record_pulse(1, 0, 0x222)
    seq.render(3840*3)
    assert dict(seq.pulse_recording.snapshot.rows) == dict.fromkeys(range(4), 0x222)
    seq.update_pulse_recording(1, 0x999)
    seq.render(3840*13)
    snapshot = seq.pulse_recording.snapshot
    assert snapshot.done and snapshot.reason == 'Pattern pass complete'
    assert len(snapshot.rows) == 16 and snapshot.rows[0] == (0, 0x222)
    assert dict(snapshot.rows)[3] == dict(snapshot.rows)[15] == 0x999
    assert seq.song.instruments == source.instruments
    assert all(seq.song.patterns[0].rows[r][1:] == source.patterns[0].rows[r][1:] for r in range(16))


def test_cancel_restores_worker_rows_and_runtime_override():
    source = song(); source.patterns[0].rows[1][0].pulse_width = 0x444
    seq = Sequencer(TraceSID()); seq.start(deepcopy(source)); seq.render(1)
    seq.record_pulse(7, 0, 0x222); seq.render(3840*4)
    seq.finish_pulse_recording(7, True)
    assert seq.song == source and seq.programs.voices[0].pulse_width is None
    assert seq.pulse_recording.snapshot.cancelled


def test_recording_can_begin_before_first_tick_and_panic_finishes_it():
    seq = Sequencer(TraceSID()); seq.start(song())
    seq.record_pulse(1, 1, 123); seq.render(1)
    assert not seq.pulse_recording.done
    seq.stop(); assert seq.pulse_recording.snapshot.done


def test_cursor_hints_replace_stale_instrument_text_on_every_field():
    app = App(song(), audio=False)
    try:
        app.editor.status = 'Draw instrument pulse_width'
        for column in range(len(FIELDS)):
            app.editor.column = column
            assert app.renderer.context_status(app) == CURSOR_HINTS[column]
        app.control_focus = True
        assert 'shared SID filter' in app.renderer.context_status(app)
    finally:
        app.close()


def test_snapshot_commit_is_one_undo_and_keeps_instruments_and_other_fields():
    app = App(song(), audio=False)
    try:
        before = deepcopy(app.editor.song)
        seq = Sequencer(TraceSID()); seq.start(deepcopy(before)); seq.render(1)
        seq.record_pulse(4, 2, 0x333); seq.render(3840*3); seq.finish_pulse_recording(4)
        app.pulse_take = {'token':4, 'value':0x333, 'pending':False, 'cancel':False}
        app.audio.pulse_capture = seq.pulse_recording.snapshot
        app.sync_audio()
        assert len(app.editor.history.undo_stack) == 1
        assert app.editor.song.instruments == before.instruments
        assert app.editor.pattern.rows[3][2].pulse_width == 0x333
        app.editor.history.undo(app.editor.song); assert app.editor.song == before
        app.editor.history.redo(app.editor.song); assert app.editor.pattern.rows[3][2].pulse_width == 0x333
    finally:
        app.close()


def test_real_audio_process_slider_capture_and_save_key_wait_for_final_rows(tmp_path):
    source = song(); source.patterns[0].rows *= 4
    app = App(source, path=tmp_path/'take.sidpulse', audio=True, audio_buffer=256)
    try:
        wait_until(lambda: app.audio.ready or app.audio.error, 5)
        assert not app.audio.error
        app.start_playback('pattern')
        wait_until(lambda: app.audio.playback.status == 'playing', 3)
        app.change_page('instrument'); app.property_index = 6
        app.open_automation_recording(); app.toggle_pulse_recording(); app.renderer.render(app)
        rect, data = next((r, d) for r, a, d in app.renderer.hits if a == 'automation_slider')
        app.begin_pulse_drag(data, (rect.x+rect.width//4, rect.centery))
        wait_until(lambda: app.audio.pulse_capture and len(app.audio.pulse_capture.rows) >= 3, 3)
        app.update_instrument_drag((rect.x+rect.width*3//4, rect.centery))
        app.handle(pg.event.Event(pg.KEYDOWN, key=pg.K_s, scancode=22, mod=pg.KMOD_CTRL, unicode='s'))
        def saved():
            app.sync_audio()
            return app.path.exists()
        wait_until(saved, 3)
        restored, _ = load(app.path)
        assert restored == app.editor.song and app.pulse_take is None
        assert restored.instruments == source.instruments
        values = [c[0].pulse_width for c in restored.patterns[0].rows if c[0].pulse_width is not None]
        assert len(values) >= 3 and min(values) < 1500 and max(values) > 2500
        assert len(app.editor.history.undo_stack) == 1
    finally:
        app.close()


def test_disarm_finishes_active_capture_and_keeps_a_single_undoable_take():
    source=song();source.patterns[0].rows *= 4
    app=App(source,audio=True,audio_buffer=512)
    try:
        wait_until(lambda:app.audio.ready or app.audio.error,5)
        assert not app.audio.error
        app.start_playback('pattern')
        wait_until(lambda:app.audio.playback.status=='playing',3)
        app.change_page('instrument');app.open_automation_recording()
        app.set_recording_channel(2);app.toggle_pulse_recording();app.renderer.render(app)
        rect,data=next((r,d) for r,a,d in app.renderer.hits if a=='automation_slider')
        before=deepcopy(app.editor.song)
        app.begin_pulse_drag(data,rect.center)
        wait_until(lambda:app.audio.pulse_capture and len(app.audio.pulse_capture.rows)>=3,3)
        app.disarm_pulse_recording()
        assert not app.pulse_record_armed
        def committed():
            app.sync_audio()
            return app.pulse_take is None
        wait_until(committed,3)
        assert len(app.editor.history.undo_stack)==1
        assert app.editor.song.instruments==before.instruments
        assert len([row for row in app.editor.pattern.rows if row[2].pulse_width is not None])>=3
        app.editor.history.undo(app.editor.song)
        assert app.editor.song==before
    finally:app.close()


@pytest.mark.parametrize('field',['attack','decay','sustain','release','pulse_width'])
def test_record_each_parameter_cancel_restores_only_its_rows_and_live_override(field):
    from sidpulse.playback.automation_parameters import PARAMETERS
    source=song();before=deepcopy(source)
    seq=Sequencer(TraceSID());seq.start(source);seq.render(1)
    program=seq.programs.voices[1]
    if field=='pulse_width':program.pulse_width=123
    else:program.envelope[field]=3
    seq.record_pulse(42,1,99999,field);seq.render(3840*2)
    snap=seq.pulse_recording.snapshot
    assert snap.field==field and len(snap.rows)>=2
    assert all(value==PARAMETERS[field][2] for _,value in snap.rows)
    assert source.instruments==before.instruments
    seq.finish_pulse_recording(42,cancel=True)
    assert source==before
    assert (program.pulse_width if field=='pulse_width' else program.envelope[field])==(123 if field=='pulse_width' else 3)


@pytest.mark.parametrize('field',['attack','decay','sustain','release'])
def test_real_worker_keyboard_records_adsr_and_can_undo_without_changing_instrument(field):
    source=song();source.patterns[0].rows *= 4
    app=App(source,audio=True,audio_buffer=512)
    try:
        wait_until(lambda:app.audio.ready or app.audio.error,5)
        assert not app.audio.error
        app.open_automation_recording();app.set_recording_parameter(field);app.set_recording_channel(1)
        app.toggle_pulse_recording();app.renderer.render(app);app.start_playback('pattern')
        wait_until(lambda:app.audio.playback.status=='playing',3)
        before=deepcopy(app.editor.song)
        app.handle(pg.event.Event(pg.KEYDOWN,key=pg.K_RIGHT,mod=0,unicode='',scancode=0))
        wait_until(lambda:app.audio.pulse_capture and len(app.audio.pulse_capture.rows)>=3,3)
        app.handle(pg.event.Event(pg.KEYUP,key=pg.K_RIGHT,mod=0,unicode='',scancode=0))
        def committed():
            app.sync_audio();return app.pulse_take is None
        wait_until(committed,3)
        assert app.dialog is None and app.inline_recording_visible
        assert len(app.editor.history.undo_stack)==1
        changed=[row[1] for row in app.editor.pattern.rows if getattr(row[1],field)!=getattr(before.patterns[0].rows[0][1],field)]
        assert len(changed)>=3 and all(getattr(cell,field)==9 for cell in changed)
        assert app.editor.song.instruments==before.instruments
        app.editor.history.undo(app.editor.song);assert app.editor.song==before
    finally:app.close()
