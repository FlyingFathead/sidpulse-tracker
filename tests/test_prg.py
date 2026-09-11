from copy import deepcopy
import struct
import sys

import pygame as pg
import pytest
from py65.devices.mpu6502 import MPU

from sidpulse.__main__ import main
from sidpulse.app import App
from sidpulse.export.prg import PRG_LOAD, compile_prg, save_prg
from sidpulse.export.psid import ExportError, RecordingSID, compile_song
from sidpulse.playback.sequencer import Sequencer
from sidpulse.project.format import load
from sidpulse.song.model import Cell, Pattern, Song
from sidpulse.song.welcome import welcome_song
from sidpulse.ui.menus import menu_items


class C64Memory(list):
    """CPU test bus: explicit CIA timer flags, keyboard row and ROM API stubs."""
    def __init__(self, prg, pal):
        super().__init__([0] * 65536)
        address = struct.unpack_from('<H', prg)[0]
        self[address:address + len(prg) - 2] = prg[2:]
        self[0x02A6] = int(pal)
        self[0xF8:0xFC] = [17, 34, 51, 68]
        for address in (0xFFD2, 0xFF84, 0xFF81):
            self[address] = 0x60  # RTS; record calls separately
        self.events = []
        self.timer_flag = 0
        self.icr_reads = 0
        self.stop_pressed = False

    def __getitem__(self, key):
        if key == 0xDC0D:
            self.icr_reads += 1
            flag, self.timer_flag = self.timer_flag, 0
            return flag
        if key == 0xDC01:
            return 0x7F if self.stop_pressed and self[0xDC00] == 0x7F else 0xFF
        return super().__getitem__(key)

    def __setitem__(self, key, value):
        if isinstance(key, int) and 0xD400 <= key <= 0xD418:
            self.events.append((key - 0xD400, value))
        super().__setitem__(key, value)


def machine(prg, pal):
    mem = C64Memory(prg, pal)
    cpu = MPU(memory=mem)
    cpu.pc = 2061
    cpu.p = cpu.UNUSED | cpu.CARRY
    cpu.stPushWord(0x0200 - 1)
    return cpu, mem


def step_until(cpu, predicate, calls=None):
    for _ in range(100000):
        if predicate():
            return
        if calls is not None and cpu.pc in (0xFF84, 0xFF81, 0xFFD2):
            calls.append((cpu.pc, cpu.a))
        cpu.step()
    pytest.fail('PRG did not reach its next expected state')


@pytest.mark.parametrize('clock', ['PAL', 'NTSC'])
def test_prg_run_timer_polling_and_runstop(clock):
    song = welcome_song()
    song.clock = clock
    result = compile_prg(song)
    # Payload bytes stay at exactly the addresses used by the tested PSID player.
    assert result.data[2 + 0x1000 - PRG_LOAD:] == compile_song(song).data[124:]
    assert result.data[:14] == bytes.fromhex('01080b080a009e32303631000000')
    cpu, mem = machine(result.data, clock == 'PAL')
    calls = []
    step_until(cpu, lambda: cpu.pc == 0x1000, calls)
    assert cpu.p & cpu.INTERRUPT
    assert mem[0xDC02] == 255 and mem[0xDC03] == 0
    assert mem[0xDC0D] == 0  # no pending underflow on startup
    mem.events.clear()
    reads = mem.icr_reads
    step_until(cpu, lambda: mem.icr_reads > reads)
    sid = RecordingSID(clock)
    seq = Sequencer(sid)
    seq.start(song)
    seq._boundary()
    assert mem.events[25:] == [(r, v) for r, v in sid.events if r < 25]
    assert (mem[0xDC04] | mem[0xDC05] << 8) == round(sid.clock_hz * 2.5 / 80) - 1
    # No timer flag means no new music tick, even if the polling loop spins.
    unchanged = list(mem.events)
    for _ in range(60):
        cpu.step()
    assert mem.events == unchanged
    for _ in range(16):
        mem.events.clear()
        sid.events.clear()
        seq.frames = int(seq.next_tick)
        seq._boundary()
        reads = mem.icr_reads
        mem.timer_flag = 1
        step_until(cpu, lambda: mem.icr_reads >= reads + 2)
        assert mem.events == [(r, v) for r, v in sid.events if r < 25]
    mem.stop_pressed = True
    step_until(cpu, lambda: cpu.pc == 0x0200, calls)
    assert mem[0xD400:0xD419] == [0] * 25
    assert mem[0xF8:0xFC] == [17, 34, 51, 68]
    assert not cpu.p & cpu.INTERRUPT and cpu.p & cpu.CARRY
    assert [pc for pc, _ in calls if pc != 0xFFD2] == [0xFF84, 0xFF81]


