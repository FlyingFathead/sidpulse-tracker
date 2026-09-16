"""UI-only activity-dot persistence; no changes to musical timing or audio.

Held voices remain lit, actual note triggers brighten the dot, and a short
150 ms visual decay makes fast percussion visible between GUI refreshes.
These are note/gate indicators, not envelope followers or loudness meters.
"""
import time


class ActivityLights:
    FLASH_SECONDS = .150

    def __init__(self):
        self.generation = None
        self.seen = {}
        self.flashes = {}

    def levels(self, snapshot, now=None):
        now = time.monotonic() if now is None else now
        if snapshot.generation != self.generation:
            self.generation = snapshot.generation
            self.seen.clear()
            self.flashes.clear()
        eligible = set(snapshot.eligible)
        for number, serial in snapshot.triggers:
            if serial != self.seen.get(number):
                self.seen[number] = serial
                if snapshot.enabled and number in eligible:
                    self.flashes[number] = now
        if not snapshot.enabled:
            self.flashes.clear()
            return {}
        self.flashes = {n:t for n,t in self.flashes.items()
                        if 0 <= now-t < self.FLASH_SECONDS and n in eligible}
        active = set(snapshot.active)
        result = {}
        for number in active | self.flashes.keys():
            flash = max(0., 1.-(now-self.flashes[number])/self.FLASH_SECONDS) if number in self.flashes else 0.
            level = max(.55 if number in active else 0., flash)
            if level:
                result[number] = level
        return result
