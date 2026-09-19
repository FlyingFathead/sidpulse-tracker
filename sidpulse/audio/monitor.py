"""Session-only monitoring, resolved at real note triggers inside the worker."""


class InstrumentMonitor:
    def __init__(self, sid):
        self.sid = sid
        self.voices = (False, False, False)
        self.instruments = [None] * 3
        self.muted = set()
        self.solo = None
        self.mask = (False, False, False)

    def apply(self, force=False):
        mask = tuple(self.voices[v] or (number != self.solo if self.solo is not None
                                      else number in self.muted)
                     for v, number in enumerate(self.instruments))
        if force or mask != self.mask:
            self.sid.set_muted(mask)
        self.mask = mask

    def note_on(self, voice, instrument):
        self.instruments[voice] = instrument
        if self.muted or self.solo is not None:
            self.apply()

    def set_voices(self, mask):
        self.voices = tuple(bool(value) for value in mask)
        self.apply()

    def set_instruments(self, muted, solo=None):
        self.muted, self.solo = set(muted), solo
        self.apply()

    def reset(self):
        self.instruments = [None] * 3
        self.apply(force=True)
