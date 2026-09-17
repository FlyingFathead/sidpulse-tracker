"""Execute all stream decoder variants, including the compact PRG link address.

The existing test_psid/test_prg suites additionally exercise selected compilers
and the complete BASIC wrapper. py65 is a development-only dependency.
"""
import random
import struct
import pytest

pytest.importorskip('py65')
from py65_nmos import MPU
from test_psid import Memory, call
from test_squeeze import fixture_song
from sidpulse.export.psid import _record_song
from sidpulse.export.squeeze import stream_candidates, COMPACT_PRG_LOAD
from sidpulse.song.model import Song, example_song
from sidpulse.song.welcome import welcome_song


@pytest.mark.parametrize('load', [0x1000, COMPACT_PRG_LOAD])
@pytest.mark.parametrize('clock', ['PAL', 'NTSC'])
@pytest.mark.parametrize('loop', [False, True])
@pytest.mark.parametrize('factory', [Song, fixture_song, example_song, welcome_song])
def test_actual_single_and_lane_binaries_match_every_timed_write(load, clock, loop, factory):
    song = factory(); song.clock = clock; song.export_config['loop'] = loop
    records = _record_song(song)[1]
    for candidate in stream_candidates(records, load):
        data = candidate.image(loop)
        mem = Memory(); mem[load:load + len(data)] = data
        cpu = MPU(memory=mem)
        for tick in range(len(records) + int(loop)):
            record = records[tick % len(records)]
            mem.events.clear(); cpu.p |= cpu.DECIMAL
            elapsed = call(cpu, load if tick == 0 else load + 3)
            actual = mem.events[25:] if tick == 0 else mem.events
            assert actual == [(r, v) for r, v in zip(record[4::2], record[5::2]) if r < 25]
            assert mem[0xDC04] | mem[0xDC05] << 8 == int.from_bytes(record[:2], 'little')
            assert elapsed <= candidate.cycles_bound
            for _ in range(record[2]):
                mem.events.clear(); call(cpu, load + 3)
                assert not mem.events
        if not loop:
            mem.events.clear(); call(cpu, load + 3)
            assert mem.events == [(4, 0), (11, 0), (18, 0)]
            mem.events.clear(); call(cpu, load + 3)
            assert not mem.events
        mem.events.clear(); call(cpu, load)
        assert mem.events[25:] == [(r, v) for r, v in zip(records[0][4::2], records[0][5::2]) if r < 25]
        assert all(0x100 <= a < 0x200 or load <= a < load + len(candidate.player)
                   or a in (0xF8, 0xF9, 0xDC04, 0xDC05, 0xDC0E)
                   or 0xD400 <= a <= 0xD418 for a, _ in mem.writes)


@pytest.mark.parametrize('seed', range(4))
def test_randomized_event_interleaving_and_packet_page_crossings(seed):
    rng = random.Random(seed)
    records = []
    for tick in range(350):
        events = [(rng.randrange(25), rng.randrange(256)) for _ in range(rng.randrange(17))]
        if events and tick % 3 == 0: events.insert(len(events) // 2, (25, 32))
        records.append(struct.pack('<HBB', 50000 + tick % 3, tick % 3, len(events))
                       + bytes(value for pair in events for value in pair))
    for candidate in stream_candidates(records):
        image = candidate.image(False)
        mem = Memory(); mem[0x1000:0x1000 + len(image)] = image
        cpu = MPU(memory=mem)
        for tick, record in enumerate(records):
            mem.events.clear()
            elapsed = call(cpu, 0x1000 if tick == 0 else 0x1003)
            assert (mem.events[25:] if tick == 0 else mem.events) == [
                (r, v) for r, v in zip(record[4::2], record[5::2]) if r < 25]
            assert elapsed <= candidate.cycles_bound
            for _ in range(record[2]):
                mem.events.clear(); call(cpu, 0x1003)
                assert not mem.events
