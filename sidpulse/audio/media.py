"""Local audio import and optional FFmpeg discovery. No device is opened here."""
import base64
import os
from pathlib import Path
import shutil
import subprocess
import wave

SAMPLE_ENCODING = 'pcm_s16le_mono'
PLAYABLE_ENCODINGS = (SAMPLE_ENCODING, 'pcm_s8_mono', 'pcm_u4le_mono')
MAX_SAMPLE_SECONDS = 30
MAX_SAMPLE_BYTES = 48000 * MAX_SAMPLE_SECONDS * 2
MAX_BANK_BYTES = 24 * 1024 * 1024
AUDIO_SUFFIXES = ('.wav', '.mp3', '.flac', '.ogg', '.aif', '.aiff', '.m4a')


def ffmpeg_path(required=True):
    """Portable/WinGet locations follow audio-bitsqueezer's bounded lookup."""
    explicit = os.environ.get('SIDPULSE_FFMPEG', '').strip().strip('"')
    found = shutil.which(explicit or 'ffmpeg')
    if not found and not explicit:
        root = Path(__file__).resolve().parents[2]
        directories = [root / 'tools/ffmpeg/bin', root / 'tools/ffmpeg']
        if os.name == 'nt':
            for variable, suffix in (('LOCALAPPDATA', 'Microsoft/WinGet'), ('ProgramFiles', 'WinGet')):
                if os.environ.get(variable):
                    base = Path(os.environ[variable]) / suffix
                    directories.append(base / 'Links')
                    for package in sorted((base / 'Packages').glob('Gyan.FFmpeg*'), reverse=True):
                        directories.append(package / 'bin')
                        directories.extend(p / 'bin' for p in package.glob('ffmpeg-*'))
        name = 'ffmpeg.exe' if os.name == 'nt' else 'ffmpeg'
        found = next((value for directory in directories
                      if (value := shutil.which(str(directory / name)))), None)
    if not found and required:
        raise ValueError('FFmpeg is required for MP3 export, compressed sample import and sample rate conversion. '
                         'Install ffmpeg (Ubuntu: sudo apt install ffmpeg; Windows: winget install Gyan.FFmpeg), '
                         'or set SIDPULSE_FFMPEG to its executable. PCM WAV import works without it '
                         'when Auto-squeeze on import is off; WAV export always works without it.'
                         + (' The configured SIDPULSE_FFMPEG could not be found.' if explicit else ''))
    return found


def process_options():
    return {'creationflags': subprocess.CREATE_NO_WINDOW} if os.name == 'nt' else {}


def sample_data(sample):
    if not isinstance(sample, dict) or sample.get('encoding') not in PLAYABLE_ENCODINGS:
        raise ValueError('This sample slot has no playable PCM. Import a WAV or other audio file first.')
    if not isinstance(sample.get('name'), str):
        raise ValueError('PCM sample name must be text.')
    value = sample.get('data', '')
    if not isinstance(value, str) or len(value) > (MAX_SAMPLE_BYTES + 2) // 3 * 4:
        raise ValueError('PCM sample exceeds the 30-second / 48 kHz limit.')
    try:
        data = base64.b64decode(value, validate=True)
    except (ValueError, TypeError) as exc:
        raise ValueError('Invalid embedded PCM data.') from exc
    rate, root = sample.get('sample_rate'), sample.get('root_note', 48)
    if type(rate) is not int or not 1000 <= rate <= 48000:
        raise ValueError('PCM sample rate must be 1000..48000 Hz.')
    if type(root) is not int or not 0 <= root <= 95:
        raise ValueError('Sample root note must be C-0..B-7.')
    frames = sample.get('frames')
    if type(frames) is not int or not 1 <= frames <= rate * MAX_SAMPLE_SECONDS:
        raise ValueError('PCM samples must contain at least one frame and at most 30 seconds.')
    encoding = sample['encoding']
    expected = frames * 2 if encoding == SAMPLE_ENCODING else frames if encoding == 'pcm_s8_mono' else (frames + 1) // 2
    if len(data) != expected:
        raise ValueError('PCM sample frame count does not match its embedded data.')
    sample_bounds(sample)
    if encoding != SAMPLE_ENCODING:
        import numpy as np
        if encoding == 'pcm_s8_mono':
            values = np.frombuffer(data, np.int8).astype(np.int16) * 256
        else:
            packed = np.frombuffer(data, np.uint8)
            codes = np.empty(len(packed) * 2, dtype=np.int16)
            codes[::2], codes[1::2] = packed & 15, packed >> 4
            # audio-bitsqueezer's low-nibble-first storage and quantizer bin centres.
            values = codes[:frames] * 4096 - 30720
        data = values.astype('<i2').tobytes()
    return data


