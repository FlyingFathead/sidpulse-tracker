"""Finite, sample-clocked host audio export through the live playback engine."""
from array import array
from copy import deepcopy
from fractions import Fraction
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import wave

from sidpulse.audio.media import ffmpeg_path, process_options
from sidpulse.audio.output import OutputConditioner
from sidpulse.playback.sequencer import Sequencer
from sidpulse.project.format import validate

SAMPLE_RATE = 48000


def duration_frames(song, progress=None):
    """Find one finite traversal, including speed/tempo, Bxx and Cxx changes."""
    from sidpulse.export.psid import RecordingSID
    from sidpulse.playback.voices import supported
    copy = deepcopy(song)
    for inst in copy.instruments.values():
        inst.sample_override = False  # duration needs tracker timing, no decoded PCM
    seq = Sequencer(RecordingSID(song.clock))
    seq._predicting = True  # omit ADSR lookahead; it cannot change transport time
    seq.start(copy, loop=False)
    seen, elapsed = set(), Fraction(0)
    for tick in range(400000):
        seq._boundary()
        seq.sid.events.clear()
        if seq.status != 'playing':
            return elapsed
        if seq.tick == 0:
            position = (seq.order, seq.row)
            if position in seen:
                raise ValueError('Song revisits an order/row through Bxx/Cxx. Make the order traversal finite, '
                                 'then use the export Loops field for whole-song repeats.')
            seen.add(position)
            for cell in copy.patterns[seq.pattern].rows[seq.row]:
                if not supported(cell.effect, cell.parameter or 0):
                    raise ValueError(f'Audio export cannot execute {cell.effect}{cell.parameter or 0:02X}.')
        elapsed += Fraction(SAMPLE_RATE * 5, seq.tempo * 2)
        if elapsed > SAMPLE_RATE * 7200:
            raise ValueError('Audio export is limited to two hours. Shorten the arrangement.')
        seq.frames = int(seq.next_tick)
        if progress and tick % 256 == 0:
            progress('Checking song length', f'{tick:,} ticks / {float(elapsed) / SAMPLE_RATE:.1f}s')
    raise ValueError('Audio export exceeded its finite traversal limit.')


