"""First paint, animation, responsive cancellation, and async continuations."""
from copy import deepcopy
from dataclasses import replace
from time import monotonic

import pytest
pg = pytest.importorskip('pygame')
from sidpulse.app import App
from sidpulse.export.analysis_job import AnalysisJob, AnalysisUpdate
from sidpulse.export.psid import compile_song
from sidpulse.export.squeeze import SqueezeOptions
from sidpulse.preferences import load_squeeze_options
from sidpulse.ui import export_squeezer as ui
from sidpulse.ui.themes import palette


class ControlledJob:
    """Deterministic UI completion control; real spawn tests live separately."""
    def __init__(self, song, options, kind, **kwargs):
        self.source = deepcopy(song)
        self.options = options
        self.kind = kind
        self.started = False
        self.starts = 0
        self.cancelled = False
        self.update = AnalysisUpdate()

    def start(self):
        self.started = True
        self.starts += 1

    def poll(self):
        return self.update

    def cancel(self):
        self.cancelled = True

    def close(self, timeout=5):
        self.cancel()
        self.update = replace(self.update, done=True, cancelled=True)
        return True

    def finish(self, *, error=None):
        self.update = AnalysisUpdate(done=True, error=error, source=self.source,
                                     result=None if error else compile_song(self.source, squeeze=self.options))


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setattr(ui, 'AnalysisJob', ControlledJob)
    value = App(audio=False)
    yield value
    value.close()


def key(app, value, mod=0):
    app.handle(pg.event.Event(pg.KEYDOWN, key=value, mod=mod, unicode=''))


def frame(app):
    pg.event.pump()
    app.renderer.render(app)
    pg.display.flip()
    app.poll_export_analysis()


def finish(app):
    job = app.dialog['job']
    job.finish()
    frame(app)


@pytest.mark.parametrize('kind', ['sid', 'prg'])
def test_menu_handler_returns_before_analysis_and_first_frame_has_progress(app, kind):
    before = deepcopy(app.editor.song)
    app.begin_export(kind)
    job = app.dialog['job']
    assert app.dialog['busy'] and not job.started and app.dialog['result'] is None
    app.poll_export_analysis()
    assert not job.started  # nothing expensive before the first paint
    frame(app)
    assert job.started and job.starts == 1
    assert app.dialog['phase'] == 'Pre-analyzing...'
    assert app.screen.get_rect().contains(app.dialog['progress_rect'])
    assert app.editor.song == before
    frame(app)
    assert job.starts == 1


@pytest.mark.parametrize('theme', ['Classic crimson', 'Charcoal crimson', 'High contrast'])
def test_bar_animates_in_slider_colour_without_a_slider_handle(app, monkeypatch, theme):
    clock = [100.0]
    monkeypatch.setattr(ui, 'monotonic', lambda: clock[0])
    app.appearance['theme'] = theme
    app.appearance['colors'] = {'SLIDER': '#125aad'}
    app.begin_export('prg')
    frame(app)
    rect = app.dialog['progress_rect'].copy()
    first = pg.image.tobytes(app.screen.subsurface(rect), 'RGB')
    clock[0] += 1.2
    frame(app)
    second = pg.image.tobytes(app.screen.subsurface(rect), 'RGB')
    assert first != second
    assert bytes(palette(app.appearance)['SLIDER']) in first
    assert bytes(palette(app.appearance)['SLIDER']) in second
    assert [(action, value) for _, action, value in app.renderer.hits] == [('squeeze_button', 'cancel')]


@pytest.mark.parametrize('size', [(360, 360), (480, 360), (1280, 900), (1920, 1080)])
@pytest.mark.parametrize('zoom', [.5, 1., 3.])
def test_busy_indicator_and_cancel_stay_visible_at_supported_sizes(app, size, zoom):
    app.screen = pg.display.set_mode(size, pg.RESIZABLE)
    app.zoom = zoom
    app.begin_export('sid')
    frame(app)
    rect = app.dialog['progress_rect'].copy()
    assert app.screen.get_rect().contains(rect)
    assert all(app.screen.get_rect().contains(hit) for hit, _, _ in app.renderer.hits)
    assert [(action,value) for _,action,value in app.renderer.hits
            if not action.startswith('squeeze_scroll_')] == [('squeeze_button','cancel')]
    key(app, pg.K_PAGEDOWN)
    frame(app)
    assert app.dialog['progress_rect'] == rect  # pinned above the scrolling body
    for hit, _, _ in app.renderer.hits:
        assert not rect.colliderect(hit)
    job = app.dialog['job']
    key(app, pg.K_ESCAPE)
    assert app.dialog is None and job.cancelled


def test_busy_controls_cannot_launch_duplicates_save_or_edit_the_song(app, monkeypatch):
    saves = []
    monkeypatch.setattr(app, 'save_project', lambda: saves.append('save'))
    before = deepcopy(app.editor.song)
    app.begin_export('sid')
    frame(app)
    job = app.dialog['job']
    for keycode in (pg.K_a, pg.K_s, pg.K_e, pg.K_F5, pg.K_z):
        key(app, keycode)
    ui.toggle(app, 0)
    assert app.dialog['job'] is job and job.starts == 1 and not saves
    assert app.dialog['options'] == SqueezeOptions()
    assert app.editor.song == before and load_squeeze_options() == SqueezeOptions()
    frame(app)
    rect = next(rect for rect, _, action in app.renderer.hits if action == 'cancel')
    app.handle(pg.event.Event(pg.MOUSEBUTTONDOWN, button=1, pos=rect.center))
    assert job.cancelled and app.dialog is None and not saves


