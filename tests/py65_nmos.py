"""Development-only py65 NMOS timing adapter; never imported by SIDpulse.

py65 1.2.0 declares DEC absolute ($CE) as 3 cycles instead of 6:
https://github.com/mnaberez/py65/blob/1.2.0/py65/devices/mpu6502.py#L1059-L1062
MOS MCS6500 Hardware Manual, January 1976, Appendix A.4.2 specifies 6:
https://xotmatrix.com/6502/6502-single-cycle-execution.html

Keep upstream instruction execution intact. Correct this one documented table
entry on a private instance copy, not in site-packages or a shared class table.
The production ReplayCPU already charges six cycles and must not be reduced to
match an incorrect reference. Exact per-call cycle assertions remain mandatory.
"""
from py65.devices.mpu6502 import MPU as UpstreamMPU


class MPU(UpstreamMPU):
    """NMOS 6502 reference with the known DEC-absolute timing typo corrected."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if (self.disassemble[0xCE] != ('DEC', 'abs')
                or self.cycletime[0xCE] not in (3, 6)
                or self.extracycles[0xCE] != 0):
            raise RuntimeError('Unexpected py65 DEC-absolute definition; review the test adapter')
        self.cycletime = list(self.cycletime)
        self.cycletime[0xCE] = 6