def sample_bounds(sample):
    start, end = sample.get('start', 0), sample.get('end', sample['frames'])
    if type(start) is not int or type(end) is not int or not 0 <= start < end <= sample['frames']:
        raise ValueError('Sample range must satisfy 0 <= start < end <= frame count; end is exclusive.')
    return start, end


def make_sample(name, pcm, rate=48000, root_note=48):
    sample = dict(name=str(name), encoding=SAMPLE_ENCODING, sample_rate=rate,
                  root_note=root_note, frames=len(pcm) // 2,
                  data=base64.b64encode(pcm).decode('ascii'))
    sample_data(sample)
    return sample


def import_sample(path):
    """Keep source rate for PCM WAV; compressed formats decode at 48 kHz.

    Mono downmix only: never auto-trim, normalize, or silently truncate a sample.
    """
    path = Path(path).expanduser().resolve()
    if not path.is_file():
        raise ValueError('Choose an existing local audio file.')
    if path.suffix.lower() not in AUDIO_SUFFIXES:
        raise ValueError('Choose WAV, MP3, FLAC, OGG, AIFF or M4A audio.')
    import numpy as np
    if path.suffix.lower() == '.wav':
        try:
            with wave.open(str(path), 'rb') as source:
                rate, channels, width = source.getframerate(), source.getnchannels(), source.getsampwidth()
                frames = source.getnframes()
                if frames > rate * MAX_SAMPLE_SECONDS:
                    raise ValueError('Sample is longer than 30 seconds. Trim it before importing.')
                if 1000 <= rate <= 48000 and channels in (1, 2) and width in (1, 2, 3, 4):
                    raw = source.readframes(frames)
                    if len(raw) != frames * channels * width:
                        raise ValueError('WAV data is truncated.')
                    if width == 1:
                        values = (np.frombuffer(raw, np.uint8).astype(np.int32) - 128) * 256
                    elif width in (2, 4):
                        values = np.frombuffer(raw, '<i' + str(width)).astype(np.float64) / (1 if width == 2 else 65536)
                    else:
                        b = np.frombuffer(raw, np.uint8).reshape(-1, 3).astype(np.int32)
                        values = b[:, 0] | b[:, 1] << 8 | b[:, 2] << 16
                        values = ((values ^ 0x800000) - 0x800000) / 256
                    if channels == 2:
                        values = values.reshape(-1, 2).mean(axis=1)
                    pcm = np.clip(np.rint(values), -32768, 32767).astype('<i2').tobytes()
                    return make_sample(path.name, pcm, rate)
        except (wave.Error, EOFError):
            pass  # Float/compressed WAV uses the same optional decoder as MP3.
    command = [ffmpeg_path(), '-v', 'error', '-nostdin', '-i', str(path),
               '-map', '0:a:0', '-vn', '-t', str(MAX_SAMPLE_SECONDS + 1),
               '-ac', '1', '-ar', '48000', '-f', 's16le', 'pipe:1']
    try:
        result = subprocess.run(command, capture_output=True, timeout=60, **process_options())
    except subprocess.TimeoutExpired as exc:
        raise ValueError('Audio decoding timed out; try a shorter local audio file.') from exc
    if result.returncode:
        raise ValueError('Audio decoding failed: ' + result.stderr.decode('utf-8', 'replace')[-1600:])
    if len(result.stdout) > MAX_SAMPLE_BYTES:
        raise ValueError('Sample is longer than 30 seconds. Trim it before importing.')
    return make_sample(path.name, result.stdout)


def _normalize_values(values):
    """Peak gain only, with 0.1 dB headroom; constant data is left alone."""
    import numpy as np
    values = np.asarray(values, dtype=np.int32)
    if values.min() == values.max():
        return values
    peak = max(abs(int(values.min())), abs(int(values.max())))
    target = 32767 * 10 ** (-0.1 / 20)
    return np.clip(np.rint(values * (target / peak)), -32768, 32767).astype(np.int32)


