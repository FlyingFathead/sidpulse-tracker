"""Explicit regression tests for the development-only timing-table adapter."""
import pytest
pytest.importorskip('py65')
from py65.devices.mpu6502 import MPU as UpstreamMPU
from py65_nmos import MPU
from sidpulse.export.replay_verify import ReplayCPU


def test_adapter_changes_only_private_dec_cycle_entry():
    before = list(UpstreamMPU.cycletime)
    upstream = UpstreamMPU()
    first, second = MPU(), MPU()
    assert list(UpstreamMPU.cycletime) == before
    assert upstream.cycletime is UpstreamMPU.cycletime
    assert first.cycletime is not UpstreamMPU.cycletime
    assert first.cycletime is not second.cycletime
    expected = before[:]
    expected[0xCE] = 6
    assert first.cycletime == second.cycletime == expected
    assert first.instruct is UpstreamMPU.instruct  # no instruction replacement
    assert first.extracycles is UpstreamMPU.extracycles


@pytest.mark.parametrize('cycles', [3, 6])
def test_known_broken_or_already_correct_table_is_supported(monkeypatch, cycles):
    original = list(UpstreamMPU.cycletime)
    changed = original[:]
    changed[0xCE] = cycles
    monkeypatch.setattr(UpstreamMPU, 'cycletime', changed)
    assert MPU().cycletime[0xCE] == 6
    assert UpstreamMPU.cycletime == changed
    assert UpstreamMPU.cycletime[0xCE] == cycles


@pytest.mark.parametrize('bad_field,value', [
    ('cycletime', 4), ('extracycles', 1), ('disassemble', ('NOP', 'abs')),
])
def test_unexpected_upstream_definition_is_not_silently_overridden(monkeypatch, bad_field, value):
    table = list(getattr(UpstreamMPU, bad_field))
    table[0xCE] = value
    monkeypatch.setattr(UpstreamMPU, bad_field, table)
    with pytest.raises(RuntimeError, match='Unexpected py65'):
        MPU()


@pytest.mark.parametrize('flags', [0x20, 0x29, 0x60, 0x69])
def test_dec_absolute_is_six_cycles_with_identical_instruction_semantics(flags):
    image = bytearray(0x200)
    image[:4] = bytes([0xCE, 0x00, 0x11, 0x60])
    ref = ReplayCPU(image, len(image))
    original, corrected = UpstreamMPU(), MPU()
    for cpu in (original, corrected):
        cpu.memory[0x1000:0x1200] = image
    for value in range(256):
        ref.pc, ref.p = 0x1000, flags
        ref.mem[0x1100] = value
        before = ref.cycles
        ref.step()
        assert ref.cycles - before == 6
        for cpu in (original, corrected):
            cpu.pc, cpu.p = 0x1000, flags
            cpu.memory[0x1100] = value
            before = cpu.processorCycles
            cpu.step()
            assert cpu.processorCycles - before == cpu.cycletime[0xCE]
            assert (cpu.pc, cpu.p, cpu.memory[0x1100]) == (ref.pc, ref.p, ref.mem[0x1100])
        assert corrected.cycletime[0xCE] == 6


def test_dec_absolute_plus_rts_is_twelve_cycles():
    from test_psid import call
    cpu = MPU()
    cpu.memory[0x1000:0x1004] = [0xCE, 0x00, 0x11, 0x60]
    cpu.memory[0x1100] = 2
    assert call(cpu, 0x1000) == 12
    assert cpu.memory[0x1100] == 1
