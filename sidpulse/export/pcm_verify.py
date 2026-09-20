"""Bounded instruction and sample verification for the bundled PCM player.

This is a 6502 instruction check, not a VIC/CIA/SID or physical C64 emulator.
The compiler rejects schedules outside a conservative interrupt + VIC budget.
Independent py65 tests exercise interrupt preemption inside the stream decoder.
"""
from collections import deque
from dataclasses import dataclass
import math

from sidpulse.export.replay_verify import ReplayCPU, VerificationError, CycleBudgetError


class PCMCPU(ReplayCPU):
    def read(self, address):
        if address == 0xdd04 and getattr(self, '_nmi_origin', None) is not None:
            period = self.mem[0xdd04] | self.mem[0xdd05] << 8
            return (period - (self.cycles-self._nmi_origin)) & 255
        if 0xdc00 <= address <= 0xdd0f:
            return self.mem[address]
        return super().read(address)

    def write(self, address, value):
        if 0xdc00 <= address <= 0xdd0f:
            self.mem[address] = value & 255
            self.timer_events.append((address, value & 255))
        else:
            super().write(address, value)

    def step(self):
        op = self.mem[self.pc]
        if op == 0xea:  # NOP timing sled
            self.pc += 1
            self.cycles += 2
        elif op == 0x48:  # PHA
            self.pc += 1
            self.push(self.a)
            self.cycles += 3
        elif op == 0x68:  # PLA
            self.pc += 1
            self.a = self.nz(self.pop())
            self.cycles += 4
        elif op == 0x49:  # EOR immediate
            self.pc += 1
            self.a = self.nz(self.a ^ self.byte())
            self.cycles += 2
        elif op == 0x40:  # RTI
            self.p = self.pop()
            self.pc = self.pop() | self.pop() << 8
            self.cycles += 6
        else:
            super().step()

    def interrupt(self, address, delay=0):
        before = self.cycles
        self._nmi_origin = before
        saved = self.a, self.x, self.y, self.p, self.sp
        self.push(2); self.push(0); self.push(self.p)
        self.p |= 4
        self.cycles += 7 + delay
        self.pc = address
        self.mem[0xdd0d] = 0x81
        self.events.clear()
        for _ in range(100):
            if self.pc == 0x200:
                if (self.a, self.x, self.y, self.p, self.sp) != saved:
                    raise VerificationError('PCM NMI did not preserve CPU registers and stack')
                self._nmi_origin = None
                return self.cycles-before
            self.step()
        raise VerificationError('PCM NMI did not return')


@dataclass(frozen=True)
class PCMVerification:
    max_cycles: int
    stack_bytes: int
    calls: int
    measured_max_cycles: int
    nmi_cycles: int


