"""DAC timing and handoff regressions, independent of the stream event oracle."""
import json
from pathlib import Path

import pytest

from sidpulse.export.pcm import compile_pcm, dac_levels, LOAD
from sidpulse.export.pcm_verify import PCMCPU
from sidpulse.export.squeeze import SqueezeOptions
from test_pcm_media import pcm_song


@pytest.mark.parametrize('clock', ['PAL', 'NTSC'])
@pytest.mark.parametrize('model', ['6581', '8580'])
def test_dac_capture_is_stable_and_never_modulates_master_volume(clock, model):
    song = pcm_song(); song.clock = clock; song.sid_model = model
    result = compile_pcm(song, kind='prg', squeeze=SqueezeOptions(digi_method=2))
    labels = json.loads((Path(__file__).resolve().parents[1]/'sidpulse/assets/pcm-player.json').read_text())['labels']
    period = 246 if clock == 'PAL' else 256
    class Timed(PCMCPU):
        def write(self, address, value):
            if 0xd400 <= address <= 0xd418:
                self.timed.append((self.cycles, address, value))
            super().write(address, value)
    captures = []
    for delay in range(8):
        cpu = Timed(result.data[2:], 0x1800-LOAD, load=LOAD)
        cpu.timed = []
        cpu.mem[0xdd04] = (period-1) & 255; cpu.mem[0xdd05] = (period-1) >> 8
        cpu.mem[labels['active']] = cpu.mem[labels['primed']] = cpu.mem[labels['owned']] = 1
        cpu.mem[labels['sample_read']+1] = 0; cpu.mem[labels['sample_read']+2] = 0x17
        cpu.mem[0x1700] = dac_levels(model,period)[15]
        cpu.interrupt(labels['nmi'], delay)
        captures.append(next(t for t,r,v in cpu.timed if r==0xd412 and v==17))
        assert all(r in (0xd412,0xd40f) for t,r,v in cpu.timed)
        cpu.mem[0x1701] = 255
        cpu.timed.clear();cpu.interrupt(labels['nmi'])
        assert cpu.mem[labels['active']] == 0 and cpu.mem[labels['owned']] == 1
        assert all(r != 0xd418 for t,r,v in cpu.timed)
        assert cpu.mem[0xd412] == 9  # hold midpoint with gate open between hits
        cpu.call(labels['pcm_stop'])
        assert cpu.mem[labels['owned']] == 0 and cpu.mem[0xd412] == 8
    assert len(set(captures)) == 1, captures


@pytest.mark.parametrize('period', [246,256])
@pytest.mark.parametrize('model', ['6581','8580'])
def test_full_scale_dac_does_not_cross_oscillator_msb_or_use_sentinel(model,period):
    levels = dac_levels(model,period)
    assert len(levels)==16 and all(a<b for a,b in zip(levels,levels[1:]))
    assert max(levels)*256*(period-18)<0x800000
    assert 255 not in levels