def render_audio(song, path, *, kind='wav', loops=0, progress=None):
    """Write a new staging file. Use save_audio() for atomic destination writes.

    0 loops = one pass. Session mutes/solos do not alter the full-song export.
    """
    validate(song)
    if kind not in ('wav', 'mp3') or type(loops) is not int or not 0 <= loops <= 99:
        raise ValueError('Choose WAV or MP3 and 0..99 extra loops (0 = play once).')
    encoder = ffmpeg_path() if kind == 'mp3' else None
    from sidpulse.audio.media import sample_data
    for number, inst in song.instruments.items():
        if inst.sample_override:
            sample = song.samples.get(str(inst.sample_slot), song.samples.get(inst.sample_slot))
            try:
                sample_data(sample)
            except ValueError as exc:
                raise ValueError(f'Instrument {number:02d}: {exc}') from exc
    total = int(duration_frames(song, progress) * (loops + 1))
    if total > SAMPLE_RATE * 7200:
        raise ValueError('Total audio export, including loops, must be at most two hours.')
    from sidpulse.sid.backend_residfp import ReSIDfpBackend, set_filter
    sid = ReSIDfpBackend(song.sid_model, SAMPLE_RATE, song.clock)
    set_filter(sid, song.filter)
    sid.render(SAMPLE_RATE)  # match live startup DC settling, outside musical time
    seq = Sequencer(sid)
    seq.start(deepcopy(song), loop=loops > 0)
    conditioner = OutputConditioner()
    conditioner.target = 1.
    path = Path(path)
    wav_path = path if kind == 'wav' else path.with_suffix('.render.wav')
    try:
        with wave.open(str(wav_path), 'wb') as output:
            output.setparams((1, 2, SAMPLE_RATE, total, 'NONE', 'not compressed'))
            written = 0
            while written < total:
                count = min(2048, total - written)
                # Keep the last 5 ms inside the requested duration as an end ramp.
                if written < total - 240:
                    count = min(count, total - 240 - written)
                else:
                    conditioner.target = 0.
                seq.loop_override = seq.loops < loops
                pcm = conditioner.process(seq.render(count))
                if sys.byteorder != 'little':
                    values = array('h', pcm); values.byteswap(); pcm = values.tobytes()
                output.writeframesraw(pcm)
                written += count
                if progress and (written == total or written // 24000 != (written - count) // 24000):
                    progress('Rendering ' + kind.upper(), f'{written / total:.0%} / {written / SAMPLE_RATE:.1f} of {total / SAMPLE_RATE:.1f}s')
        if kind == 'mp3':
            if progress:
                progress('Encoding MP3', 'High quality VBR (LAME quality 2)')
            result = subprocess.run([encoder, '-v', 'error', '-nostdin', '-y', '-i', str(wav_path),
                                     '-map', '0:a:0', '-codec:a', 'libmp3lame', '-q:a', '2',
                                     '-metadata', 'title=' + song.title, '-metadata', 'artist=' + song.author,
                                     '-f', 'mp3', str(path)], capture_output=True, timeout=600, **process_options())
            if result.returncode:
                raise ValueError('MP3 encoding failed: ' + result.stderr.decode('utf-8', 'replace')[-1600:])
        return dict(path=str(path), kind=kind, frames=total, seconds=total / SAMPLE_RATE,
                    loops=loops, bytes=path.stat().st_size)
    finally:
        if kind == 'mp3':
            wav_path.unlink(missing_ok=True)


def publish_audio(staged, target):
    """Only publish a complete export; existing output gets a .bak on success."""
    target = Path(target)
    with Path(staged).open('rb+') as stream:
        os.fsync(stream.fileno())
    if target.exists():
        shutil.copy2(target, target.with_suffix(target.suffix + '.bak'))
    os.replace(staged, target)
    return target


def save_audio(song, target, *, kind=None, loops=0, progress=None):
    target = Path(target).expanduser().absolute()
    kind = kind or target.suffix.lower().lstrip('.')
    if kind not in ('wav', 'mp3'):
        raise ValueError('Audio destination must be WAV or MP3.')
    target = target.with_suffix('.' + kind)
    with tempfile.TemporaryDirectory(prefix='.sidpulse-audio-', dir=target.parent) as folder:
        result = render_audio(song, Path(folder) / ('render.' + kind), kind=kind, loops=loops, progress=progress)
        publish_audio(result['path'], target)
    return {**result, 'path': str(target)}


def media_worker(connection, source, options, unused_kind):
    """AnalysisJob owns spawn/IPC/cancellation; all output here is temporary."""
    if os.name == 'posix':
        import signal
        os.setsid()  # a private group containing only this job and its encoder
        def terminate_group(signum, frame):
            signal.signal(signal.SIGTERM, signal.SIG_DFL)
            os.killpg(os.getpid(), signal.SIGTERM)
        signal.signal(signal.SIGTERM, terminate_group)
    try:
        def progress(phase, detail):
            connection.send(('progress', phase, detail))
        if options['operation'] == 'import':
            from sidpulse.audio.media import import_sample, squeeze_sample
            progress('Importing sample', Path(source).name)
            result = import_sample(source)
            if options.get('auto_squeeze', True):
                progress('Auto-squeezing sample', '4,000 Hz / 4-bit; keeping the original for Restore.')
                try:
                    result = squeeze_sample(result, 4000, 4,
                                            normalize_before=options.get('normalize_before', False),
                                            normalize_after=options.get('normalize_after', False))
                except ValueError as exc:
                    raise ValueError(f'{exc} To import at its original quality, turn off '
                                     'Auto-squeeze on import in F3.') from exc
        elif options['operation'] == 'squeeze':
            from sidpulse.audio.media import squeeze_sample
            progress('Squeezing sample', f'{options["rate"]:,} Hz / {options["bits"]}-bit')
            result = squeeze_sample(source, options['rate'], options['bits'],
                                    normalize_before=options.get('normalize_before', False),
                                    normalize_after=options.get('normalize_after', False))
        elif options['operation'] == 'normalize':
            from sidpulse.audio.media import normalize_sample
            progress('Normalizing sample', 'Selected range; same bit depth. Original kept for Restore.')
            result = normalize_sample(source)
        elif options['operation'] == 'volume':
            from sidpulse.audio.media import adjust_sample_volume
            progress('Adjusting sample volume', f'{options["percent"]}% of the marked range; original kept for Restore.')
            result = adjust_sample_volume(source, options['percent'])
        elif options['operation'] in ('synthesize', 'synthesize_all'):
            if os.name == 'posix':
                try: os.nice(5)
                except OSError: pass
            if options['operation'] == 'synthesize_all':
                from sidpulse.audio.synthesis_batch import synthesize_mapped_samples
                result = synthesize_mapped_samples(source, progress=progress)
            else:
                from sidpulse.audio.synthesize import synthesize_sample
                result = synthesize_sample(source, model=options['model'], clock=options['clock'],
                                           tempo=options['tempo'], progress=progress)
        else:
            result = render_audio(source, options['staged'], kind=options['kind'],
                                  loops=options['loops'], progress=progress)
        connection.send(('result', result))
    except Exception as exc:
        import traceback
        connection.send(('error', f'{type(exc).__name__}: {exc}', traceback.format_exc()))
    finally:
        connection.close()