def verify_pcm(image, labels, records, references, clips, sample_period, levels, progress=None, *, digi_method=2):
    if digi_method == 1:
        from sidpulse.export.pcm_volume_verify import verify_volume_pcm
        return verify_volume_pcm(image, labels, records, references, clips, sample_period, progress)
    cpu = PCMCPU(image, 0x1800-0x0801, gap_address=labels['gap'], load=0x0801)
    codes_by_pointer = {0x1800+index*4: codes for codes, index in clips.items()}
    queue = deque()
    volume, active, owned, primed = 0, False, False, False
    max_music, max_bound, max_nmi, calls = 0, 0, 0, 0
    # Both pipeline phases, every entry delay, pointer carry and end sentinel.
    probe = PCMCPU(image, 0x1800-0x0801, load=0x0801)
    probe.mem[0xdd04] = (sample_period-1) & 255
    probe.mem[0xdd05] = (sample_period-1) >> 8
    for phase in (0, 1):
        for delay in range(8):
            for value in (levels[0], levels[8], levels[15], 255):
                for low in (0, 255):
                    probe.mem[labels['active']] = 1
                    probe.mem[labels['primed']] = phase
                    probe.mem[labels['sample_read']+1] = low
                    probe.mem[labels['sample_read']+2] = 0x17
                    probe.mem[0x1700+low] = value
                    max_nmi = max(max_nmi, probe.interrupt(labels['nmi'], delay))
    # Entry jitter is included above. Published entry disables display/sprites
    # and waits for a fresh frame, so there are no VIC DMA steals during PCM.
    if max_nmi + 16 >= sample_period:
        raise CycleBudgetError('PCM NMI cannot finish before its next timer underflow')
    available = 1 - max_nmi/sample_period - .02  # additional scheduling reserve
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
        nonlocal volume, active, owned, primed, queue
        writes = []
        for register, value in events:
            if register == 30:
                queue = deque(levels[c] for c in codes_by_pointer[references[id(value)]])
                queue.extend((levels[8], 255))
                active = True
                primed = False
                if not owned:
                    writes.extend(((18, 8), (14, 0), (19, 0), (20, 240),
                                   (15, levels[8]), (18, 0), (18, 16)))
                owned = True
                writes.extend(((18, 9), (24, volume & 127)))
            elif register == 31:
                active = False
                queue.clear()
                if owned:
                    writes.extend(((18, 8), (24, volume)))
                    owned = False
            elif register == 24:
                volume = value
                writes.append((24, value & 127 if owned else value))
            else:
                writes.append((register, value))
        return writes

    for tick, (period, idle, events) in enumerate(records):
        if progress and tick % 256 == 0:
            progress('Verifying C64 PCM instructions...', f'{tick:,} / {len(records):,} ticks; SID writes, samples and CPU budgets.')
        wanted = ([(n, 0) for n in range(23, -1, -1)] if tick == 0 else []) + expected(events)
        cycles = cpu.call(labels['init'] if tick == 0 else labels['play'])
        calls += 1
        if cpu.events != wanted:
            raise VerificationError(f'PCM music write mismatch at tick {tick}: {cpu.events[:12]} != {wanted[:12]}')
        if cpu.mem[0xdc04] | cpu.mem[0xdc05] << 8 != period:
            raise VerificationError('PCM music timer does not match the arrangement')
        check_budget(cycles, period, f'tick {tick}')
        # Between musical ticks, execute every active sample interrupt. Registers,
        # all DAC values, midpoint tail, ownership and termination are checked.
        for subcall in range(idle+1):
            for _ in range((period+1)//sample_period + 1):
                if not active:
                    break
                value = queue.popleft()
                wanted_nmi = ([(18, 17)] if primed else []) + [(18, 9)]
                primed = True
                ending = value == 255
                if not ending:
                    wanted_nmi.extend(((15, value), (18, 1)))
                cost = cpu.interrupt(labels['nmi'])
                if cpu.events != wanted_nmi:
                    raise VerificationError(f'PCM DAC/pipeline mismatch at tick {tick}: {cpu.events} != {wanted_nmi}')
                if ending:
                    active = False
                max_nmi = max(max_nmi, cost)
            if subcall < idle:
                cpu.call(labels['play'])
                calls += 1
                if cpu.events:
                    raise VerificationError('Slow-tempo idle call unexpectedly wrote SID registers')
    # Decode the terminator and, for looping songs, the first complete next tick.
    wanted = expected(((31, 0),))
    if cpu.mem[labels['loop_song']]:
        wanted += expected(records[0][2])
    else:
        wanted += [(4, 0), (11, 0), (18, 0)]
    cycles = cpu.call(labels['play'])
    calls += 1
    if cpu.events != wanted:
        raise VerificationError('PCM replay failed song termination/loop verification')
    if cpu.mem[labels['loop_song']]:
        check_budget(cycles, records[0][0], 'loop restart')
    # Music stack plus hardware interrupt frame and the one-byte NMI A save.
    return PCMVerification(max_bound, cpu.stack_bytes+4, calls, max_music, max_nmi)