def test_prg_clock_mismatch_returns_without_starting_music():
    cpu, mem = machine(compile_prg(welcome_song()).data, pal=False)
    calls = []
    step_until(cpu, lambda: cpu.pc == 0x0200, calls)
    display = ''.join(chr(a) for pc, a in calls if pc == 0xFFD2)
    assert 'DIFFERENT VIDEO CLOCK' in display
    assert not mem.events and mem.icr_reads == 0
    assert mem[0xF8:0xFC] == [17, 34, 51, 68]
    assert not cpu.p & cpu.INTERRUPT


def test_prg_slow_tempo_and_tempo_changes_use_compiled_cia_timing():
    song = Song(speed=1, tempo=32, export_config={'loop': False})
    song.patterns = {0: Pattern(rows=[
        [Cell(48, 1), Cell(), Cell()],
        [Cell(52, 1, 'T', 160), Cell(), Cell()],
        [Cell(), Cell(), Cell()]])}
    cpu, mem = machine(compile_prg(song).data, pal=True)
    step_until(cpu, lambda: cpu.pc == 0x1000)
    reads = mem.icr_reads
    step_until(cpu, lambda: mem.icr_reads > reads)
    old_timer = mem[0xDC04] | mem[0xDC05] << 8
    assert old_timer == round(round(985248 * 2.5 / 32) / 2) - 1
    for expected_notes in (False, True):
        mem.events.clear()
        reads = mem.icr_reads
        mem.timer_flag = 1
        step_until(cpu, lambda: mem.icr_reads >= reads + 2)
        assert any(r == 4 and v & 1 for r, v in mem.events) == expected_notes
    assert (mem[0xDC04] | mem[0xDC05] << 8) == round(985248 * 2.5 / 160) - 1


def test_prg_preserves_project_and_rejects_unsupported_music():
    song = welcome_song()
    before = deepcopy(song)
    compile_prg(song)
    assert song == before
    song.patterns[0].rows[0][0] = Cell(effect='P', parameter=0x12)
    with pytest.raises(ExportError, match='not supported'):
        compile_prg(song)


def test_prg_display_warns_about_unicode_without_changing_native_text():
    song = welcome_song()
    song.title = 'Who? Autumn \u00e4'
    song.author = 'A' * 40
    result = compile_prg(song)
    assert any('PRG title' in warning for warning in result.warnings)
    assert any('PRG author' in warning for warning in result.warnings)
    assert song.title == 'Who? Autumn \u00e4' and song.author == 'A' * 40
    offset = 2 + 0x0C00 - PRG_LOAD
    assert result.data[offset:offset + 33] == b'WHO? AUTUMN ?'.ljust(33, b'\0')


def test_prg_atomic_save_and_backup(tmp_path, monkeypatch):
    result = compile_prg(welcome_song())
    path = save_prg(tmp_path / 'autumn.prg', result)
    path.write_bytes(b'previous')
    save_prg(path, result)
    assert path.with_suffix('.prg.bak').read_bytes() == b'previous'
    assert path.read_bytes() == result.data
    def fail(*args):
        raise OSError('Full disk')
    monkeypatch.setattr('sidpulse.export.psid.os.replace', fail)
    with pytest.raises(OSError, match='Full disk'):
        save_prg(path, result)
    assert path.read_bytes() == result.data
    assert not list(tmp_path.glob('*.tmp'))


def test_cli_prg_exports_welcome_and_editable_source(monkeypatch, tmp_path):
    target = tmp_path / 'autumn.prg'
    monkeypatch.setattr(sys, 'argv', ['sidpulse', '--play-welcome-song', '--export-prg', str(target)])
    assert main() == 0
    assert target.read_bytes() == compile_prg(welcome_song()).data
    assert load(target.with_suffix('.sidpulse'))[0] == welcome_song()


def test_prg_menu_export_keeps_unsaved_editor_state(tmp_path):
    assert next(item for item in menu_items('File Menu') if item.command == 'export_prg').enabled
    app = App(welcome_song(), audio=False)
    try:
        app.file_dir = tmp_path
        app.editor.saved = None
        before = deepcopy(app.editor.song)
        app.begin_export('prg')
        assert app.dialog['title'].startswith('Export PRG')
        app.handle(pg.event.Event(pg.KEYDOWN, key=pg.K_e, mod=0, unicode='e'))
        assert app.dialog['title'] == 'Export .prg (C64 program)'
        app.dialog['callback'](str(tmp_path / 'music.prg'))
        assert (tmp_path / 'music.prg').read_bytes() == compile_prg(before).data
        assert app.editor.song == before and app.editor.saved is None
        assert app.path is None and not list(tmp_path.glob('*.sidpulse'))
    finally:
        app.close()
