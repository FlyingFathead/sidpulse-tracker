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
from sidpulse.audio.synthesis_analysis import FitTarget, source_model, rms_envelope, audible_signal

RATE = 12000
MAX_SECONDS = 2
MAX_CANDIDATES = 320
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
    # reSIDfp's external filter can retain a large DC startup transient well
    # beyond 50 ms. It must settle before measuring an instrument's envelope.
    sid.render(RATE)
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
    energy = rms_envelope(audible_signal(values),len(values))
    peak = max(float(energy.max()),1e-8)
    onset = np.flatnonzero(energy>=peak*.12)
    # Drum recordings often carry a few milliseconds of quiet lead-in. Align
    # a detected short transient to note-on instead of turning that gap into
    # a slow ADSR attack. Sustained/slow sounds keep their selected timing.
    percussive = (int(np.argmax(energy))*.0025 < .08 and
                  float(np.mean(energy[len(energy)*3//4:])) < peak*.25)
    lead = min(max(0,len(values)-round(.012*RATE)),round(.03*RATE),
               round(onset[0]*.0025*RATE)) if percussive and len(onset) else 0
    if lead:values=values[lead:]
    root = sample.get('root_note',48)
    tick = 2.5/tempo
    offsets, confidence = _pitch_track(values,tick,root)
    # Short windows attenuate autocorrelation of low, decaying kick tones.
    # Keep those tonal candidates; the SID render score still competes with noise.
    pitched = confidence >= .25
    typical = int(np.median(np.asarray(offsets)[pitched])) if pitched.any() else 0
    contour = [offset if good else typical for offset,good in zip(offsets,pitched)]
    count = len(values)+RATE//8  # include a silent tail when judging release
    target = FitTarget(values, count)
    measured = source_model(values, tick, root)
    drum_like = bool(percussive and (np.ptp(measured['pitch'][:4]) >= 4 or
                                     float(measured['high'].max()) > .08))
    if drum_like:
        reference = render_instrument(Instrument(waveform=64,attack=0,decay=0,sustain=15),
                                      48,.08,model,clock,tempo)
        reference=audible_signal(reference)
        target.impact_reference=float(np.sqrt(np.mean(reference[:RATE//50]**2)))*.8
    target_envelope = target.envelope
    # Estimate attack from its rising edge, not the maximum of a 43 ms window.
    # A low kick can peak later because of oscillator phase and pitch descent.
    rising = np.flatnonzero(target_envelope >= .7)
    peak_time = rising[0]*.0025 if len(rising) else 0.
    last_level = float(np.mean(target_envelope[max(0,round(duration*400)-20):max(1,round(duration*400))]))
    attack = int(np.argmin(abs(np.asarray(ATTACK_MS)-min(80,peak_time*1000))))
    if percussive:attack=min(attack,1)
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
        if tested>=MAX_CANDIDATES:return float('inf')
        audio = render_instrument(inst,root,count/RATE,model,clock,tempo)
        waves=inst.wave_sequence or [inst.waveform]
        changes=sum(a!=b for a,b in zip(waves,waves[1:]))
        score = target.loss(audio) + .0006*changes
        cache[key]=score;tested+=1
        # Tiny differences are dominated by native output dithering, especially
        # in the silent tail. Retain the earlier, simpler stage in such ties.
        if score<best_score-.0002:best,best_score=inst,score
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
    # Source-derived pitch trajectories and short attack/body stages. A noise
    # oscillator's clock pitch is independent of a drum's tonal fundamental.
    # Explore these jointly, before committing to a single waveform family.
    for pitches in (measured['pitch'], measured['chirp']):
        for wave in (16,64):
            for a in (0,1):
                candidate=replace(base,waveform=wave,attack=a,pitch_sequence=pitches,
                                  sustain=0,decay=8,release=5)
                evaluate(candidate)
                for noise_position in (0,1):
                    waves=[wave]*len(pitches);new_pitches=pitches[:]
                    if noise_position>=len(waves):continue
                    waves[noise_position]=128;new_pitches[noise_position]=max(-48,min(48,84-root))
                    evaluate(replace(candidate,wave_sequence=waves,pitch_sequence=new_pitches))
    for threshold in (.08,.18):
        for noise_note in (48,54,60,72,84,95):
            pitches=measured['pitch'][:]
            waves=[128 if high>threshold else 16 for high in measured['high']]
            mixed=[p if w!=128 else max(-48,min(48,noise_note-root)) for p,w in zip(pitches,waves)]
            evaluate(replace(base,attack=0,decay=8,sustain=0,release=5,
                             waveform=waves[0],wave_sequence=waves,pitch_sequence=mixed))
    # Coordinate search keeps cost bounded and preserves the best earlier fit.
    for field,choices in (('decay',range(16)),('attack',range(2) if percussive else range(7)),
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
        for wave,noise_note in ((16,0),(32,0),(64,0),(128,48),(128,54),(128,60),(128,72),(128,84),(128,95)):
            new_waves=waves[:];new_pitches=pitches[:]
            new_waves[start:end]=[wave]*(end-start)
            if wave==128:
                new_pitches[start:end]=[max(-48,min(48,noise_note-root))]*(end-start)
            elif any(w==128 for w in waves[start:end]):
                new_pitches[start:end]=contour[start:end]
            evaluate(replace(current,wave_sequence=new_waves,pitch_sequence=new_pitches))
    # Refit the envelope after the waveform stages change. In particular, a
    # pulse/noise switch changes loudness and must not inherit an old slow swell.
    for field,choices in (('attack',range(2) if percussive else range(5)),('decay',range(16)),
                          ('gate_ticks',sorted({1,2,3,4,gate,max(1,gate//2)})),
                          ('release',range(10))):
        current=best
        for value in choices:evaluate(replace(current,**{field:value}))
    if drum_like:
        current=best
        waves=(current.wave_sequence or [current.waveform])*1
        waves=waves+[waves[-1]]*(max(2,len(contour))-len(waves))
        pitches=current.pitch_sequence or [0]
        pitches=pitches+[pitches[-1]]*(len(waves)-len(pitches))
        for wave in (16,32,64,128):
            for shift in (0,7,12):
                attack_pitches=pitches[:]
                attack_pitches[0]=max(-48,min(48,pitches[0]+shift if wave!=128 else 84-root))
                evaluate(replace(current,attack=0,wave_sequence=[wave]+waves[1:],
                                 pitch_sequence=attack_pitches))
    # No mutable relationship to the source sample survives in the instrument.
    if best.wave_sequence and len(set(best.wave_sequence))==1:
        best=replace(best,waveform=best.wave_sequence[0],wave_sequence=[])
    if best.pitch_sequence and len(set(best.pitch_sequence))==1:
        best=replace(best,pitch_sequence=best.pitch_sequence[:1] if best.pitch_sequence[0] else [])
    for field in ('wave_sequence','pitch_sequence'):
        sequence=getattr(best,field)
        while len(sequence)>1 and sequence[-1]==sequence[-2]:sequence.pop()
    waveforms = set(best.wave_sequence or [best.waveform])
    kind = 'mixed' if 128 in waveforms and len(waveforms)>1 else 'noise' if waveforms == {128} else 'tonal'
    details=dict(version=2,source_name=sample['name'],source_sha256=hashlib.sha256(raw).hexdigest(),
                 root_note=root,tempo=tempo,model=model,clock=clock,
                 kind=kind,
                 candidates=tested,score=best_score,seconds=duration,
                 analysis='multiresolution spectrum, transient envelope, least-squares pitch decay',
                 pitch_decay=list(measured['chirp_parameters']) if measured['chirp_parameters'] else None,
                 percussive=percussive,
                 impact_fit=drum_like,
                 onset_compensation_ms=lead*1000/RATE)
    best._extra_fields['sample_synthesis']=details
    best._extra_fields['editor_frozen']=True
    return dict(instrument=best,details=details)
