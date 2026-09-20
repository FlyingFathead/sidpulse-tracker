import argparse
import logging
import os
from pathlib import Path
import sys


def main():
    parser = argparse.ArgumentParser(description="SIDpulse Tracker: an homage to Impulse Tracker")
    parser.add_argument("project", nargs="?", help="editable .sidpulse project")
    exports = parser.add_mutually_exclusive_group()
    exports.add_argument("--export-sid",type=Path,help="compile SID-only PSID or PCM-enhanced RSID and save .sidpulse source; no GUI")
    exports.add_argument("--export-prg",type=Path,help="compile a runnable C64 PRG and save a sibling .sidpulse source; no GUI")
    exports.add_argument("--export-audio",type=Path,help="render .wav or .mp3; no GUI or audio device")
    parser.add_argument("--audio-loops",type=int,default=0,help="extra song repeats for audio export: 0 = play once (default)")
    parser.add_argument("--digi-method", type=int, choices=(1, 2), default=None,
                        help="C64 PCM export: 1 = volume digis, display enabled (default); 2 = waveform DAC, display blanked")
    for name, help_text in (("song", "enable export-only RAM/file squeezing (default: on)"),
                            ("patterns", "condense duplicate export patterns"),
                            ("instruments", "condense identical export instruments"),
                            ("unused", "discard unused export-copy data"),
                            ("streams", "pack resident voice/timing streams")):
        parser.add_argument("--squeeze-" + name, action=argparse.BooleanOptionalAction,
                            default=None, help=help_text)
    parser.add_argument("--save-project",type=Path,help="native save path with --export-sid or --export-prg (default: export basename.sidpulse)")
    parser.add_argument("--silent", action="store_true", help="run editor without an audio device")
    parser.add_argument("--example", action="store_true", help="open the First light SID arrangement")
    parser.add_argument("--zoom", type=float, default=1.0, help="UI zoom 0.5..3.0")
    parser.add_argument("--size", default="1280x900", help="window size, e.g. 1280x900")
    parser.add_argument("--audio-buffer", type=int, choices=(256,512,1024,2048,4096,8192), help="override machine audio buffer in samples for this run")
    parser.add_argument("--log-keys", type=Path, help="write physical key events for compatibility diagnosis")
    parser.add_argument("--headless-smoke", action="store_true", help="render a few frames with SDL dummy drivers")
    parser.add_argument("--screenshot", type=Path, help="save screenshot on exit / smoke completion")
    parser.add_argument("--welcome", action="store_true", help="show the intro-song welcome screen again")
    parser.add_argument("--play-welcome-song", action="store_true", help="open Autumn at five and play it immediately, without the welcome screen")
    args = parser.parse_args()
    if args.digi_method is not None and not (args.export_sid or args.export_prg):
        parser.error("--digi-method applies only to --export-sid / --export-prg")
    if not 0 <= args.audio_loops <= 99 or (args.audio_loops and not args.export_audio):
        parser.error("--audio-loops requires --export-audio and a value from 0 to 99")
    if args.play_welcome_song and (args.project or args.example or args.welcome):
        parser.error("--play-welcome-song cannot accompany a project, --example or --welcome")
    if not (args.export_sid or args.export_prg) and any(
            getattr(args, "squeeze_" + name) is not None
            for name in ("song", "patterns", "instruments", "unused", "streams")):
        parser.error("--squeeze-* options apply only to --export-sid / --export-prg")
    if args.headless_smoke:
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        os.environ["SDL_AUDIODRIVER"] = "dummy"
    os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
    if args.log_keys:
        logging.basicConfig(filename=args.log_keys, level=logging.DEBUG, format="%(asctime)s %(message)s")
    from sidpulse.diagnostics import Diagnostics, show_crash
    diagnostics = Diagnostics()
    diagnostics.start()
    app = None
    exit_code = 0
    try:
        from sidpulse.project.format import load
        from sidpulse.song.model import Song, example_song
        from sidpulse.song.welcome import welcome_song
        size = tuple(int(n) for n in args.size.lower().split("x"))
        if len(size) != 2 or min(size) < 360:
            raise ValueError("Use WIDTHxHEIGHT with dimensions at least 360")
        metadata = {}
        welcome = False
        if not (args.export_sid or args.export_prg or args.export_audio):
            from sidpulse.ui.welcome import show_on_startup, open_dialog, play_intro
            welcome = not (args.project or args.example or args.play_welcome_song or args.headless_smoke) and (args.welcome or show_on_startup())
        if args.project:
            song, metadata = load(args.project)
            from sidpulse.project.format import compatibility_warnings
            for warning in compatibility_warnings(song):
                print('Compatibility: ' + warning, file=sys.stderr)
        else:
            song = welcome_song() if args.play_welcome_song or welcome else example_song() if args.example else Song()
        if args.export_audio:
            from sidpulse.export.audio import save_audio
            if args.save_project:
                from sidpulse.project.format import save
                save(args.save_project,song,metadata)
            result=save_audio(song,args.export_audio,loops=args.audio_loops)
            print(f'Saved {result["path"]}: {result["seconds"]:.3f}s, {result["loops"]} extra loops')
            return 0
        if args.export_sid or args.export_prg:
            from sidpulse.export.psid import compile_song,save_export
            from sidpulse.export.prg import compile_prg,save_prg
            from sidpulse.project.format import save
            target = args.export_prg or args.export_sid
            from sidpulse.export.squeeze import SqueezeOptions
            options = SqueezeOptions(digi_method=args.digi_method or 1, **{("enabled" if name == "song" else name): getattr(args, "squeeze_" + name)
                                        for name in ("song", "patterns", "instruments", "unused", "streams")
                                        if getattr(args, "squeeze_" + name) is not None})
            result = compile_prg(song, squeeze=options) if args.export_prg else compile_song(song, squeeze=options)
            native=save(args.save_project or target.with_suffix('.sidpulse'),song,metadata)
            output=save_prg(target,result) if args.export_prg else save_export(target,result)
            print(f"Saved {native} and {output}: {len(result.data):,} bytes, {result.seconds:.2f}s")
            if result.squeeze_report: print(result.squeeze_report.summary())
            for warning in result.warnings:print(warning)
            return 0
        if args.save_project:
            raise ValueError("--save-project accompanies --export-sid or --export-prg")
        from sidpulse.app import App
        app = App(song, args.project, not args.silent, size, args.zoom, args.audio_buffer)
        app.runtime_clean = False
        app.diagnostics = diagnostics
        app.restore_metadata(metadata)
        if welcome:
            open_dialog(app)
        app.start_services()
        if args.play_welcome_song:
            play_intro(app)
        app.run(frames=20 if args.headless_smoke else None, screenshot=args.screenshot)
        app.runtime_clean = True
    except KeyboardInterrupt:
        exit_code = 130
    except Exception as exc:
        diagnostics.exception('Main application failure', exc)
        recovery = None
        if app:
            app.runtime_clean = False
            recovery = app.autosave.emergency(app.editor, app.metadata(), app.path)
        show_crash(diagnostics.path, recovery, interactive=not args.headless_smoke)
        exit_code = 2
    finally:
        try:
            if app: app.close()
        except Exception as exc:
            exit_code = 2
            diagnostics.exception('Application shutdown failure', exc)
            show_crash(diagnostics.path, interactive=not args.headless_smoke)
        finally:
            diagnostics.close()
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