def test_late_cancelled_result_cannot_replace_a_new_dialog(app):
    app.begin_export('sid')
    frame(app)
    old = app.dialog['job']
    key(app, pg.K_ESCAPE)
    app.begin_export('prg')
    current = app.dialog['job']
    old.finish()
    frame(app)
    assert old.cancelled and app.dialog['job'] is current
    assert app.dialog['busy'] and app.dialog['target'] == 'prg'
    assert app.dialog['result'] is None


@pytest.mark.parametrize('action', ['save', 'export'])
def test_reanalysis_continues_only_after_a_successful_result(app, monkeypatch, action):
    saved = []
    monkeypatch.setattr(app, 'save_project', lambda: saved.append('native'))
    app.begin_export('sid')
    finish(app)
    ui.toggle(app, 0)
    ui.activate(app, action)
    assert app.dialog['busy'] and app.dialog['pending_action'] == action
    assert not saved and load_squeeze_options().enabled
    finish(app)
    assert app.dialog is None and not load_squeeze_options().enabled
    if action == 'save':
        assert saved == ['native'] and callable(app.after_save)
        app.after_save()
    assert app.page == 'files' and app.file_mode == 'sid'
    assert not app.browser.export_result.squeeze_report.enabled


def test_cancelling_reanalysis_discards_pending_save_and_preferences(app, monkeypatch):
    saved = []
    monkeypatch.setattr(app, 'save_project', lambda: saved.append('native'))
    app.begin_export('sid')
    finish(app)
    ui.toggle(app, 0)
    ui.activate(app, 'save')
    job = app.dialog['job']
    key(app, pg.K_ESCAPE)
    job.finish()
    app.poll_export_analysis()
    assert not saved and app.dialog is None and app.after_save is None
    assert load_squeeze_options().enabled


def test_worker_error_shows_error_and_allows_retry(app):
    app.begin_export('sid')
    app.dialog['job'].finish(error='ExportError: unsupported effect')
    frame(app)
    assert not app.dialog['busy'] and app.dialog['result'] is None
    assert 'unsupported effect' in app.dialog['error']
    frame(app)
    assert len([r for r, a, _ in app.renderer.hits if a == 'squeeze_button']) == 4
    ui.activate(app, 'analyze')
    assert app.dialog['busy'] and not app.dialog.get('error')


def test_changed_snapshot_is_rejected_without_saving(app):
    app.begin_export('sid')
    app.editor.song.title = 'Changed outside the modal'
    finish(app)
    assert app.dialog['result'] is None and 'changed during analysis' in app.dialog['error']
    assert load_squeeze_options().enabled


def test_completed_job_waits_safely_under_a_notice(app):
    app.begin_export('sid')
    frame(app)
    dialog = app.dialog
    app.notice('Test notice', 'No export should occur here.', return_dialog=dialog)
    dialog['job'].finish()
    app.poll_export_analysis()
    assert app.dialog['kind'] == 'notice' and dialog['result'] is None
    key(app, pg.K_ESCAPE)
    frame(app)
    assert app.dialog is dialog and not dialog['busy'] and dialog['result'] is not None


def test_real_slow_child_keeps_frame_loop_resize_and_cancel_responsive(monkeypatch):
    from test_export_analysis_job import stalled_worker
    monkeypatch.setattr(ui, 'AnalysisJob', lambda *args, **kwargs: AnalysisJob(*args, worker=stalled_worker))
    app = App(audio=False)
    try:
        app.begin_export('prg')
        job = app.dialog['job']
        deadline = monotonic() + 10
        frames = 0
        while app.dialog['phase'] != 'Squeezing song...':
            assert monotonic() < deadline
            app.run(frames=1)
            frames += 1
        app.handle(pg.event.Event(pg.VIDEORESIZE, w=800, h=600, size=(800, 600)))
        app.run(frames=3)
        assert app.screen.get_size() == (800, 600) and frames > 0 and not job.poll().done
        key(app, pg.K_ESCAPE)
        assert app.dialog is None
        assert job.close() and job.poll().cancelled
    finally:
        app.close()


def test_replaced_modal_cancels_an_abandoned_analysis(app):
    app.begin_export('sid')
    frame(app)
    job = app.dialog['job']
    app.confirm_quit()
    frame(app)
    assert app.dialog.get('quit') and job.cancelled
    key(app, pg.K_ESCAPE)
    assert app.running and app.dialog is None


def test_async_save_failure_restores_dialog_and_drops_pending_continuation(app, monkeypatch):
    def fail_save():
        raise OSError('Test native save denied')

    monkeypatch.setattr(app, 'save_project', fail_save)
    app.begin_export('sid')
    finish(app)
    ui.toggle(app, 0)
    ui.activate(app, 'save')
    assert app.dialog['busy']
    finish(app)
    assert not app.dialog['busy'] and app.dialog['result'] is not None
    assert 'native save denied' in app.dialog['error'] and app.after_save is None
