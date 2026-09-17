"""Bounded verifier for SIDpulse's bundled replay routines, not a C64 emulator.

Only the documented NMOS 6502 instructions used by these routines are accepted.
No ROM, IRQ, VIC, SID synthesis or arbitrary third-party executable is emulated.
This dependency-free export check verifies writes, CIA latches, memory ownership,
termination and CPU instruction cycles. Independent py65 tests remain essential.
"""
from dataclasses import dataclass


class VerificationError(ValueError):
    pass


class CycleBudgetError(VerificationError):
    pass


@dataclass(frozen=True)
class Verification:
    max_cycles: int
    stack_bytes: int
    calls: int
    measured_max_cycles: int = 0


class ReplayCPU:
    def __init__(self, image, player_size, *, gap_address=None, load=0x1000):
        self.mem = bytearray(65536)
        self.mem[load:load + len(image)] = image
        self.load, self.end = load, load + len(image)
        self.player_end = load + player_size
        self.gap_address = gap_address
        self.a = self.x = self.y = 0
        self.sp = 255
        self.p = 0x20
        self.pc = 0
        self.cycles = 0
        self.stack_bytes = 0
        self.events = []
        self.timer_events = []

    def read(self, address):
        if not (self.load <= address < self.end or 0x100 <= address < 0x200 or
                0xf8 <= address <= 0xfb or address in (0xdc04, 0xdc05, 0xdc0e)):
            raise VerificationError(f'Replay reads outside its memory map: ${address:04X}')
        return self.mem[address]

    def write(self, address, value):
        value &= 255
        if 0xd400 <= address <= 0xd418:
            self.events.append((address - 0xd400, value))
        elif address in (0xdc04, 0xdc05, 0xdc0e):
            self.timer_events.append((address, value))
        elif not (self.load <= address < self.player_end or 0x100 <= address < 0x200 or
                  0xf8 <= address <= 0xfb):
            raise VerificationError(f'Replay writes outside its workspace: ${address:04X}')
        self.mem[address] = value

    def byte(self):
        value = self.read(self.pc)
        self.pc = (self.pc + 1) & 65535
        return value

    def word(self):
        low = self.byte()
        return low | self.byte() << 8

    def nz(self, value):
        value &= 255
        self.p = (self.p & ~0x82) | (value & 0x80) | (2 if value == 0 else 0)
        return value

    def push(self, value):
        self.write(0x100 + self.sp, value)
        self.sp = (self.sp - 1) & 255
        self.stack_bytes = max(self.stack_bytes, 255 - self.sp)

    def pop(self):
        self.sp = (self.sp + 1) & 255
        return self.read(0x100 + self.sp)

    def step(self):
        if self.pc == self.gap_address:
            self.events.append((25, 32))
        op = self.byte()
        if op == 0x4c:  # JMP absolute
            self.pc = self.word(); self.cycles += 3; return
        if op == 0x20:  # JSR absolute
            target = self.word(); ret = self.pc - 1
            self.push(ret >> 8); self.push(ret & 255)
            self.pc = target; self.cycles += 6; return
        if op == 0x60:
            self.pc = ((self.pop() | self.pop() << 8) + 1) & 65535
            self.cycles += 6; return
        if op in (0xd8, 0x18, 0x38):
            self.p = self.p & ~8 if op == 0xd8 else self.p & ~1 if op == 0x18 else self.p | 1
            self.cycles += 2; return
        if op in (0x10, 0x30, 0xd0, 0xf0, 0x90, 0xb0):
            offset = self.byte(); before = self.pc
            take = {0x10: not self.p & 0x80, 0x30: bool(self.p & 0x80), 0xd0: not self.p & 2,
                    0xf0: bool(self.p & 2), 0x90: not self.p & 1, 0xb0: bool(self.p & 1)}[op]
            self.cycles += 2
            if take:
                self.pc = (self.pc + (offset if offset < 128 else offset - 256)) & 65535
                self.cycles += 1 + ((before >> 8) != (self.pc >> 8))
            return
        if op in (0xca, 0xc8, 0xaa, 0x8a, 0xa8, 0x0a, 0x4a):
            if op == 0xca: self.x = self.nz(self.x - 1)
            elif op == 0xc8: self.y = self.nz(self.y + 1)
            elif op == 0xaa: self.x = self.nz(self.a)
            elif op == 0x8a: self.a = self.nz(self.x)
            elif op == 0xa8: self.y = self.nz(self.a)
            else:
                carry = (self.a >> 7) if op == 0x0a else (self.a & 1)
                self.a = self.nz(self.a << 1 if op == 0x0a else self.a >> 1)
                self.p = (self.p & ~1) | carry
            self.cycles += 2; return
        # Address mode and base cycles. Stores and RMW never gain read penalties.
        immediate = (0xa9, 0xa2, 0xa0, 0xc9, 0xe0, 0x69, 0xe9, 0x09, 0x29)
        zero = (0xa5, 0xa6, 0xa4, 0x85, 0xc5, 0x65, 0x05, 0xe6, 0xc6)
        absolute = (0xad, 0xae, 0xac, 0x8d, 0xcd, 0x6d, 0x0d, 0xee, 0xce)
        indexed = (0xbd, 0xb9, 0x9d, 0xde, 0xfe, 0x7d)
        stores = (0x85, 0x8d, 0x9d, 0x91)
        rmw = (0xe6, 0xc6, 0xee, 0xce, 0xde, 0xfe)
        if op in immediate:
            address = self.pc; self.pc += 1; cycles = 2
        elif op in zero:
            address = self.byte(); cycles = 5 if op in rmw else 3
        elif op in absolute:
            address = self.word(); cycles = 6 if op in rmw else 4
        elif op in indexed:
            base = self.word(); address = (base + (self.y if op == 0xb9 else self.x)) & 65535
            cycles = 7 if op in rmw else 5 if op in stores else 4 + ((base >> 8) != (address >> 8))
        elif op in (0xb1, 0x91):
            zp = self.byte(); base = self.read(zp) | self.read((zp + 1) & 255) << 8
            address = (base + self.y) & 65535
            cycles = 6 if op == 0x91 else 5 + ((base >> 8) != (address >> 8))
        else:
            raise VerificationError(f'Unexpected replay opcode ${op:02X} at ${(self.pc-1):04X}')
        self.cycles += cycles
        if op in stores:
            self.write(address, self.a); return
        value = self.read(address)
        if op in (0xa9, 0xa5, 0xad, 0xbd, 0xb9, 0xb1): self.a = self.nz(value)
        elif op in (0xa2, 0xa6, 0xae): self.x = self.nz(value)
        elif op in (0xa0, 0xa4, 0xac): self.y = self.nz(value)
        elif op in (0xc9, 0xc5, 0xcd, 0xe0):
            reg = self.x if op == 0xe0 else self.a
            self.nz(reg - value); self.p = (self.p & ~1) | int(reg >= value)
        elif op == 0x29: self.a = self.nz(self.a & value)
        elif op in (0x09, 0x05, 0x0d): self.a = self.nz(self.a | value)
        elif op in (0x69, 0x65, 0x6d, 0x7d, 0xe9):
            if self.p & 8: raise VerificationError('Replay did not clear decimal mode')
            addend = value ^ 255 if op == 0xe9 else value
            total = self.a + addend + (self.p & 1)
            overflow = (~(self.a ^ addend) & (self.a ^ total) & 128) >> 1
            self.p = (self.p & ~0x41) | overflow | int(total > 255)
            self.a = self.nz(total)
        elif op in rmw:
            value = self.nz(value + (1 if op in (0xe6, 0xee, 0xfe) else -1))
            self.write(address, value)
        else: raise VerificationError(f'Unimplemented replay opcode ${op:02X}')

    def call(self, address):
        self.events.clear(); self.timer_events.clear()
        self.pc = address
        self.p |= 8  # init AND play must cope with a caller doing BCD arithmetic
        self.push(1); self.push(255)  # return to sentinel $0200
        before = self.cycles
        for _ in range(20000):
            if self.pc == 0x200:
                if self.sp != 255: raise VerificationError('Unbalanced replay stack')
                return self.cycles - before
            self.step()
        raise VerificationError('Replay did not return within the instruction guard')


