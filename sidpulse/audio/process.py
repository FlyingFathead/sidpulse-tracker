"""Isolate the existing audio worker and SDL callback from the editor's GIL.

Only commands and bounded display snapshots cross the pipe. PCM and chip state
stay in the child; no audio block travels through IPC. Spawn avoids inheriting
SDL threads and works on both Windows and POSIX. A parent coordinator owns all
potentially blocking process/pipe operations.
"""
import multiprocessing as mp
from queue import Empty
from threading import Thread
import time


STATE_FIELDS = (
    'error', 'active', 'activity', 'levels', 'underruns', 'late_wakes',
    'over_budget', 'render_load', 'peak_render_load', 'peak', 'rms',
    'waveform', 'voice_waveforms', 'ready', 'muted', 'description',
    'buffer_frames', 'playback', 'missing_frames', 'late_callbacks',
    'callback_count', 'max_callback_interval',
    'output_device', 'output_devices', 'output_notice', 'output_list_error',
    'output_result', 'test_result', 'test_active',
    'pulse_capture',
)


def audio_process(connection, stop, song, frames, output_device=None):
    from sidpulse.audio.engine import AudioEngine
    engine = AudioEngine(song, enabled=False, buffer_frames=frames, output_device=output_device)
    engine.stop_event = stop
    def receive_commands():
        try:
            while not stop.is_set():
                if connection.poll(.05):
                    engine.commands.put(connection.recv())
        except (EOFError, BrokenPipeError, OSError):
            stop.set()
    # Receiving remains independent of status writes: a UI stall can fill the
    # status pipe, and the next command may itself contain a large song.
    reader = Thread(target=receive_commands, name='sidpulse-audio-commands', daemon=True)
    reader.start()
    worker = Thread(target=engine._run, name='sidpulse-audio', daemon=True)
    worker.start()
    try:
        next_snapshot = 0.0
        while worker.is_alive() and not stop.is_set():
            now = time.monotonic()
            if now >= next_snapshot:
                # The parent continuously drains this one small state message.
                # The audio worker never waits on serialization or pipe writes.
                connection.send(tuple(getattr(engine, key) for key in STATE_FIELDS))
                next_snapshot = now + 1 / 60
            stop.wait(.001)
    except (EOFError, BrokenPipeError, OSError):
        stop.set()
    finally:
        stop.set()
        worker.join(3)
        if worker.is_alive():
            engine.error = 'Audio worker did not stop within three seconds.'
            engine.ready = False
        try:
            connection.send(tuple(getattr(engine, key) for key in STATE_FIELDS))
        except (EOFError, BrokenPipeError, OSError):
            pass
        connection.close()


def bridge(engine):
    process = parent = child = child_stop = None
    try:
        context = mp.get_context('spawn')
        parent, child = context.Pipe()
        child_stop = context.Event()
        process = context.Process(target=audio_process,
                                  args=(child, child_stop, engine.startup, engine.buffer_frames, engine.output_device),
                                  name='sidpulse-audio', daemon=True)
        process.start()
        child.close()
        child = None
        while not engine.stop_event.is_set():
            for _ in range(256):
                try:
                    command = engine.commands.get_nowait()
                except Empty:
                    break
                parent.send(command)
            while parent.poll():
                values = parent.recv()
                for key, value in zip(STATE_FIELDS, values):
                    setattr(engine, key, value)
            if not process.is_alive():
                if not engine.error:
                    engine.error = f'Audio process exited unexpectedly ({process.exitcode}).'
                break
            engine.stop_event.wait(.001)
    except Exception as exc:
        if not engine.stop_event.is_set():
            from sidpulse.diagnostics import record_exception
            record_exception('Audio process failed', exc)
            engine.error = engine.error or f'{type(exc).__name__}: {exc}'
    finally:
        if child_stop is not None:
            child_stop.set()
        if parent is not None:
            # Drain pending status writes while the child closes its SDL device.
            deadline = time.monotonic() + 3
            while process is not None and process.pid is not None and process.is_alive() and time.monotonic() < deadline:
                try:
                    if parent.poll(.01):
                        parent.recv()
                except (EOFError, OSError):
                    break
            parent.close()
        if child is not None:
            child.close()
        if process is not None and process.pid is not None:
            process.join(.1)
            if process.is_alive():
                process.terminate()
                process.join(.5)
                engine.error = engine.error or 'Audio process required forced shutdown.'
            if process.is_alive():
                process.kill()
                process.join(.5)
            if not process.is_alive():
                process.close()
        from sidpulse.audio.activity import ActivitySnapshot
        engine.activity = ActivitySnapshot()
        engine.ready = False
        if engine.error:
            engine.description = 'Audio unavailable; editing remains available'
