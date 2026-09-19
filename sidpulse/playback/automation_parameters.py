"""Recordable row parameters; SID envelopes are nibbles and PW is 12 bits."""
PARAMETERS = {
    'attack': ('Attack', 'A', 15),
    'decay': ('Decay', 'D', 15),
    'sustain': ('Sustain', 'S', 15),
    'release': ('Release', 'R', 15),
    'pulse_width': ('Pulse width', 'PW', 4095),
}
