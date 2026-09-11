"""Versioned JSON with strict validation and atomic, backed-up saves."""
from dataclasses import asdict
import json
import os
from pathlib import Path
import shutil
import tempfile

from sidpulse.song.model import Cell, ControlCell, Filter, Instrument, Pattern, Song, INSTRUMENT_PROGRAMS

MAX_BYTES = 8 * 1024 * 1024


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
    for name, maximum in (("cutoff", 2047), ("resonance", 15), ("routing", 7), ("mode", 0x70), ("volume", 15)):
        integer(getattr(song.filter, name), 0, maximum, f"filter {name}")
    if song.filter.mode & 0x0F:
        raise ProjectError("Filter mode uses LP/BP/HP bits only")
    for name in ("samples", "macros", "filter_programs", "export_config"):
        if not isinstance(getattr(song, name), dict):
            raise ProjectError(f"{name} must be an object")


def encode(song, editor=None):
    validate(song)
    return {"format": "SIDPULSE", "format_version": 6, "song": asdict(song), "editor": editor or {}}


def decode(document):
    try:
        if document.get("format") != "SIDPULSE" or type(document.get("format_version")) is not int or document["format_version"] not in (1, 2, 3, 4, 5, 6):
            raise ProjectError("Unsupported project format/version; original file has not been modified")
        raw = dict(document["song"])
        raw.setdefault("tempo", 125)  # v0.1.0 project migration
        for pat in raw["patterns"].values():
            if set(pat)-{"name","rows","controls"}:
                raise ProjectError("Unknown pattern fields; original file preserved")
        raw["patterns"] = {int(k): Pattern(v["name"], [[Cell(**c) for c in row] for row in v["rows"]], {int(r): ControlCell(**c) for r,c in v.get("controls",{}).items()}) for k, v in raw["patterns"].items()}
        raw["instruments"] = {int(k): Instrument(**v) for k, v in raw["instruments"].items()}
        raw["filter"] = Filter(**raw["filter"])
        song = Song(**raw)
        validate(song)
        editor = document.get("editor", {})
        if not isinstance(editor, dict):
            raise ProjectError("Editor metadata must be an object")
        # Unknown musical fields fail visibly, never disappear during a save.
        if set(document) - {"format", "format_version", "song", "editor"}:
            raise ProjectError("Unknown project fields; open with the version that created this file")
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
            raise ProjectError("Project exceeds the 8 MiB prototype limit")
        return decode(json.loads(data))
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise ProjectError(f"Invalid JSON project: {exc}") from exc


def save(path, song, editor=None):
    path = Path(path).expanduser()
    if path.suffix.lower() != ".sidpulse":
        path = path.with_suffix(".sidpulse")
    payload = (json.dumps(encode(song, editor), ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")
    if len(payload) > MAX_BYTES:
        raise ProjectError("Project exceeds the 8 MiB prototype limit")
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
