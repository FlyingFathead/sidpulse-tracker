"""Versioned JSON with strict validation and atomic, backed-up saves."""
from dataclasses import fields, is_dataclass
from copy import deepcopy
import json
import os
import re
from pathlib import Path
import shutil
import tempfile

from sidpulse.song.model import Cell, ControlCell, Filter, Instrument, Pattern, Song, INSTRUMENT_PROGRAMS
from sidpulse.song.model import ENVELOPE_FIELDS
from sidpulse import __version__

MAX_BYTES = 40 * 1024 * 1024
CURRENT_FORMAT = 10
AUTOMATION_FIELDS = ('pulse_width', *ENVELOPE_FIELDS)


class ProjectError(ValueError):
    pass


def integer(value, lo, hi, label):
    if type(value) is not int or not lo <= value <= hi:
        raise ProjectError(f"{label} must be an integer in {lo}..{hi}")


def validate(song):
    for key in ("title", "author", "comments"):
        if not isinstance(getattr(song, key), str):
            raise ProjectError(f"{key} must be text")
    if song.sid_model not in ("6581", "8580") or song.clock not in ("PAL", "NTSC"):
        raise ProjectError("Choose one 6581/8580 SID with PAL or NTSC timing")
    integer(song.speed, 1, 255, "speed")
    integer(song.tempo, 32, 255, "tempo")
    if not 1 <= len(song.patterns) <= 256 or not 1 <= len(song.orders) <= 256:
        raise ProjectError("Use 1..256 patterns and orders")
    for order in song.orders:
        integer(order, 0, 255, "order pattern")
        if order not in song.patterns:
            raise ProjectError(f"Order refers to missing pattern {order:02X}")
    if not 0 <= len(song.instruments) <= 99:
        raise ProjectError("Use 0..99 SID instruments")
    for number, inst in song.instruments.items():
        integer(number, 1, 99, "instrument number")
        if not isinstance(inst.name, str):
            raise ProjectError("Instrument name must be text")
        integer(inst.waveform, 0x10, 0x80, "waveform")
        if inst.waveform not in (0x10, 0x20, 0x40, 0x80):
            raise ProjectError("Combined waveforms are not enabled in this version")
        for name in ("attack", "decay", "sustain", "release"):
            integer(getattr(inst, name), 0, 15, name)
        integer(inst.pulse_width, 0, 4095, "pulse width")
        if type(inst.sync) is not bool or type(inst.ring) is not bool or not isinstance(inst.macros, dict):
            raise ProjectError("Invalid instrument switches or macro assignments")
        for program in INSTRUMENT_PROGRAMS:
            if type(getattr(inst, program + '_enabled')) is not bool:
                raise ProjectError(f"{program} enabled switch must be true or false")
        if type(inst.sample_override) is not bool:
            raise ProjectError('Sample override must be true or false')
        integer(inst.sample_slot, 0, 99, 'sample slot')
        integer(inst.sample_gain, 0, 100, 'sample gain')
        for key, lo, hi in (("arp_speed",1,255), ("pulse_depth",0,2047), ("pulse_rate",1,255),
                            ("vibrato_speed",0,15), ("vibrato_depth",0,15), ("vibrato_delay",0,255),
                            ("gate_ticks",0,255), ("retrigger",0,255)):
            integer(getattr(inst,key),lo,hi,key)
        for key in ("arpeggio", "wave_sequence", "pitch_sequence"):
            values = getattr(inst,key)
            if not isinstance(values,list) or len(values)>64:
                raise ProjectError(f"{key} must be a list of at most 64 values")
            for v in values:
                integer(v,16,128,key) if key=="wave_sequence" else integer(v,-48,48,key)
                if key=="wave_sequence" and v not in (16,32,64,128):
                    raise ProjectError("Wave sequence values: 10,20,40,80 hex")
    if not isinstance(song.export_config,dict):raise ProjectError("Export settings must be an object")
    if "loop" in song.export_config and type(song.export_config["loop"]) is not bool:
        raise ProjectError("Song loop must be true or false")
    for number, pat in song.patterns.items():
        integer(number, 0, 255, "pattern number")
        if not isinstance(pat.name, str) or not 1 <= len(pat.rows) <= 256:
            raise ProjectError("Pattern needs a name and 1..256 rows")
        for rownum, control in pat.controls.items():
            integer(rownum,0,len(pat.rows)-1,"control row")
            for key,lo,hi in (("cutoff",0,2047),("resonance",0,15),("routing",0,7),
                              ("mode",0,112),("volume",0,15),("slide",-2047,2047)):
                v=getattr(control,key)
                if v is not None:
                    integer(v,lo,hi,f"control {key}")
                    if key=="mode" and v & 15:
                        raise ProjectError("Control filter mode uses LP/BP/HP bits")
        for row in pat.rows:
            if len(row) != 3:
                raise ProjectError("Each row must have exactly three SID voices")
            for cell in row:
                if cell.note is not None:
                    integer(cell.note, -2, 95, "note")
                if cell.instrument is not None:
                    integer(cell.instrument, 1, 99, "cell instrument")
                if not isinstance(cell.effect, str) or (cell.effect and (len(cell.effect) != 1 or not "A" <= cell.effect <= "Z")):
                    raise ProjectError("Effect must be empty or A..Z")
                if cell.parameter is not None:
                    integer(cell.parameter, 0, 255, "effect parameter")
                if cell.pulse_width is not None:
                    integer(cell.pulse_width, -1, 4095, "row pulse width")
                if cell.arp_mode is not None:
                    integer(cell.arp_mode, -1, 1, 'row arpeggio mode')
                if cell.waveform is not None:
                    if type(cell.waveform) is not int or cell.waveform not in (-1, 0x10, 0x20, 0x40, 0x80):
                        raise ProjectError('Invalid row waveform: use instrument reset or triangle/saw/pulse/noise')
                for field in ENVELOPE_FIELDS:
                    value = getattr(cell, field)
                    if value is not None:
                        integer(value, -1, 15, 'row ' + field)
    for name, maximum in (("cutoff", 2047), ("resonance", 15), ("routing", 7), ("mode", 0x70), ("volume", 15)):
        integer(getattr(song.filter, name), 0, maximum, f"filter {name}")
    if song.filter.mode & 0x0F:
        raise ProjectError("Filter mode uses LP/BP/HP bits only")
    for name in ("samples", "macros", "filter_programs", "export_config"):
        if not isinstance(getattr(song, name), dict):
            raise ProjectError(f"{name} must be an object")
    from sidpulse.audio.media import PLAYABLE_ENCODINGS, MAX_BANK_BYTES, sample_data
    total = 0
    slots = set()
    for number, sample in song.samples.items():
        if isinstance(sample, dict) and sample.get('encoding') in PLAYABLE_ENCODINGS:
            try:
                slot = int(number)
                integer(slot, 1, 99, 'sample number')
                if str(slot) in slots:
                    raise ProjectError('Duplicate sample slot')
                slots.add(str(slot))
                total += len(sample_data(sample))
                if 'original' in sample:
                    if not isinstance(sample['original'], dict) or 'original' in sample['original']:
                        raise ProjectError('Invalid nested original sample')
                    total += len(sample_data(sample['original']))
            except (ValueError, TypeError) as exc:
                raise ProjectError(f'Sample {number}: {exc}') from exc
    if total > MAX_BANK_BYTES:
        raise ProjectError('Embedded PCM bank exceeds 24 MiB. Shorten or remove samples.')


