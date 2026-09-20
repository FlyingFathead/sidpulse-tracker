"""Cancellable, UI-independent SID/PRG analysis.

A coordinator thread owns a single spawned compiler process and its private pipe.
Neither process startup, song copying, IPC reads nor process joins run in the SDL
thread. Only immutable status snapshots cross back to the UI. The compiler child
never imports pygame, opens a device or writes project/preferences/export files.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, replace
import logging
import multiprocessing as mp
from threading import Event, Lock, Thread
from typing import Any

LOG = logging.getLogger("sidpulse.export.analysis")


@dataclass(frozen=True)
class AnalysisUpdate:
    phase: str = "Pre-analyzing..."
    detail: str = "Preparing an isolated song snapshot."
    done: bool = False
    cancelled: bool = False
    result: Any = None
    source: Any = None
    error: str | None = None


def compile_worker(connection, song, options, kind, *, compare=False):
    """Spawn entry point; the pipe is private to this one analysis job."""
    try:
        # Like sample fitting, compilation is throughput work. Let playback
        # and the UI win CPU contention without changing their clocks or PCM.
        # Only adjust a spawned child, never an embedding caller's process.
        if mp.parent_process() is not None:
            import os
            if hasattr(os, 'nice'):
                try:
                    os.nice(5)
                except OSError:
                    pass
        from sidpulse.export.psid import compile_song
        from sidpulse.export.prg import compile_prg

        def progress(phase, detail):
            connection.send(("progress", phase, detail))

        compiler = compile_prg if kind == "prg" else compile_song
        if compare and options.enabled:
            from sidpulse.export.comparison import compile_comparison
            result = compile_comparison(song, options, kind, progress=progress)
        else:
            result = compiler(song, squeeze=options, progress=progress)
        connection.send(("result", result))
    except Exception as exc:
        # Send text, not arbitrary exception objects (some cannot be unpickled).
        import traceback
        try:
            connection.send(("error", f"{type(exc).__name__}: {exc}", traceback.format_exc()))
        except (OSError, EOFError):
            pass  # The UI cancelled and discarded this job's pipe.
    finally:
        connection.close()


def comparison_worker(connection, song, options, kind):
    compile_worker(connection, song, options, kind, compare=True)


class AnalysisJob:
    """One-shot analysis with nonblocking start/poll/cancel operations.

    ``start`` only starts the small coordinator thread. ``close`` is reserved for
    application shutdown/tests; ordinary frames and Cancel never wait for joins.
    Spawn is intentional: SDL/audio may already have threads on Linux or Windows.
    A supplied context/worker is useful for embedding and independent tests.
    """

    def __init__(self, song, options, kind, *, context=None, worker=compile_worker):
        if kind not in ("sid", "prg"):
            raise ValueError("Analysis target must be SID or PRG")
        self._song = song
        self._options = options
        self._kind = kind
        self._context = context if context is not None else mp.get_context("spawn")
        self._worker = worker
        self._lock = Lock()
        self._cancel = Event()
        self._update = AnalysisUpdate()
        self._thread = None

    @property
    def started(self):
        return self._thread is not None

    def poll(self):
        with self._lock:
            return self._update

    def _publish(self, **values):
        with self._lock:
            self._update = replace(self._update, **values)

    def start(self):
        if self._thread is not None or self._cancel.is_set() or self.poll().done:
            return
        self._thread = Thread(target=self._run, name="sidpulse-export-analysis", daemon=True)
        try:
            self._thread.start()
        except RuntimeError as exc:
            self._thread = None
            self._song = None
            self._publish(done=True, error=f"Could not start export analysis: {exc}")

    def cancel(self):
        self._cancel.set()
        if self._thread is None:
            self._song = None
            self._publish(done=True, cancelled=True, result=None, source=None)

    def close(self, timeout=5.0):
        self.cancel()
        if self._thread is not None:
            self._thread.join(timeout)
            return not self._thread.is_alive()
        return True

    def _run(self):
        reader = writer = process = None
        source = result = error = None
        try:
            # The export modal blocks song edits. Copying here also keeps large
            # project snapshots off the display thread. The UI checks this exact
            # snapshot against the live project before accepting the result.
            source = deepcopy(self._song)
            self._song = None
            if self._cancel.is_set():
                return
            self._publish(detail="Starting the export compiler.")
            reader, writer = self._context.Pipe(duplex=False)
            process = self._context.Process(
                target=self._worker, args=(writer, source, self._options, self._kind),
                name="sidpulse-export-compiler", daemon=True,
            )
            process.start()
            writer.close()
            writer = None
            while not self._cancel.is_set():
                # All potentially blocking IPC is owned by this thread, not SDL.
                if reader.poll(0.05):
                    message = reader.recv()
                    if message[0] == "progress":
                        self._publish(phase=message[1], detail=message[2])
                    elif message[0] == "result":
                        result = message[1]
                        break
                    elif message[0] == "error":
                        error = message[1]
                        LOG.error("Export analysis failed:\n%s", message[2])
                        break
                    else:
                        raise ValueError("Invalid export worker message")
                elif not process.is_alive():
                    error = f"Export analysis worker exited without a result (exit code {process.exitcode})."
                    break
        except (EOFError, BrokenPipeError):
            error = "Export analysis worker stopped before returning a result. No file was written."
        except Exception as exc:
            error = f"Export analysis could not complete: {type(exc).__name__}: {exc}"
            LOG.exception("Export analysis coordinator failed")
        finally:
            # No shared queues or locks are owned by the child. On cancellation it
            # is safe to terminate this computation and discard its private pipe.
            if process is not None:
                try:
                    if process.pid is not None:
                        if process.is_alive() and (self._cancel.is_set() or result is None):
                            process.terminate()
                        process.join(1.0)
                        if process.is_alive():
                            process.kill()
                            process.join(1.0)
                        if process.is_alive():
                            error = "Export analysis worker did not stop cleanly."
                            LOG.error(error)
                        else:
                            process.close()
                except (OSError, ValueError, AssertionError):
                    LOG.exception("Export analysis worker cleanup failed")
            for pipe in (reader, writer):
                if pipe is not None:
                    pipe.close()
            self._song = None
            if self._cancel.is_set():
                self._publish(done=True, cancelled=True, result=None, source=None, error=None)
            elif result is None or error is not None:
                self._publish(done=True, error=error or "Export analysis returned no result.")
            else:
                self._publish(done=True, phase="Analysis complete", detail="", result=result, source=source)
