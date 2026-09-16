"""Schematic ADSR control geometry, NOT a common time axis or SID emulator.

00 is the fastest SID rate (~2 ms attack at 1 MHz), not a zero-time envelope.
Its vertical attack line is a UI convention. Timing/register writes are unchanged.
Nominal rates: MOS 6581 datasheet, Table 2 (see docs/ISSUES-v0.2.15.md).
"""
ATTACK_MS = (2,8,16,24,38,56,68,80,100,250,500,800,1000,3000,5000,8000)


def clamp(value,lo,hi):
    return max(lo,min(hi,value))


def envelope_points(rect,inst):
    x,y,w,h=rect
    level=y+h*(1-inst.sustain/15)
    return [(x,y+h),(x+w*.26*inst.attack/15,y),
            (x+w*(.30+.22*inst.decay/15),level),(x+w*.66,level),
            (x+w*(.72+.26*inst.release/15),y+h)]


def envelope_value(pos,rect,field):
    x=clamp((pos[0]-rect.x)/max(1,rect.width),0,1)
    level=clamp(round(15*(1-(pos[1]-rect.y)/max(1,rect.height))),0,15)
    if field=='sustain':return {'sustain':level}
    base,width={'attack':(0.,.26),'decay':(.30,.22),'release':(.72,.26)}[field]
    result={field:clamp(round((x-base)/width*15),0,15)}
    if field=='decay':result['sustain']=level
    return result


def attack_caption(attack,clock='PAL'):
    from sidpulse.sid.backend_residfp import CLOCKS
    ms=ATTACK_MS[attack]*1_000_000/CLOCKS[clock]
    time=f'{ms:.2f}ms' if ms<100 else f'{ms/1000:.2f}s'
    return f'A{attack:02X} ~{time} ({clock}); schematic'
