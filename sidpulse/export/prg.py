"""Runnable C64 BASIC-loadable PRG using the same compiled music as PSID."""
from dataclasses import replace
from pathlib import Path
import struct

from sidpulse.export.psid import ExportError, LOAD, compile_song, save_export

PRG_LOAD = 0x0801
TITLE = 0x0C00 - PRG_LOAD
AUTHOR = TITLE + 33
TARGET = AUTHOR + 33
PAL_FLAG = TARGET + 16


def compile_prg(song):
    result = compile_song(song)
    loader = bytearray((Path(__file__).resolve().parents[1] / 'assets/prg-loader.bin').read_bytes())
    if len(loader) != LOAD - PRG_LOAD or loader[:12] != bytes.fromhex('0b080a009e32303631000000'):
        raise ExportError('Invalid bundled PRG loader')
    warnings = list(result.warnings)
    for label, offset, text in [('title', TITLE, song.title), ('author', AUTHOR, song.author)]:
        # The default uppercase/graphics PETSCII screen cannot show all Unicode.
        display = ''.join(c.upper() if c.isascii() and 32 <= ord(c) < 127 else '?' for c in text)
        if len(display) > 32 or any(not (c.isascii() and 32 <= ord(c) < 127) for c in text):
            warnings.append(f'PRG {label} display shortened/replaced; full text stays in .sidpulse.')
        value = display[:32].encode('ascii')
        loader[offset:offset + 33] = value.ljust(33, b'\0')
    target = f'{song.clock} / {song.sid_model}'.encode('ascii')
    loader[TARGET:TARGET + 16] = target.ljust(16, b'\0')
    loader[PAL_FLAG] = int(song.clock == 'PAL')
    header_size = struct.unpack_from('>H', result.data, 6)[0]
    if result.data[:4] != b'PSID' or struct.unpack_from('>H', result.data, 8)[0] != LOAD:
        raise ExportError('PRG requires the native $1000 SIDpulse player')
    data = struct.pack('<H', PRG_LOAD) + loader + result.data[header_size:]
    return replace(result, data=data, warnings=tuple(warnings))


def save_prg(path, result):
    return save_export(path, result, suffix='.prg')
