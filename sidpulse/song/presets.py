"""Factory presets. Every call returns independent SID instruments."""
from sidpulse.song.model import Instrument


def first_light_instruments():
    return {
        1: Instrument("Neon minor arp",0x40,0,7,9,3,0x640,
                      arpeggio=[0,3,7,12],arp_speed=1,pulse_depth=0x280,pulse_rate=12,gate_ticks=20),
        2: Instrument("Rubber saw bass",0x20,0,6,7,2,gate_ticks=9),
        3: Instrument("Glass major arp",0x40,0,7,8,3,0x740,
                      arpeggio=[0,4,7,12],arp_speed=1,pulse_depth=0x240,pulse_rate=16,gate_ticks=20),
        4: Instrument("Triangle kick",0x10,0,7,0,2,
                      wave_sequence=[0x40,0x10],pitch_sequence=[24,12,4,0,-5,-9,-12],gate_ticks=10),
        5: Instrument("Noise / pulse snare",0x80,0,6,0,2,0x800,
                      wave_sequence=[0x80,0x80,0x40,0x80],pitch_sequence=[12,7,0,-5],gate_ticks=8),
        6: Instrument("Closed noise hat",0x80,0,2,0,1,gate_ticks=2),
        7: Instrument("Open noise hat",0x80,0,5,0,2,gate_ticks=7),
        8: Instrument("Afterglow lead",0x40,0,7,10,5,0x500,
                      pulse_depth=0x200,pulse_rate=20,vibrato_speed=3,vibrato_depth=4,vibrato_delay=8,gate_ticks=22),
        9: Instrument("Falling glass",0x10,0,10,0,7,
                      pitch_sequence=[12,7,0],arpeggio=[0,7,12],arp_speed=2,gate_ticks=20),
    }


def available_presets():
    first=first_light_instruments()
    categories=['Minor arps','Bass','Major arps','Percussive','Percussive','Percussive','Percussive','Leads','FX']
    result=[(category,inst) for category,inst in zip(categories,first.values())]
    result.extend([
        ('Melodic',Instrument('Plain pulse',waveform=0x40,attack=0,decay=4,sustain=12,release=4)),
        ('Melodic',Instrument('Soft triangle',waveform=0x10,attack=4,decay=6,sustain=10,release=7)),
        ('Bass',Instrument('Short octave bass',waveform=0x20,attack=0,decay=5,sustain=6,release=2,
                           arpeggio=[0,-12],arp_speed=2,gate_ticks=12)),
        ('Leads',Instrument('Slow PWM lead',waveform=0x40,attack=2,decay=5,sustain=12,release=6,
                           pulse_width=0x800,pulse_depth=0x600,pulse_rate=32,vibrato_speed=2,vibrato_depth=3,vibrato_delay=10)),
    ])
    result.extend([
        ('Melodic',Instrument('Triangle bell',0x10,0,10,0,9,gate_ticks=24)),
        ('Melodic',Instrument('Plucked saw',0x20,0,6,0,3,gate_ticks=12)),
        ('Melodic',Instrument('Gentle pulse keys',0x40,1,6,8,6,0x900,pulse_depth=160,pulse_rate=24)),
        ('Percussive',Instrument('Deep triangle kick',0x10,0,8,0,2,pitch_sequence=[24,12,5,0,-7,-12,-19],gate_ticks=12)),
        ('Percussive',Instrument('Tight noise snare',0x80,0,4,0,2,gate_ticks=5)),
        ('Percussive',Instrument('Noise clap',0x80,0,3,0,1,wave_sequence=[0x80,0x10,0x80,0x10,0x80],gate_ticks=7)),
        ('Percussive',Instrument('Triangle tom',0x10,0,9,0,3,pitch_sequence=[7,3,0,-2,-3],gate_ticks=14)),
        ('Bass',Instrument('Solid pulse bass',0x40,0,5,8,2,0x500,pulse_depth=96,pulse_rate=16,gate_ticks=12)),
        ('Bass',Instrument('Round triangle bass',0x10,0,4,10,3,gate_ticks=16)),
        ('Bass',Instrument('Descending saw bass',0x20,0,5,8,2,pitch_sequence=[12,7,3,0],gate_ticks=12)),
        ('Leads',Instrument('Narrow pulse lead',0x40,0,4,12,5,0x280,vibrato_speed=3,vibrato_depth=3,vibrato_delay=6)),
        ('Leads',Instrument('Singing saw',0x20,2,5,11,6,vibrato_speed=2,vibrato_depth=4,vibrato_delay=12)),
        ('Major arps',Instrument('Bright major triad',0x40,0,5,10,3,0x800,arpeggio=[0,4,7],arp_speed=1)),
        ('Major arps',Instrument('Major seventh shimmer',0x10,0,6,10,5,arpeggio=[0,4,7,11,12,11,7,4],arp_speed=2)),
        ('Minor arps',Instrument('Minor octave cascade',0x40,0,6,9,4,0x600,arpeggio=[0,3,7,12,7,3],arp_speed=1)),
        ('Minor arps',Instrument('Minor seventh glass',0x10,0,7,8,6,arpeggio=[0,3,7,10],arp_speed=2)),
        ('FX',Instrument('Laser dive',0x40,0,8,0,3,0x400,pitch_sequence=[36,24,12,7,0,-7,-12,-24],gate_ticks=9)),
        ('FX',Instrument('Ascending beacon',0x20,0,5,9,5,pitch_sequence=[0,2,4,7,12,16,19,24],gate_ticks=12)),
    ])
    result.extend([
        ('Noise',Instrument('Pure SID noise',0x80,0,0,15,3)),
        ('Noise',Instrument('Rising wind',0x80,8,7,10,9,pitch_sequence=[-24,-20,-16,-12,-8,-4,0,4,8,12,16,20,24])),
        ('Noise',Instrument('Falling whoosh',0x80,2,10,0,8,pitch_sequence=[24,20,16,12,8,4,0,-4,-8,-12,-16,-20,-24],gate_ticks=24)),
        ('Noise',Instrument('Steam burst',0x80,0,8,0,6,gate_ticks=10)),
        ('Noise',Instrument('Two-tone siren',0x40,0,0,15,3,0x800,arpeggio=[0,7],arp_speed=18,pulse_depth=128,pulse_rate=24)),
    ])
    result.extend([
        ('Fifths',Instrument('Open pulse fifth',0x40,0,5,10,4,0x700,arpeggio=[0,7],arp_speed=1)),
        ('Fifths',Instrument('Stacked triangle fifths',0x10,1,6,10,5,arpeggio=[0,7,12,19],arp_speed=2)),
        ('Fifths',Instrument('Driving saw fifth',0x20,0,5,9,3,arpeggio=[0,7,0,12],arp_speed=1,gate_ticks=16)),
    ])
    import json
    from pathlib import Path
    from sidpulse.project.format import _construct
    source = Path(__file__).resolve().parents[1] / 'assets' / 'wavetable_drums.json'
    result.extend(('[Wavetable] Drums & Percussion', _construct(Instrument, raw))
                  for raw in json.loads(source.read_text(encoding='utf-8')))
    return result



