from types import SimpleNamespace
from copy import deepcopy
import pytest
from sidpulse.song.model import Instrument
from sidpulse.ui.envelope import envelope_points,envelope_value,attack_caption,ATTACK_MS

class Rect:
    def __init__(self,x,y,w,h):self.x,self.y,self.width,self.height=x,y,w,h
    def __iter__(self):return iter((self.x,self.y,self.width,self.height))

@pytest.mark.parametrize('size',[(0,0,1,1),(8,11,410,180),(30,20,800,500)])
def test_zero_attack_is_vertical_but_caption_does_not_claim_zero_ms(size):
    rect=Rect(*size);inst=Instrument(attack=0);before=deepcopy(inst)
    points=envelope_points(rect,inst)
    assert points[0][0]==points[1][0]==rect.x
    assert envelope_value(points[1],rect,'attack')=={'attack':0}
    assert inst==before and '2.03ms' in attack_caption(0,'PAL')
    assert ATTACK_MS[0]==2

@pytest.mark.parametrize('rate',range(16))
@pytest.mark.parametrize('field',['attack','decay','release'])
def test_each_handle_roundtrips_every_hex_rate(field,rate):
    rect=Rect(11,15,600,200);inst=Instrument(attack=rate,decay=rate,release=rate,sustain=6)
    point=envelope_points(rect,inst)[{'attack':1,'decay':2,'release':4}[field]]
    assert envelope_value(point,rect,field)[field]==rate

@pytest.mark.parametrize('sustain',range(16))
def test_sustain_all_levels_and_ordered_geometry(sustain):
    rect=Rect(0,0,600,200);inst=Instrument(sustain=sustain)
    points=envelope_points(rect,inst)
    assert envelope_value(points[3],rect,'sustain')=={'sustain':sustain}
    assert all(a[0]<=b[0] for a,b in zip(points,points[1:]))


def test_drag_clamps_rate_and_preserves_decays_existing_mapping():
    rect=Rect(10,10,100,100)
    assert envelope_value((-20,10),rect,'attack')=={'attack':0}
    assert envelope_value((999,10),rect,'attack')=={'attack':15}
    assert envelope_value((62,90),rect,'decay')=={'decay':15,'sustain':3}
    assert 'NTSC' in attack_caption(0,'NTSC') and '1.96ms' in attack_caption(0,'NTSC')