def _serialize(value):
    if is_dataclass(value):
        result = deepcopy(value._extra_fields)
        for item in fields(value):
            if item.name.startswith('_'):
                continue
            data = getattr(value, item.name)
            if isinstance(value, Cell) and item.name in (*AUTOMATION_FIELDS, 'arp_mode', 'waveform') and data is None:
                continue  # ordinary saves remain readable by format-6 applications
            if isinstance(value, Instrument) and item.name in ('sample_override', 'sample_slot', 'sample_gain'):
                if not value.sample_override and not value.sample_slot and value.sample_gain == 50:
                    continue
            result[item.name] = _serialize(data)
        return result
    if isinstance(value, dict):
        return {key: _serialize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_serialize(item) for item in value]
    return deepcopy(value)


def encode(song, editor=None):
    validate(song)
    automation = any(getattr(cell, field) is not None for pattern in song.patterns.values()
                     for row in pattern.rows for cell in row for field in AUTOMATION_FIELDS)
    version = 7 if automation else 6
    if any(i.sample_override or i.sample_slot or i.sample_gain != 50 for i in song.instruments.values()) or any(
            isinstance(s, dict) and s.get('encoding') in ('pcm_s16le_mono', 'pcm_s8_mono', 'pcm_u4le_mono') for s in song.samples.values()):
        version = 8
    if any(cell.arp_mode is not None for pattern in song.patterns.values() for row in pattern.rows for cell in row):
        version = 9
    if any(cell.waveform is not None or (cell.effect == 'Z' and cell.parameter in (0x10, 0x11, 0x1F, 0x20, 0x21, 0x2F))
           for pattern in song.patterns.values() for row in pattern.rows for cell in row):
        version = 10
    if song._source_format > CURRENT_FORMAT:
        version = song._source_format  # do not label preserved future content as an older schema
    metadata = deepcopy(editor or {})
    metadata['saved_with_version'] = __version__
    result = deepcopy(song._root_fields)
    result.update(format='SIDPULSE', format_version=version, song=_serialize(song), editor=metadata)
    return result


