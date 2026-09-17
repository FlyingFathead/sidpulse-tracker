"""Runnable C64 BASIC-loadable PRG using the same compiled music as PSID."""
from dataclasses import replace
from pathlib import Path
import struct

from sidpulse.export.psid import ExportError, LOAD, compile_song, save_export
from sidpulse.export.squeeze import COMPACT_PRG_LOAD

PRG_LOAD = 0x0801
TITLE = 0x0C00 - PRG_LOAD
AUTHOR = TITLE + 33
TARGET = AUTHOR + 33
PAL_FLAG = TARGET + 16


def compile_prg(song, *, squeeze=None, progress=None):
    result = compile_song(song, squeeze=squeeze, _prg=True, progress=progress)
    if progress is not None:
        progress("Preparing PRG...", "Adding the standalone C64 loader and title display.")
    load = struct.unpack_from('>H', result.data, 8)[0]
    compact = load == COMPACT_PRG_LOAD
    image = 'prg-loader-squeezed.bin' if compact else 'prg-loader.bin'
    loader = bytearray((Path(__file__).resolve().parents[1] / 'assets' / image).read_bytes())
    if load not in (LOAD, COMPACT_PRG_LOAD) or len(loader) != load - PRG_LOAD or loader[:12] != bytes.fromhex('0b080a009e32303631000000'):
        raise ExportError('Invalid bundled PRG loader')
    warnings = list(result.warnings)
    title = 0x0961 - PRG_LOAD if compact else TITLE
    author, target_offset = title + 33, title + 66
    pal_flag = target_offset + 16
    for label, offset, text in [('title', title, song.title), ('author', author, song.author)]:
        # The default uppercase/graphics PETSCII screen cannot show all Unicode.
        display = ''.join(c.upper() if c.isascii() and 32 <= ord(c) < 127 else '?' for c in text)
        if len(display) > 32 or any(not (c.isascii() and 32 <= ord(c) < 127) for c in text):
            warnings.append(f'PRG {label} display shortened/replaced; full text stays in .sidpulse.')
        value = display[:32].encode('ascii')
        loader[offset:offset + 33] = value.ljust(33, b'\0')
    target = f'{song.clock} / {song.sid_model}'.encode('ascii')
    loader[target_offset:target_offset + 16] = target.ljust(16, b'\0')
    loader[pal_flag] = int(song.clock == 'PAL')
    header_size = struct.unpack_from('>H', result.data, 6)[0]
    if result.data[:4] != b'PSID' or load not in (LOAD, COMPACT_PRG_LOAD):
        raise ExportError('PRG requires a native SIDpulse player')
    data = struct.pack('<H', PRG_LOAD) + loader + result.data[header_size:]
    report = replace(result.squeeze_report, wrapper_bytes=len(loader),
                     original_wrapper_bytes=LOAD - PRG_LOAD, zero_page_bytes=max(4, result.squeeze_report.zero_page_bytes), stack_bytes=max(7, result.squeeze_report.stack_bytes + 3))
    return replace(result, data=data, warnings=tuple(warnings), squeeze_report=report)


def save_prg(path, result):
    return save_export(path, result, suffix='.prg')
