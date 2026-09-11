"""Shared field order for F4 rendering, keyboard focus and validated editing."""
FIELDS=('name','waveform','attack','decay','sustain','release','pulse_width','sync','ring',
        'arpeggio','arp_speed','wave_sequence','pitch_sequence','pulse_depth','pulse_rate',
        'vibrato_speed','vibrato_depth','vibrato_delay','gate_ticks','retrigger')
LABELS=('Name','Waveform','Attack','Decay','Sustain','Release','Pulse width','Sync','Ring modulation',
        'Arpeggio notes','Arp ticks / step','Wave sequence','Pitch sequence','Pulse depth','Pulse quarter-cycle',
        'Vibrato speed','Vibrato depth','Vibrato delay','Gate-off tick','Retrigger ticks')
SEQUENCES=('arpeggio','wave_sequence','pitch_sequence')
LIMITS={'arp_speed':(1,255),'pulse_depth':(0,2047),'pulse_rate':(1,255),
        'vibrato_speed':(0,15),'vibrato_depth':(0,15),'vibrato_delay':(0,255),'gate_ticks':(0,255),'retrigger':(0,255)}
PROGRAM_ROWS = {9:'arpeggio', 11:'wave_sequence', 12:'pitch_sequence',
                13:'pulse', 15:'vibrato', 18:'gate', 19:'retrigger'}
PROGRAM_LABELS = {'arpeggio':'Arpeggio', 'wave_sequence':'Wave sequence',
                  'pitch_sequence':'Pitch sequence', 'pulse':'Pulse motion',
                  'vibrato':'Vibrato', 'gate':'Auto gate-off', 'retrigger':'Retrigger'}


def display(inst,key):
    value=getattr(inst,key)
    if key in SEQUENCES:
        return ' '.join(f'{x:02X}' if key=='wave_sequence' else str(x) for x in value) or '(empty)'
    return str(value)
