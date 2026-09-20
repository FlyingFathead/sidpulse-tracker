"""Bounded sample-to-SID approximation using actual SID renders as candidates.

All analysis runs in the media worker. The result is an ordinary SID instrument
with optional editor protection: no hidden player, filter edits or new effects.
"""
from dataclasses import replace
import hashlib
import math
from pathlib import Path

import numpy as np

from sidpulse.audio.media import sample_bounds, sample_data
from sidpulse.song.model import Instrument

RATE = 12000
MAX_SECONDS = 2
ATTACK_MS = (2, 8, 16, 24, 38, 56, 68, 80, 100, 250, 500, 800, 1000, 3000, 5000, 8000)
DECAY_MS = tuple(x * 3 for x in ATTACK_MS)


def _resample(values, count):
    """Fourier resampling for analysis only; padding avoids an endpoint join."""
    count = max(1, count)
    spectrum = np.fft.rfft(values)
    result = np.zeros(count // 2 + 1, complex)
    common = min(count, len(values))
    result[:common // 2 + 1] = spectrum[:common // 2 + 1]
    if common % 2 == 0 and count != len(values):
        result[common // 2] *= 2 if count < len(values) else .5
    return np.fft.irfft(result, count) * (count / len(values))


def _features(values, count):
    values = np.pad(values[:count], (0, max(0, count-len(values))))
    windows = np.lib.stride_tricks.sliding_window_view(np.pad(values, (256,256)), 512)[::120]
    spectrum = abs(np.fft.rfft(windows * np.hanning(512), axis=1))
    frequencies = np.fft.rfftfreq(512, 1/RATE)
    edges = np.geomspace(23, RATE/2+1, 29)
    bands = np.stack([np.sqrt(np.mean(spectrum[:, (frequencies>=lo)&(frequencies<hi)]**2, axis=1))
                      if np.any((frequencies>=lo)&(frequencies<hi)) else np.zeros(len(windows))
                      for lo,hi in zip(edges,edges[1:])], axis=1)
    envelope = np.sqrt(np.mean(windows**2, axis=1))
    scale = max(float(envelope.max()), 1e-8)
    return np.log1p(bands / (scale*10)), envelope / scale


def _pitch_track(values, tick, root):
    """Windowed autocorrelation, with confidence so noise is not forced to pitch."""
    offsets, confidence = [], []
    window = 1024
    duration = len(values)/RATE
    for age in range(min(64, max(1, math.ceil(duration/tick)))):
        center = round((age*tick + min(tick/2, duration/2))*RATE)
        start = center-window//2
        clip = values[max(0,start):min(len(values), start+window)]
        clip = np.pad(clip,(max(0,-start), max(0,start+window-len(values))))[:window]
        clip = (clip-clip.mean()) * np.hanning(window)
        corr = np.fft.irfft(abs(np.fft.rfft(clip, 2048))**2, 2048)[:window]
        lo, hi = 4, min(window//2, round(RATE/30))
        peaks = np.flatnonzero((corr[lo:hi]>corr[lo-1:hi-1]) & (corr[lo:hi]>=corr[lo+1:hi+1]))+lo
        if corr[0]<1e-10 or not len(peaks):
            offsets.append(0);confidence.append(0.);continue
        best = float(corr[peaks].max())
        if best <= 0:
            offsets.append(0);confidence.append(0.);continue
        lag = int(peaks[np.flatnonzero(corr[peaks] >= best*.92)[0]])
        quality = float(corr[lag]/corr[0])
        note = round(12*math.log2((RATE/lag)/16.3515978313))
        offsets.append(max(-48,min(48,note-root)))
        confidence.append(quality)
    return offsets, np.asarray(confidence)


def render_instrument(inst, root, seconds, model='8580', clock='PAL', tempo=125):
    from sidpulse.sid.backend_residfp import ReSIDfpBackend
    from sidpulse.playback.voices import Audition
    sid = ReSIDfpBackend(model, RATE, clock)
    sid.write(24,15)
    sid.render(RATE//20)  # settle the mixer before scoring musical time
    audition = Audition(sid, tempo)
    audition.trigger(0,root,inst)
    return np.frombuffer(audition.render(round(seconds*RATE)), '<i2').astype(float)


def synthesize_sample(sample, *, model='8580', clock='PAL', tempo=125, progress=None):
    decoded = sample_data(sample)
    start,end = sample_bounds(sample)
    raw = decoded[start*2:end*2]
    duration = (end-start)/sample['sample_rate']
    if duration > MAX_SECONDS:
        raise ValueError('Synthesis currently fits marked ranges up to 2 seconds. Move the end marker and try again.')
    if duration < .012:
        raise ValueError('Select at least 12 ms of audio for waveform and envelope analysis.')
    source = np.frombuffer(raw, '<i2').astype(float)
    source -= source.mean()
    if np.max(abs(source)) < 8:
        raise ValueError('The marked range is silent or constant; there is no changing waveform to synthesize.')
    padding = round(sample['sample_rate']*.05)
    padded = np.pad(source,(padding,padding))
    resampled = _resample(padded, round(len(padded)*RATE/sample['sample_rate']))
    values = resampled[round(padding*RATE/sample['sample_rate']):][:round(duration*RATE)]
    values /= max(abs(values).max(),1)
    root = sample.get('root_note',48)
    tick = 2.5/tempo
    offsets, confidence = _pitch_track(values,tick,root)
    # Short windows attenuate autocorrelation of low, decaying kick tones.
    # Keep those tonal candidates; the SID render score still competes with noise.
    pitched = confidence >= .25
    typical = int(np.median(np.asarray(offsets)[pitched])) if pitched.any() else 0
    contour = [offset if good else typical for offset,good in zip(offsets,pitched)]
    count = len(values)+RATE//8  # include a silent tail when judging release
    target_spectrum, target_envelope = _features(values,count)
    peak_time = np.argmax(target_envelope)*.01
    last_level = float(np.mean(target_envelope[max(0,round(duration*100)-5):max(1,round(duration*100))]))
    attack = int(np.argmin(abs(np.asarray(ATTACK_MS)-min(80,peak_time*1000))))
    decay = int(np.argmin(abs(np.asarray(DECAY_MS)-max(6,duration*700))))
    gate = max(1,min(255,round(duration/tick)))
    sustain = max(0,min(15,round(last_level*15))) if last_level>.4 else 0
    base = Instrument(name=Path(sample['name']).stem[:20]+' / SID fit', attack=attack,
                      decay=decay,sustain=sustain,release=0,gate_ticks=gate,
                      arpeggio_enabled=False, pulse_enabled=False, vibrato_enabled=False,
                      retrigger_enabled=False)
    cache = {}; tested = 0
    best = None; best_score = float('inf')
    def evaluate(inst):
        nonlocal tested,best,best_score
        key = (inst.waveform,inst.attack,inst.decay,inst.sustain,inst.release,inst.gate_ticks,
               inst.pulse_width,tuple(inst.wave_sequence),tuple(inst.pitch_sequence))
        if key in cache:return cache[key]
        audio = render_instrument(inst,root,count/RATE,model,clock,tempo)
        spectrum,envelope = _features(audio,count)
        score = float(np.mean((spectrum-target_spectrum)**2) + .8*np.mean((envelope-target_envelope)**2))
        cache[key]=score;tested+=1
        if score<best_score:best,best_score=inst,score
        if progress and tested%8==0:
            progress('Matching SID instruments', f'{tested} candidates auditioned; comparing spectrum, pitch and envelope.')
        return score
    if progress:progress('Analyzing the marked sample','Estimating pitch, noisy sections and amplitude envelope.')
    # Tonal shapes, followed by noise models. Each is scored through the SID.
    if pitched.any():
        for wave,width in ((16,2048),(32,2048),(64,256),(64,512),(64,1024),(64,2048)):
            for pitches in ([typical],contour):
                inst=replace(base,waveform=wave,pulse_width=width,pitch_sequence=list(pitches))
                evaluate(inst)
                if not pitched.all():
                    waves=[wave if good else 128 for good in pitched]
                    mixed=[p if good else min(48,typical+36) for p,good in zip(contour,pitched)]
                    evaluate(replace(inst,wave_sequence=waves,pitch_sequence=mixed))
    for note in (36,48,60,72,84,95):
        evaluate(replace(base,waveform=128,pitch_sequence=[max(-48,min(48,note-root))]))
    # Coordinate search keeps cost bounded and preserves the best earlier fit.
    for field,choices in (('decay',range(16)),('attack',range(7)),
                          ('sustain',(0,2,4,6,8,10,12,15)),
                          ('gate_ticks',sorted({max(1,gate-n) for n in (0,1,2,4,8)})),
                          ('release',range(8))):
        current=best
        for value in choices:evaluate(replace(current,**{field:value}))
    current=best
    for shift in (-2,-1,1,2):
        evaluate(replace(current,pitch_sequence=[max(-48,min(48,p+shift)) for p in current.pitch_sequence]))
    if best.waveform==64:
        current=best
        for width in (256,512,768,1024,1536,2048,2560,3072,3584):evaluate(replace(current,pulse_width=width))
    # Fit a genuine SID wavetable, including noisy attacks on tonal bodies.
    # Resolve the first eight ticks individually, then at most eight wider
    # regions. This bounds the search while retaining short drum transients.
    steps = len(contour)
    cuts = sorted(set(range(min(8, steps)+1)) | set(np.linspace(min(8,steps),steps,9,dtype=int)))
    for start,end in zip(cuts,cuts[1:]):
        if start == end: continue
        current=best
        waves=[current.wave_sequence[min(i,len(current.wave_sequence)-1)]
               if current.wave_sequence else current.waveform for i in range(steps)]
        pitches=[current.pitch_sequence[min(i,len(current.pitch_sequence)-1)]
                 if current.pitch_sequence else 0 for i in range(steps)]
        for wave in (16,32,64,128):
            new_waves=waves[:];new_pitches=pitches[:]
            new_waves[start:end]=[wave]*(end-start)
            if wave==128:
                new_pitches[start:end]=[max(-48,min(48,84-root))]*(end-start)
            elif any(w==128 for w in waves[start:end]):
                new_pitches[start:end]=contour[start:end]
            evaluate(replace(current,wave_sequence=new_waves,pitch_sequence=new_pitches))
    # No mutable relationship to the source sample survives in the instrument.
    if best.wave_sequence and len(set(best.wave_sequence))==1:
        best=replace(best,waveform=best.wave_sequence[0],wave_sequence=[])
    if best.pitch_sequence and len(set(best.pitch_sequence))==1:
        best=replace(best,pitch_sequence=best.pitch_sequence[:1] if best.pitch_sequence[0] else [])
    for field in ('wave_sequence','pitch_sequence'):
        sequence=getattr(best,field)
        while len(sequence)>1 and sequence[-1]==sequence[-2]:sequence.pop()
    details=dict(version=1,source_name=sample['name'],source_sha256=hashlib.sha256(raw).hexdigest(),
                 root_note=root,tempo=tempo,model=model,clock=clock,
                 kind='tonal' if pitched.mean()>.75 else 'noise' if pitched.mean()<.25 else 'mixed',
                 candidates=tested,score=best_score,seconds=duration)
    best._extra_fields['sample_synthesis']=details
    best._extra_fields['editor_frozen']=True
    return dict(instrument=best,details=details)
