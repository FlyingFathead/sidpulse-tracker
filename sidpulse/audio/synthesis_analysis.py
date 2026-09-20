"""Source measurements for SID inverse synthesis; NumPy only, worker-side.

Use short energy windows for attacks, long spectral windows for bass, and
weighted least squares for a decaying pitch trajectory. None of these
measurements or arrays are used by the playback engine.
"""
import math
import numpy as np

RATE = 12000


def audible_signal(values):
    """Keep subsonic SID bias changes out of pitch/impact measurements."""
    padding=RATE//4
    padded=np.pad(values,(padding,padding))
    frequency=np.fft.rfftfreq(len(padded),1/RATE)
    response=frequency**4/(frequency**4+20.**4)
    return np.fft.irfft(np.fft.rfft(padded)*response,len(padded))[padding:padding+len(values)]


def rms_envelope(values, count, window=60, hop=30):
    values = np.pad(values[:count], (0, max(0, count-len(values))))
    frames = np.lib.stride_tricks.sliding_window_view(
        np.pad(values, (window//2, window//2)), window)[::hop]
    return np.sqrt(np.mean(frames*frames, axis=1))


def spectral_features(values, count):
    """Three time/frequency resolutions, with one common amplitude scale."""
    values = np.pad(values[:count], (0, max(0, count-len(values))))
    scale = max(float(rms_envelope(values, count).max()), 1e-8)
    values = values/scale
    result = []
    for size in (128, 512, 2048):
        hop = size//4
        frames = np.lib.stride_tricks.sliding_window_view(
            np.pad(values, (size//2, size//2)), size)[::hop]
        magnitude = abs(np.fft.rfft(frames*np.hanning(size), axis=1))/size
        # Linear bins preserve the energy of a broad noise band. Log amplitude
        # retains weak partials without giving silence the same weight as a hit.
        result.append(np.log1p(magnitude*20))
    return result


class FitTarget:
    def __init__(self, values, count):
        self.count = count
        self.impact_reference = None
        values = audible_signal(values)
        self.spectra = spectral_features(values, count)
        envelope = rms_envelope(values, count)
        self.envelope = envelope/max(float(envelope.max()), 1e-8)
        self.times = np.arange(len(envelope))*.0025
        active = np.flatnonzero(self.envelope >= .12)
        self.onset = self.times[active[0]] if len(active) else 0.
        # An attack is a short event even in a sample with a long decay.
        self.weights = 1 + 4*np.exp(-np.maximum(0, self.times-self.onset)/.035)

    def loss(self, values):
        values = audible_signal(values)
        impact=0.
        if self.impact_reference:
            first=values[:min(len(values),RATE//50)]
            rms=float(np.sqrt(np.mean(first*first)))
            impact=.3*max(0.,1-rms/self.impact_reference)**2
        spectra = spectral_features(values, self.count)
        spectral = []
        noise_balance = 0.
        for size, candidate, reference in zip((128,512,2048), spectra, self.spectra):
            times = np.arange(len(reference))*(size//4)/RATE
            weights = 1+2*np.exp(-np.maximum(0,times-self.onset)/.04)
            # Relative spectral error, not the mean of thousands of bins: a
            # bass fundamental occupies few bins and must not get averaged out.
            difference=np.sum((candidate-reference)**2,axis=1)
            reference_energy=np.sum(reference**2,axis=1)
            spectral.append(float(np.sum(difference*weights)/max(np.sum(reference_energy*weights),1e-8)))
            if size == 512:
                # A snare's quieter broadband component must remain audible
                # beside its dominant bass body. Measure its energy fraction
                # separately so a loud periodic waveform cannot erase it.
                power = np.expm1(candidate)**2
                reference_power = np.expm1(reference)**2
                high = np.fft.rfftfreq(size, 1/RATE) >= 1500
                fraction = np.sqrt(power[:,high].sum(axis=1) /
                                   np.maximum(power.sum(axis=1), 1e-12))
                reference_fraction = np.sqrt(reference_power[:,high].sum(axis=1) /
                                             np.maximum(reference_power.sum(axis=1), 1e-12))
                active_weight = weights*reference_power.sum(axis=1)
                noise_balance = float(np.sum((fraction-reference_fraction)**2*active_weight) /
                                      max(active_weight.sum(), 1e-12))
        envelope = rms_envelope(values, self.count)
        envelope /= max(float(envelope.max()), 1e-8)
        energy = float(np.sum((envelope-self.envelope)**2*self.weights)/self.weights.sum())
        # Derivatives stop a slow swell winning by matching the later peak.
        attack = float(np.mean((np.diff(envelope)-np.diff(self.envelope))**2))
        return .18*sum(spectral)/3 + .6*energy + .15*attack + .6*noise_balance + impact


def source_model(values, tick, root):
    """Measure local tone/noise energy and fit f(t)=b+a*exp(-t/tau).

    The frequency grid is searched in the source spectrum. The exponential
    parameters are solved by weighted least squares for each candidate tau;
    this supplies a coherent pitch sweep instead of unrelated octave guesses.
    """
    steps = min(64, max(1, math.ceil(len(values)/RATE/tick)))
    times = (np.arange(steps)+.5)*tick
    notes, low, high, energies = [], [], [], []
    for age, time in enumerate(times):
        size = 256 if age < 2 else 1024
        center = round(time*RATE)
        start = center-size//2
        clip = np.pad(values[max(0,start):min(len(values),start+size)],
                      (max(0,-start),max(0,start+size-len(values))))[:size]
        power = abs(np.fft.rfft((clip-clip.mean())*np.hanning(size),8192))**2
        freq = np.fft.rfftfreq(8192,1/RATE)
        valid = (freq>=30)&(freq<=2500)
        peak = np.flatnonzero(valid)[np.argmax(power[valid])]
        hz = max(30.,float(freq[peak]))
        notes.append(12*np.log2(hz/16.3515978313))
        total = max(float(power.sum()),1e-12)
        low.append(float(power[freq<500].sum()/total))
        high.append(float(power[freq>=1500].sum()/total))
        energies.append(float(np.sqrt(np.mean(clip*clip))))
    notes = np.asarray(notes)
    energy = np.asarray(energies)
    low, high = np.asarray(low), np.asarray(high)
    # A local median suppresses isolated harmonic/octave errors in the body.
    smooth = notes.copy()
    for i in range(2,steps-1):smooth[i]=np.median(notes[i-1:i+2])
    hz = 16.3515978313*2**(smooth/12)
    weight = energy*low
    mask = (energy > energy.max()*.12)&(low>.55)
    chirp = smooth.copy()
    fitted = None
    if mask.sum() >= 3:
        t = times[mask]; w = np.sqrt(weight[mask])
        best = float('inf')
        for tau in np.geomspace(.005,.15,28):
            basis = np.column_stack((np.ones(len(t)),np.exp(-t/tau)))
            coefficients = np.linalg.lstsq(basis*w[:,None],hz[mask]*w,rcond=None)[0]
            floor, sweep = coefficients
            if not (25<=floor<=2000 and 0<=sweep<=5000):continue
            prediction = basis@coefficients
            error = float(np.sum(weight[mask]*(np.log(prediction)-np.log(hz[mask]))**2))
            if error < best:
                best=error;fitted=(float(floor),float(sweep),float(tau))
        if fitted:
            floor,sweep,tau=fitted
            chirp = 12*np.log2((floor+sweep*np.exp(-times/tau))/16.3515978313)
    def offsets(sequence):return np.clip(np.rint(sequence-root),-48,48).astype(int).tolist()
    return dict(pitch=offsets(smooth),chirp=offsets(chirp),low=low,high=high,
                energy=energy,chirp_parameters=fitted)
