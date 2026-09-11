import pytest

from sidpulse.playback.sequencer import Sequencer
from sidpulse.sid.backend_residfp import ReSIDfpBackend, set_filter
from sidpulse.song.model import example_song, Pattern, Cell


@pytest.mark.parametrize('clock', ['PAL', 'NTSC'])
@pytest.mark.parametrize('tempo', [125, 137, 255])
def test_native_percussion_attacks_start_on_time(clock, tempo):
    """ENV3 exposes delayed attacks even when all register timestamps match."""
    song = example_song()
    song.clock, song.tempo = clock, tempo
    sid = ReSIDfpBackend(clock=clock)
    set_filter(sid, song.filter)
    sid.render(48000)
    seq = Sequencer(sid)
    seq.start(song)
    last_position = None
    pending = None
    delays = []
    for frame in range(0, 48000 * 8, 48):  # read envelope every millisecond
        seq.render(48)
        position = (seq.order, seq.row)
        if position != last_position:
            cell = song.patterns[seq.pattern].rows[seq.row][2]
            if cell.note is not None:
                if pending is not None:
                    pytest.fail('Percussion never reached its attack peak')
                pending = frame
            last_position = position
        if pending is not None and sid.chip.read(28) >= 200:
            delays.append((frame - pending) / 48)
            pending = None
    assert len(delays) >= 15
    assert max(delays) <= 5, delays  # previously variable 2..36 ms


def test_loop_restart_keeps_the_prepared_attack():
    song = example_song()
    song.patterns = {0: Pattern(rows=[[Cell(), Cell(), Cell(36, 4)]] +
                               [[Cell(), Cell(), Cell()] for _ in range(3)])}
    song.orders = [0]
    sid = ReSIDfpBackend()
    sid.render(48000)
    seq = Sequencer(sid)
    seq.start(song)
    seq.render(48)
    for _ in range(12):
        seq.render(23040 - 48)  # 4 rows, 6 ticks/row, 960 samples/tick
        assert seq.row == 0
        seq.render(48 * 4)
        assert sid.chip.read(28) >= 200
        seq.render(23040 - 48 * 4 + 48)  # a second complete loop