def _construct(cls, raw):
    if not isinstance(raw, dict):
        raise ProjectError(f'{cls.__name__} must be an object')
    known = {item.name for item in fields(cls) if not item.name.startswith('_')}
    result = cls(**{key: value for key, value in raw.items() if key in known})
    result._extra_fields = deepcopy({key: value for key, value in raw.items() if key not in known})
    return result


def compatibility_warnings(song):
    messages = []
    def version(text):
        match = re.match(r'^(\d+)\.(\d+)\.(\d+)', text)
        return tuple(map(int, match.groups())) if match else None
    saved, current = version(song._saved_with), version(__version__)
    if saved and current and saved > current:
        messages.append(f'Saved with newer SIDpulse Tracker {song._saved_with}; this is {__version__}.')
    elif saved and current and saved < current:
        messages.append(f'Saved with older SIDpulse Tracker {song._saved_with}; this is {__version__}. '
                        'The project loaded successfully. Save a separate copy before editing if you need the original.')
    if song._source_format > CURRENT_FORMAT:
        messages.append(f'Newer project format {song._source_format}; this build understands formats 1..{CURRENT_FORMAT}.')
    unknown = []
    def walk(value, path):
        if is_dataclass(value):
            unknown.extend(f'{path}.{key}' for key in value._extra_fields)
            for item in fields(value):
                if not item.name.startswith('_'):
                    walk(getattr(value, item.name), path+'.'+item.name)
        elif isinstance(value, dict):
            for key, item in value.items(): walk(item, f'{path}[{key}]')
        elif isinstance(value, list):
            for index, item in enumerate(value): walk(item, f'{path}[{index}]')
    unknown.extend('project.'+key for key in song._root_fields)
    walk(song, 'song')
    if unknown:
        messages.append(f'{len(unknown)} unfamiliar field(s) preserved, but not interpreted: '
                        + ', '.join(unknown[:4]) + (' ...' if len(unknown) > 4 else ''))
    if (saved and current and saved > current) or song._source_format > CURRENT_FORMAT or unknown:
        messages.append('Known data has been loaded. Playback/export uses supported features; unfamiliar data stays in native saves. '
                        'Keep the original when editing future features: deleting their owning row, pattern or instrument also deletes its data.')
    return tuple(messages)


def decode(document):
    try:
        if document.get("format") != "SIDPULSE" or type(document.get("format_version")) is not int or document["format_version"] < 1:
            raise ProjectError("Unsupported project format/version; original file has not been modified")
        raw = dict(document["song"])
        raw.setdefault("tempo", 125)  # v0.1.0 project migration
        raw['patterns'] = {int(k): _construct(Pattern, {**v,
            'rows': [[_construct(Cell, c) for c in row] for row in v['rows']],
            'controls': {int(r): _construct(ControlCell, c) for r, c in v.get('controls', {}).items()}})
            for k, v in raw['patterns'].items()}
        raw["instruments"] = {int(k): _construct(Instrument, v) for k, v in raw["instruments"].items()}
        raw["filter"] = _construct(Filter, raw["filter"])
        song = _construct(Song, raw)
        validate(song)
        editor = deepcopy(document.get("editor", {}))
        if not isinstance(editor, dict):
            raise ProjectError("Editor metadata must be an object")
        saved_with = editor.get('saved_with_version', '')
        song._saved_with = saved_with if isinstance(saved_with, str) else ''
        if isinstance(saved_with, str):
            editor.pop('saved_with_version', None)
        song._source_format = document['format_version']
        song._root_fields = deepcopy({key: value for key, value in document.items()
                                     if key not in {'format', 'format_version', 'song', 'editor'}})
        return song, editor
    except (KeyError, TypeError, AttributeError, ValueError) as exc:
        if isinstance(exc, ProjectError):
            raise
        raise ProjectError(f"Invalid SIDpulse project: {exc}") from exc


def load(path):
    path = Path(path).expanduser()
    if path.suffix.lower() != ".sidpulse":
        raise ProjectError("Open a .sidpulse project. SID import/remapping is a later milestone.")
    try:
        with path.open("rb") as stream:
            data = stream.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES:
            raise ProjectError("Project exceeds the 40 MiB limit")
        return decode(json.loads(data))
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise ProjectError(f"Invalid JSON project: {exc}") from exc


def save(path, song, editor=None):
    path = Path(path).expanduser()
    if path.suffix.lower() != ".sidpulse":
        path = path.with_suffix(".sidpulse")
    payload = (json.dumps(encode(song, editor), ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")
    if len(payload) > MAX_BYTES:
        raise ProjectError("Project exceeds the 40 MiB limit")
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        if path.exists():
            shutil.copy2(path, path.with_suffix(path.suffix + ".bak"))
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)
    return path