def _encode_values(values, bits):
    import numpy as np
    if bits == 4:
        codes = ((values + 32768) >> 12).astype(np.uint8)
        if len(codes) & 1:
            codes = np.append(codes, np.uint8(8))
        return (codes[::2] | codes[1::2] << 4).tobytes(), 'pcm_u4le_mono'
    if bits == 8:
        return (values >> 8).astype(np.int8).tobytes(), 'pcm_s8_mono'
    return values.astype('<i2').tobytes(), SAMPLE_ENCODING


def normalize_sample(sample):
    """Normalize the marked range, keeping rate, bit depth and outside frames."""
    import numpy as np
    from copy import deepcopy
    values = np.frombuffer(sample_data(sample), '<i2').astype(np.int32)
    start, end = sample_bounds(sample)
    values[start:end] = _normalize_values(values[start:end])
    bits = {SAMPLE_ENCODING: 16, 'pcm_s8_mono': 8, 'pcm_u4le_mono': 4}[sample['encoding']]
    data, _ = _encode_values(values, bits)
    result = dict(sample, data=base64.b64encode(data).decode('ascii'))
    source = deepcopy(sample.get('original', sample))
    source.pop('original', None)
    result['original'] = source
    return result


def adjust_sample_volume(sample, percent=100):
    """Apply relative gain to the marked frames, preserving the stored format."""
    import numpy as np
    from copy import deepcopy
    if type(percent) is not int or not 0 <= percent <= 200:
        raise ValueError('Use a volume from 0 to 200%.')
    values = np.frombuffer(sample_data(sample), '<i2').astype(np.int32)
    if percent == 100:
        return deepcopy(sample)
    start, end = sample_bounds(sample)
    values[start:end] = np.clip(np.rint(values[start:end] * (percent / 100)), -32768, 32767)
    bits = {SAMPLE_ENCODING: 16, 'pcm_s8_mono': 8, 'pcm_u4le_mono': 4}[sample['encoding']]
    data, _ = _encode_values(values, bits)
    result = dict(sample, data=base64.b64encode(data).decode('ascii'))
    source = deepcopy(sample.get('original', sample))
    source.pop('original', None)
    result['original'] = source
    return result


def squeeze_sample(sample, rate=4000, bits=4, *, normalize_before=False, normalize_after=False):
    """Bake the selected range into compact PCM; retain the original for Restore.

    Matches audio-bitsqueezer's anti-aliased FFmpeg resampling and four-bit
    quantization convention. This is host PCM preparation, not C64 replay code.
    """
    import numpy as np
    from copy import deepcopy
    if type(rate) is not int or not 1000 <= rate <= 48000 or bits not in (4, 8, 16):
        raise ValueError('Choose 1000..48000 Hz and 4, 8 or 16 bits.')
    start, end = sample_bounds(sample)
    pcm = sample_data(sample)[start * 2:end * 2]
    if normalize_before:
        pcm = _normalize_values(np.frombuffer(pcm, '<i2')).astype('<i2').tobytes()
    if rate != sample['sample_rate']:
        result = subprocess.run([ffmpeg_path(), '-v', 'error', '-nostdin', '-f', 's16le',
                                 '-ar', str(sample['sample_rate']), '-ac', '1', '-i', 'pipe:0',
                                 '-af', f'aresample={rate}:filter_size=64:cutoff=0.94',
                                 '-f', 's16le', 'pipe:1'], input=pcm, capture_output=True,
                                timeout=60, **process_options())
        if result.returncode:
            raise ValueError('Sample resampling failed: ' + result.stderr.decode('utf-8', 'replace')[-1600:])
        pcm = result.stdout
    values = np.frombuffer(pcm, '<i2').astype(np.int32)
    data, encoding = _encode_values(values, bits)
    source = deepcopy(sample.get('original', sample))
    source.pop('original', None)
    result = dict(name=sample['name'], encoding=encoding, sample_rate=rate,
                  frames=len(values), root_note=sample.get('root_note', 48),
                  data=base64.b64encode(data).decode('ascii'), original=source)
    sample_data(result)
    return normalize_sample(result) if normalize_after else result
