"""Independent development-only CPU/cycle comparison for all ten linked players."""
import pytest
pytest.importorskip('py65')
from py65_nmos import MPU
from test_psid import Memory, call
from test_channel_squeeze import interleaved
from sidpulse.export.squeeze import optimized_stream_candidates
from sidpulse.export.channel_phrases import channel_candidates
from sidpulse.export.replay_verify import ReplayCPU


@pytest.mark.parametrize('load', [0x1000, 0x09b4])
@pytest.mark.parametrize('loop', [False, True])
def test_all_new_binaries_match_py65_cycles_and_events(load, loop):
    records = interleaved(count=129)
    choices = list(optimized_stream_candidates(records, load)) + channel_candidates(records, loop, load)
    seen = set()
    for choice in choices:
        name = choice.mode if hasattr(choice, 'packed') else ('templates' if 'templates' in choice.mode else 'raw')
        if name in seen:
            continue
        seen.add(name)
        image = choice.image(loop)
        mem = Memory(); mem[load:load+len(image)] = image
        cpu = MPU(memory=mem)
        checked = ReplayCPU(image, len(choice.player), load=load, gap_address=choice.gap_address)
        count = 0
        def compare(address):
            mem.events.clear(); cpu.p |= cpu.DECIMAL
            elapsed = call(cpu, address)
            context = (name, hex(load), loop, count, hex(address))
            assert checked.call(address) == elapsed, context
            assert mem.events == [(r, v) for r, v in checked.events if r < 25], context
            assert mem[0xdc04:0xdc06] == list(checked.mem[0xdc04:0xdc06]), context
            assert mem[0xdc0e] == checked.mem[0xdc0e], context
        for traversal in range(2 if loop else 1):
            for r in records:
                compare(load if count == 0 else load+3)
                count += 1
                for _ in range(r[2]):
                    compare(load+3)
                    assert not mem.events
        if not loop:
            compare(load+3); compare(load+3)
        compare(load)
        assert all(load <= a < load+len(choice.player) or 0x100 <= a < 0x200 or
                   0xf8 <= a <= 0xfb or 0xd400 <= a <= 0xd418 or
                   a in (0xdc04, 0xdc05, 0xdc0e) for a, _ in mem.writes)
    assert seen == {'single', 'lanes', 'registers', 'raw', 'templates'}
