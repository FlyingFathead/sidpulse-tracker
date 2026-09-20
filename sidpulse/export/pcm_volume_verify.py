"""Instruction verification for DIGI method #1 and its packed sample stream."""
from collections import deque
import math
from sidpulse.export.pcm_verify import PCMCPU, PCMVerification
from sidpulse.export.replay_verify import VerificationError, CycleBudgetError


def verify_volume_pcm(image, labels, records, references, clips, sample_period, progress=None):
    cpu = PCMCPU(image, 0x1800-0x0801, gap_address=labels['gap'], load=0x0801)
    codes_by_pointer = {0x1800+index*4: codes for codes, index in clips.items()}
    queue = deque()
    volume, active = 0, False
    max_music, max_bound, max_nmi, calls = 0, 0, 0, 0
    # All NMI branches, pointer-page and counter borrows; values checked below.
    probe = PCMCPU(image, 0x1800-0x0801, load=0x0801)
    for phase in (0, 1):
        for count in (0, 1, 256, 257):
            for low in (0, 255):
                probe.mem[labels['active']] = 1
                probe.mem[labels['phase']] = phase
                probe.mem[labels['count_lo']] = count & 255
                probe.mem[labels['count_hi']] = count >> 8
                probe.mem[labels['sample_read']+1] = low
                probe.mem[labels['sample_read']+2] = 0x10
                max_nmi = max(max_nmi, probe.interrupt(labels['nmi']))
    # Up to 43 VIC badline steals + seven cycles for an interrupted instruction.
    if max_nmi + 50 >= sample_period:
        raise CycleBudgetError('PCM NMI cannot finish before its next timer underflow')
    available = 1 - max_nmi/sample_period - .08  # VIC reserve, no sprite DMA
    if available <= 0:
        raise CycleBudgetError('PCM NMI leaves no safe music CPU budget')

    def check_budget(cycles, period, label):
        nonlocal max_music, max_bound
        max_music = max(max_music, cycles)
        bound = math.ceil((cycles+300)/available)
        if bound >= period+1:
            raise CycleBudgetError(f'PCM {label} needs up to {bound:,} cycles; timer budget {period+1:,}. '
                                   'Simplify this row or lower the tempo.')
        max_bound = max(max_bound, bound)

    def expected(events):
        nonlocal volume, active, queue
        writes = []
        for register, value in events:
            if register == 30:
                queue = deque(codes_by_pointer[references[id(value)]])
                active = True
                writes.extend(((18, 8), (24, volume), (14, 0), (15, 0), (19, 0), (20, 240), (18, 25)))
            elif register == 31:
                active = False
                queue.clear()
                writes.extend(((18, 8), (24, volume)))
            elif register == 24:
                volume = value
                if not active:
                    writes.append((24, value))
            else:
                writes.append((register, value))
        return writes

    for tick, (period, idle, events) in enumerate(records):
        if progress and tick % 256 == 0:
            progress('Verifying C64 PCM instructions...', f'{tick:,} / {len(records):,} ticks; SID writes, samples and CPU budgets.')
        wanted = ([(n, 0) for n in range(24, -1, -1)] if tick == 0 else []) + expected(events)
        cycles = cpu.call(labels['init'] if tick == 0 else labels['play'])
        calls += 1
        if cpu.events != wanted:
            raise VerificationError(f'PCM music write mismatch at tick {tick}: {cpu.events[:12]} != {wanted[:12]}')
        if cpu.mem[0xdc04] | cpu.mem[0xdc05] << 8 != period:
            raise VerificationError('PCM music timer does not match the arrangement')
        check_budget(cycles, period, f'tick {tick}')
        # Between musical ticks, execute every active sample interrupt. Registers,
        # exact nibbles, end-of-sample volume and termination are checked.
        for subcall in range(idle+1):
            for _ in range((period+1)//sample_period + 1):
                if not active:
                    break
                wanted_nmi = [(24, queue.popleft() | (volume & 112))] if queue else [(18, 8), (24, volume)]
                ending = not cpu.mem[labels['count_lo']] and not cpu.mem[labels['count_hi']]
                cost = cpu.interrupt(labels['nmi'])
                if cpu.events != wanted_nmi:
                    raise VerificationError(f'PCM nibble/volume mismatch at tick {tick}')
                if ending:
                    active = False
                max_nmi = max(max_nmi, cost)
            if subcall < idle:
                cpu.call(labels['play'])
                calls += 1
                if cpu.events:
                    raise VerificationError('Slow-tempo idle call unexpectedly wrote SID registers')
    # Decode the terminator and, for looping songs, the first complete next tick.
    if cpu.mem[labels['loop_song']]:
        active = False
        queue.clear()
        wanted = [(18, 8), (24, volume)] + expected(records[0][2])
    else:
        wanted = [(18, 8), (24, volume), (4, 0), (11, 0), (18, 0)]
    cycles = cpu.call(labels['play'])
    calls += 1
    if cpu.events != wanted:
        raise VerificationError('PCM replay failed song termination/loop verification')
    if cpu.mem[labels['loop_song']]:
        check_budget(cycles, records[0][0], 'loop restart')
    if cpu.mem[labels['loop_song']]:
        max_music = max(max_music, cycles)
        bound = math.ceil((cycles+300)/available)
        if bound >= records[0][0]+1:
            raise CycleBudgetError('PCM loop restart exceeds the music timer budget')
        max_bound = max(max_bound, bound)
    # Music stack plus hardware interrupt frame and the one-byte NMI A save.
    return PCMVerification(max_bound, cpu.stack_bytes+4, calls, max_music, max_nmi)
