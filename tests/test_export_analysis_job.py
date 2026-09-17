"""Actual spawned compiler IPC, cancellation, isolation and error handling."""
from copy import deepcopy
from time import monotonic, sleep
from threading import Event
import multiprocessing as mp
import os
import sys

import pytest

from sidpulse.export.analysis_job import AnalysisJob
from sidpulse.export.psid import compile_song
from sidpulse.export.prg import compile_prg
from sidpulse.export.squeeze import SqueezeOptions
from sidpulse.song.model import Song


def wait_until(predicate, timeout=15):
    deadline = monotonic() + timeout
    while not predicate():
        if monotonic() > deadline:
            raise AssertionError('Worker did not reach the expected state')
        sleep(.005)


def stalled_worker(connection, song, options, kind):
    connection.send(('progress', 'Squeezing song...', 'Deliberately stalled test computation.'))
    while True:
        sleep(.05)


def crash_worker(connection, song, options, kind):
    os._exit(17)


def isolation_worker(connection, song, options, kind):
    connection.send(('result', ('pygame' in sys.modules, os.getpid(), song)))
    connection.close()


@pytest.mark.parametrize('kind', ['sid', 'prg'])
@pytest.mark.parametrize('squeeze', [False, True])
def test_real_spawn_matches_direct_export_and_never_writes_files(tmp_path, monkeypatch, kind, squeeze):
    song = Song()
    before = deepcopy(song)
    options = SqueezeOptions(enabled=squeeze)
    expected = (compile_prg if kind == 'prg' else compile_song)(song, squeeze=options)
    monkeypatch.chdir(tmp_path)
    job = AnalysisJob(song, options, kind)
    try:
        assert not job.started and not job.poll().done
        job.start()
        job.start()  # a one-shot worker, not a second submission
        wait_until(lambda: job.poll().done)
        update = job.poll()
        assert not update.error and not update.cancelled
        assert update.result == expected
        assert update.source == song == before and update.source is not song
        assert not list(tmp_path.iterdir())
    finally:
        assert job.close()


def test_worker_has_separate_process_and_no_pygame_import():
    job = AnalysisJob(Song(), SqueezeOptions(), 'sid', worker=isolation_worker)
    try:
        job.start()
        wait_until(lambda: job.poll().done)
        imported_pg, pid, source = job.poll().result
        assert not imported_pg and pid != os.getpid() and source == Song()
    finally:
        assert job.close()


def test_cancel_during_slow_work_reaps_the_child_without_a_result():
    original_children = {p.pid for p in mp.active_children()}
    job = AnalysisJob(Song(), SqueezeOptions(), 'sid', worker=stalled_worker)
    try:
        job.start()
        wait_until(lambda: job.poll().phase == 'Squeezing song...')
        assert not job.poll().done
        job.cancel()
        assert job.close(timeout=5)
        assert job.poll().done and job.poll().cancelled
        assert job.poll().result is None and job.poll().source is None
        assert {p.pid for p in mp.active_children()} == original_children
    finally:
        job.close()


def test_cancel_before_start_never_launches_a_child():
    job = AnalysisJob(Song(), SqueezeOptions(), 'sid', worker=stalled_worker)
    job.cancel()
    job.start()
    assert not job.started and job.poll().done and job.poll().cancelled
    assert job.close()


def test_snapshot_copy_is_off_the_calling_thread_and_cancellable():
    entered, release = Event(), Event()

    class SlowSnapshot:
        def __deepcopy__(self, memo):
            entered.set()
            assert release.wait(5), 'Test did not release the snapshot copy'
            return Song()

    job = AnalysisJob(SlowSnapshot(), SqueezeOptions(), 'sid')
    try:
        job.start()
        assert entered.wait(5)  # start already returned while the copy is blocked
        assert not job.poll().done
        job.cancel()
        release.set()
        assert job.close()
        assert job.poll().cancelled and job.poll().result is None
    finally:
        release.set()
        job.close()


@pytest.mark.parametrize('worker', [crash_worker, None])
def test_worker_errors_become_terminal_status_not_an_eternal_spinner(worker):
    song = Song()
    if worker is None:
        song.instruments.clear()
    job = AnalysisJob(song, SqueezeOptions(), 'sid', **({'worker': worker} if worker else {}))
    try:
        job.start()
        wait_until(lambda: job.poll().done)
        update = job.poll()
        assert update.error and update.result is None and not update.cancelled
    finally:
        assert job.close()


def test_startup_failure_is_reported_without_a_synchronous_fallback():
    class BrokenContext:
        def Pipe(self, **kwargs):
            raise OSError('Process creation unavailable')

    job = AnalysisJob(Song(), SqueezeOptions(), 'sid', context=BrokenContext())
    try:
        job.start()
        wait_until(lambda: job.poll().done)
        assert 'Process creation unavailable' in job.poll().error
        assert job.poll().result is None
    finally:
        assert job.close()


def test_rejects_non_export_targets():
    with pytest.raises(ValueError):
        AnalysisJob(Song(), SqueezeOptions(), 'sidpulse')


@pytest.mark.parametrize('compiler', [compile_song, compile_prg])
@pytest.mark.parametrize('squeeze', [False, True])
def test_progress_callback_reports_real_phases_without_changing_bytes(compiler, squeeze):
    updates = []
    song = Song()
    expected = compiler(song, squeeze=squeeze)
    actual = compiler(song, squeeze=squeeze, progress=lambda stage, detail: updates.append((stage, detail)))
    assert actual == expected
    stages = [stage for stage, _ in updates]
    assert stages[0] == 'Pre-analyzing...'
    assert 'Recording playback...' in stages and 'Preparing export...' in stages
    assert ('Squeezing song...' in stages) == squeeze
    if compiler is compile_prg:
        assert stages[-1] == 'Preparing PRG...'
    assert all(isinstance(detail, str) for _, detail in updates)
