from copy import deepcopy

import pytest

from sidpulse.export.psid import RecordingSID, compile_song
from sidpulse.playback.sequencer import Sequencer
from sidpulse.project.format import load, save
from sidpulse.song.welcome import welcome_song


def test_welcome_song_roundtrips_as_editable_project_and_loads_independently(tmp_path):
    song = welcome_song()
    expected = deepcopy(song)
    target = save(tmp_path / 'autumn.sidpulse', song)
    assert load(target)[0] == expected
    song.instruments[1].name = 'My melody'
    song.patterns[0].rows[0][1].note = 36
    assert welcome_song() == expected


@pytest.mark.parametrize('clock', ['PAL', 'NTSC'])
def test_welcome_arrangement_compiles_for_one_real_sid(clock):
    from test_psid import call, machine

    song = welcome_song()
    song.clock = clock
    before = deepcopy(song)
    result = compile_song(song)
    assert song == before
    assert result.seconds == pytest.approx(96)
    assert result.data.startswith(b'PSID') and not result.warnings
    sid = RecordingSID(clock)
    sequencer = Sequencer(sid)
    sequencer.start(song)
    cpu, memory = machine(result.data)
    ticks = sum(len(song.patterns[p].rows) for p in song.orders) * song.speed
    # Execute every exported tick and cross the loop boundary too: arpeggios,
    # envelope preparation, filter changes and delayed vibrato must all survive.
    for tick in range(ticks + 8):
        sequencer._boundary()
        expected = [(r, v) for r, v in sid.events if r < 25]
        memory.events = []
        elapsed = call(cpu, 0x1000 if tick == 0 else 0x1003)
        actual = memory.events[25:] if tick == 0 else memory.events
        assert actual == expected, (clock, tick)
        assert elapsed < round(sid.clock_hz * 2.5 / song.tempo)
        sid.events.clear()
        sequencer.frames = int(sequencer.next_tick)
    assert sequencer.loops == 1
