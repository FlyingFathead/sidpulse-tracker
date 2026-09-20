"""Fit each PCM-mapped sample once; return proposals without changing the song."""
from copy import deepcopy

from sidpulse.audio.media import sample_data, sample_bounds
from sidpulse.audio.synthesize import synthesize_sample, MAX_SECONDS


def synthesize_mapped_samples(song, *, progress=None):
    mapped = [(number, inst) for number, inst in sorted(song.instruments.items())
              if inst.sample_override]
    if not mapped:
        raise ValueError('There are no PCM-mapped instruments to synthesize.')
    samples = {}
    # Check all references/ranges before doing an expensive fit. Any failure
    # discards the whole batch; the caller applies nothing until review.
    for number, inst in mapped:
        slot = inst.sample_slot
        if slot in samples:
            continue
        sample = song.samples.get(str(slot), song.samples.get(slot))
        try:
            sample_data(sample)
            start, end = sample_bounds(sample)
            if not .012 <= (end-start)/sample['sample_rate'] <= MAX_SECONDS:
                raise ValueError('Select a range from 12 ms to 2 seconds in F3.')
        except (ValueError, TypeError) as exc:
            raise ValueError(f'Instrument {number:02d}, sample {slot:02d}: {exc}') from exc
        samples[slot] = sample
    fitted = {}
    for index, (slot, sample) in enumerate(samples.items(), 1):
        def report(phase, detail):
            if progress:
                progress(f'Sample {slot:02d} ({index}/{len(samples)}) / {phase}', detail)
        try:
            fitted[slot] = synthesize_sample(sample, model=song.sid_model,
                                            clock=song.clock, tempo=song.tempo, progress=report)
        except ValueError as exc:
            raise ValueError(f'Sample {slot:02d}, {sample["name"]}: {exc}') from exc
    proposals = []
    for number, old in mapped:
        result = deepcopy(fitted[old.sample_slot])
        result['instrument'].name = old.name
        result['details']['sample_slot'] = old.sample_slot
        proposals.append(dict(number=number, slot=old.sample_slot, result=result))
    return dict(proposals=proposals, fitted_samples=len(fitted))
