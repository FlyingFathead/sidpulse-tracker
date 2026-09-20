"""Display ownership, method selection and volume-digi sample regressions."""
from copy import deepcopy
from dataclasses import replace
import json

import pygame as pg
import pytest

from sidpulse.export.pcm import compile_pcm, prepare_pcm, player_image, LOAD
from sidpulse.export.squeeze import SqueezeOptions
from test_pcm_media import pcm_song


@pytest.mark.parametrize('value', [False, True, 0, 3, '1', None])
def test_invalid_digi_method_is_rejected(value):
    with pytest.raises(ValueError, match='DIGI method'):
        SqueezeOptions(digi_method=value)


def test_old_preferences_default_to_volume_but_explicit_method_survives():
    from sidpulse.preferences import config_path, load_squeeze_options, save_squeeze_options
    path = config_path(); path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({'export_squeeze': {'enabled': False, 'version': 201}}))
    old = load_squeeze_options()
    assert old.digi_method == 1 and not old.enabled and old.version == 201
    save_squeeze_options(replace(old, digi_method=2))
    assert load_squeeze_options().digi_method == 2
    path.write_text(json.dumps({'export_squeeze': {'digi_method': True}}))
    assert load_squeeze_options().digi_method == 1


@pytest.mark.parametrize('clock', ['PAL', 'NTSC'])
def test_volume_samples_preserve_every_nibble_and_use_half_the_storage(clock):
    song = pcm_song(4005); song.clock = clock
    volume = prepare_pcm(song, digi_method=1)
    dac = prepare_pcm(song, digi_method=2)
    assert list(volume.clips) == list(dac.clips)
    offset = 0
    for codes in volume.clips:
        data = volume.samples[offset:offset+(len(codes)+1)//2]
        unpacked = bytes(c for b in data for c in (b & 15, b >> 4))
        assert unpacked[:len(codes)] == codes
        offset += len(data)
    assert offset == len(volume.samples) < len(dac.samples)


@pytest.mark.parametrize('clock', ['PAL', 'NTSC'])
def test_volume_entry_and_replay_leave_vic_and_screen_memory_alone(clock):
    """Run actual entry and NMIs with an independent CPU and populated display."""
    MPU = pytest.importorskip('py65.devices.mpu6502').MPU
    song = pcm_song(4005); song.clock = clock
    result = compile_pcm(song, kind='sid', squeeze=False)
    _, labels = player_image('plain', 1)
    class Memory(list):
        def __init__(self):
            super().__init__([0]*65536); self.writes = []; self.polls = 0
        def __setitem__(self, address, value):
            if isinstance(address, int): self.writes.append((address, value))
            super().__setitem__(address, value)
        def __getitem__(self, address):
            if address == 0xdc0d:
                self.polls += 1
                return int(self.polls % 100 == 0)
            if address == 0xdd0d: return 0x81
            return super().__getitem__(address)
    mem = Memory(); mem[LOAD:LOAD+len(result.data)-126] = result.data[126:]
    mem[0x400:0x800] = [0x41]*1024
    mem[0xd011] = 0x1b; mem[0xd015] = 0xa5; mem[0x01] = 0x37
    mem.writes.clear()
    cpu = MPU(memory=mem); cpu.pc = labels['entry']
    calls = interrupts = 0
    for count in range(150000):
        if cpu.pc == labels['play']:
            calls += 1
            if calls == 12: break
        if mem[labels['active']] and count % 31 == 7:
            return_pc = cpu.pc
            cpu.nmi()
            for _ in range(100):
                cpu.step()
                if cpu.pc == return_pc: break
            else: pytest.fail('Sample NMI failed to return')
            interrupts += 1
        cpu.step()
    assert calls == 12 and interrupts > 10
    assert mem[0xd011] == 0x1b and mem[0xd015] == 0xa5
    assert mem[0x400:0x800] == [0x41]*1024
    assert not any(0xd000 <= a <= 0xd3ff or 0x400 <= a < 0x800 for a, _ in mem.writes)
    assert len({v & 15 for a,v in mem.writes if a == 0xd418}) > 4


def test_method_and_target_are_separate_comparison_cache_entries():
    song = pcm_song(); cache = {}
    before = deepcopy(song)
    for method, kind in ((1, 'prg'), (2, 'sid'), (2, 'prg'), (1, 'sid')):
        options = SqueezeOptions(digi_method=method)
        cached = compile_pcm(song, kind=kind, squeeze=options, _comparison_cache=cache)
        independent = compile_pcm(song, kind=kind, squeeze=options)
        assert cached == independent
        assert cached.squeeze_report.digi_method == method
    assert song == before


@pytest.mark.parametrize('size', [(640,480), (1280,900)])
def test_method_menu_invalidates_analysis_and_confirmation_describes_selection(size):
    from sidpulse.app import App
    from sidpulse.ui import export_squeezer as ui
    from export_gui_helpers import finish_export_analysis
    app = App(pcm_song(), audio=False, size=size)
    try:
        before = deepcopy(app.editor.song)
        ui.open_dialog(app, 'prg'); finish_export_analysis(app)
        assert app.dialog['options'].digi_method == 1
        app.dialog['focus'] = 22; app.dialog['ensure_focus'] = True
        app.renderer.render(app)
        rect = next(r for r,a,v in app.renderer.hits if a == 'squeeze_digi_method')
        app.handle(pg.event.Event(pg.MOUSEBUTTONDOWN, button=1, pos=rect.center))
        assert app.dialog['options'].digi_method == 2 and app.dialog['result'] is None
        assert app.dialog['source'] is None and app.dialog['comparison'] is None
        ui.activate(app, 'export')
        assert app.dialog['digi_method'] == 2 and app.dialog['button_focus'] == 1
        app.renderer.render(app)
        app.handle(pg.event.Event(pg.KEYDOWN, key=pg.K_ESCAPE, mod=0))
        app.dialog['focus'] = 22
        app.handle(pg.event.Event(pg.KEYDOWN, key=pg.K_SPACE, mod=0))
        assert app.dialog['options'].digi_method == 1
        ui.activate(app, 'export'); app.renderer.render(app)
        assert app.dialog['digi_method'] == 1 and app.editor.song == before
    finally:
        app.close()
