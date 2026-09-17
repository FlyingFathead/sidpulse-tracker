"""Hardware-manual cycle checks independent of optional py65 installation."""
import pytest
from sidpulse.export.replay_verify import ReplayCPU


# MOS MCS6500 Hardware Manual Appendix A.4.1/A.4.2/A.4.4: 5/6/7 cycles.
# Include zero, sign and wraparound results and both states of carry/decimal.
@pytest.mark.parametrize('instruction,address,index,cycles', [
    (bytes([0xC6, 0xF8]), 0x00F8, 0, 5),
    (bytes([0xCE, 0x00, 0x11]), 0x1100, 0, 6),
    (bytes([0xDE, 0x00, 0x11]), 0x1101, 1, 7),
    (bytes([0xDE, 0xFF, 0x10]), 0x1100, 1, 7),
])
@pytest.mark.parametrize('flags', [0x20, 0x29, 0x60, 0x69])
def test_decrement_cycles_flags_and_memory(instruction, address, index, cycles, flags):
    image = bytearray(0x200)
    image[:len(instruction)] = instruction
    cpu = ReplayCPU(image, len(image))
    for value in range(256):
        cpu.pc, cpu.x, cpu.p = 0x1000, index, flags
        cpu.mem[address] = value
        before = cpu.cycles
        cpu.step()
        expected = (value - 1) & 255
        assert cpu.cycles - before == cycles
        assert cpu.pc == 0x1000 + len(instruction)
        assert cpu.mem[address] == expected
        assert cpu.p == (flags & ~0x82) | (expected & 0x80) | (2 if not expected else 0)


def test_idle_path_uses_six_cycle_dec_and_totals_thirty():
    # Exact idle path from the single-stream player at $1000:
    # JMP (3), CLD (2), LDA (4), BEQ taken (3), LDA (4),
    # BEQ not taken (2), DEC abs (6), RTS (6) = 30.
    from sidpulse.export.squeeze import optimized_stream_candidates
    from test_channel_squeeze import interleaved
    records = interleaved(count=3)
    choice = next(c for c in optimized_stream_candidates(records, 0x1000)
                  if c.mode == 'single')
    cpu = ReplayCPU(choice.image(False), len(choice.player), gap_address=choice.gap_address)
    cpu.call(0x1000)
    cpu.call(0x1003)
    assert records[1][2] == 1
    assert cpu.call(0x1003) == 30
    assert not cpu.events and not cpu.timer_events