def user_presets():
    import json
    from sidpulse.preferences import config_path
    from sidpulse.project.format import validate
    from sidpulse.song.model import Song
    presets=[];errors=[]
    for path in sorted((config_path().parent/'presets').glob('*.json')):
        try:
            if path.stat().st_size>65536:raise ValueError('Preset is too large')
            raw=json.loads(path.read_text(encoding='utf-8'))
            if raw.get('format')!='SIDPULSE_INSTRUMENT' or raw.get('version') not in (1,2):raise ValueError('Unknown preset version')
            from sidpulse.project.format import _construct
            inst=_construct(Instrument,raw['instrument']);song=Song(instruments={1:inst});validate(song)
            presets.append(('User',inst))
        except (OSError,ValueError,TypeError,KeyError,AttributeError) as exc:errors.append(path.name+': '+str(exc))
    return presets,errors


def save_user_preset(inst):
    import json,uuid
    from sidpulse.project.format import _serialize
    from sidpulse.preferences import config_path
    from sidpulse.project.format import validate
    from sidpulse.song.model import Song
    validate(Song(instruments={1:inst}))
    folder=config_path().parent/'presets';folder.mkdir(parents=True,exist_ok=True)
    path=folder/('instrument-'+uuid.uuid4().hex+'.json')
    with path.open('x',encoding='utf-8') as stream:
        json.dump({'format':'SIDPULSE_INSTRUMENT','version':2,'instrument':_serialize(inst)},stream,indent=2,ensure_ascii=False)
        stream.write('\n')
    return path


CATEGORIES=('Melodic','Percussive','[Wavetable] Drums & Percussion','Bass','Leads','Major arps','Minor arps','Fifths','Noise','FX')


def built_in_catalog():
    return sorted(available_presets(),key=lambda p:CATEGORIES.index(p[0]))