def verify_replay(image, player_size, records, loop, *, gap_address=None, load=0x1000):
    """Execute a pass and the entire loop pass, including every slow-tick idle call.

    A 128-cycle call margin and 20% instruction-cycle reserve are checked, but VIC DMA/IRQ scheduling is outside this
    instruction-level model. Failure prevents selection of the compact candidate.
    """
    if not records:
        raise VerificationError('Replay has no musical ticks')
    if not (0 <= load < load + player_size <= load + len(image) <= 65536):
        raise VerificationError('Invalid replay image layout')
    cpu = ReplayCPU(image, player_size, gap_address=gap_address, load=load)
    maximum = calls = 0
    previous_period = None
    for traversal in range(2 if loop else 1):
        for index, record in enumerate(records):
            control_before = cpu.mem[0xdc0e]
            cycles = cpu.call(load if calls == 0 else load + 3)
            expected = list(zip(record[4::2], record[5::2]))
            if calls == 0:
                expected = [(r, 0) for r in range(24, -1, -1)] + expected
            actual = cpu.events if gap_address is not None else [(r, v) for r, v in cpu.events if r < 25]
            if gap_address is None: expected = [(r, v) for r, v in expected if r < 25]
            if actual != expected:
                raise VerificationError(f'Replay write mismatch in pass {traversal+1}, tick {index}')
            period = record[0] | record[1] << 8
            expected_timer = ([(0xdc04, period & 255), (0xdc05, period >> 8),
                               (0xdc0e, control_before | 0x11)] if period != previous_period else [])
            if cpu.timer_events != expected_timer:
                raise VerificationError(f'Replay ordered timer writes differ at tick {index}')
            previous_period = period
            if cpu.mem[0xdc04] | cpu.mem[0xdc05] << 8 != period:
                raise VerificationError(f'Replay timer mismatch at tick {index}')
            if (cycles + 128) * 5 >= period * 4:
                raise CycleBudgetError(f'Replay needs {cycles+128} cycles with margin; 80% timer budget is {period * 4 // 5}')
            maximum = max(maximum, cycles); calls += 1
            for _ in range(record[2]):
                cycles = cpu.call(load + 3); calls += 1
                if cpu.events or cpu.timer_events: raise VerificationError('Idle call changed SID/timer')
                if (cycles + 128) * 5 >= period * 4: raise CycleBudgetError('Idle call exceeds cycle margin')
                maximum = max(maximum, cycles)
    if not loop:
        cycles = cpu.call(load + 3); calls += 1
        maximum = max(maximum, cycles)
        if (cycles + 128) * 5 >= period * 4:
            raise CycleBudgetError('Terminal call exceeds cycle margin')
        if cpu.events != [(4, 0), (11, 0), (18, 0)] or cpu.timer_events:
            raise VerificationError('Replay terminal cut differs')
        cycles = cpu.call(load + 3); calls += 1
        maximum = max(maximum, cycles)
        if (cycles + 128) * 5 >= period * 4:
            raise CycleBudgetError('Stopped call exceeds cycle margin')
        if cpu.events or cpu.timer_events: raise VerificationError('Stopped replay kept writing')
    # INIT must also reset a previously used decoder; verify its first complete
    # musical tick instead of assuming initialization works only on zero RAM.
    control_before = cpu.mem[0xdc0e]
    cycles = cpu.call(load); calls += 1
    maximum = max(maximum, cycles)
    period = records[0][0] | records[0][1] << 8
    if (cycles + 128) * 5 >= period * 4:
        raise CycleBudgetError('Reinitialization exceeds cycle margin')
    if cpu.timer_events != [(0xdc04, period & 255), (0xdc05, period >> 8),
                            (0xdc0e, control_before | 0x11)]:
        raise VerificationError('Replay reinitialization timer mismatch')
    expected = [(r, 0) for r in range(24, -1, -1)] + list(zip(records[0][4::2], records[0][5::2]))
    actual = cpu.events
    if gap_address is None:
        expected = [(r, v) for r, v in expected if r < 25]
    if actual != expected:
        raise VerificationError('Replay reinitialization changed the first tick')
    return Verification(maximum + 128, cpu.stack_bytes, calls, maximum)
