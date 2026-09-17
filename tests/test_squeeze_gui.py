"""Export dialog: opt-out, keyboard/mouse, cancellation, scope and small windows."""
from export_gui_helpers import finish_export_analysis
from copy import deepcopy
from dataclasses import replace
import pytest
pg = pytest.importorskip('pygame')
from sidpulse.app import App
from sidpulse.export.squeeze import SqueezeOptions
from sidpulse.preferences import load_squeeze_options
from sidpulse.ui.export_squeezer import toggle, activate, open_dialog


def key(app, value, mod=0):
    app.handle(pg.event.Event(pg.KEYDOWN, key=value, mod=mod, unicode=''))


@pytest.mark.parametrize('kind', ['sid', 'prg'])
def test_default_checks_and_cancel_never_touch_source_or_preferences(kind):
    app = App(audio=False)
    try:
        before = deepcopy(app.editor.song)
        app.begin_export(kind)
        finish_export_analysis(app)
        assert app.dialog['options'] == SqueezeOptions()
        assert app.dialog['result'].squeeze_report.saved_bytes > 0
        toggle(app, 0)
        assert not app.dialog['options'].enabled and app.dialog['result'] is None
        toggle(app, 1)
        assert app.dialog['options'].patterns  # disabled with master off
        key(app, pg.K_ESCAPE)
        assert app.dialog is None and app.editor.song == before
        assert load_squeeze_options() == SqueezeOptions()
    finally: app.close()


@pytest.mark.parametrize('kind', ['sid', 'prg'])
def test_export_only_uses_selected_options_and_preserves_unsaved_state(kind):
    app = App(audio=False)
    try:
        before = deepcopy(app.editor.song)
        app.editor.saved = None
        app.begin_export(kind)
        finish_export_analysis(app)
        toggle(app, 0)
        key(app, pg.K_e)
        finish_export_analysis(app)
        assert app.dialog is None and app.page == 'files' and app.file_mode == kind
        assert not app.browser.export_result.squeeze_report.enabled
        assert not load_squeeze_options().enabled
        assert app.editor.song == before and app.editor.saved is None and app.path is None
    finally: app.close()


def test_save_continuation_retains_squeezed_export_and_cancel_is_default(monkeypatch):
    app = App(audio=False)
    try:
        called = []
        app.begin_export('sid')
        key(app, pg.K_RETURN)
        assert app.dialog is None  # default Cancel, not accidental export
        app.begin_export('sid')
        finish_export_analysis(app)
        monkeypatch.setattr(app, 'save_project', lambda: called.append('native-save'))
        key(app, pg.K_s)
        assert called == ['native-save'] and callable(app.after_save)
        app.after_save()
        assert app.page == 'files' and app.browser.export_result.squeeze_report.enabled
    finally: app.close()


@pytest.mark.parametrize('size', [(360, 360), (480, 360), (1280, 900), (1920, 1080)])
@pytest.mark.parametrize('zoom', [.5, 1., 3.])
def test_dialog_controls_remain_inside_viewport_and_keyboard_scrolls(size, zoom):
    app = App(audio=False, size=size, zoom=zoom)
    try:
        app.begin_export('sid')
        finish_export_analysis(app)
        for index in range(5):
            app.dialog['focus'] = index
            app.dialog['ensure_focus'] = True
            app.renderer.render(app)
            assert all(app.screen.get_rect().contains(rect) for rect, _, _ in app.renderer.hits)
            assert len([rect for rect, action, _ in app.renderer.hits if action == 'squeeze_button']) == 4
            rect = next(rect for rect, action, value in app.renderer.hits
                        if action == 'squeeze_option' and value == index)
            before = app.dialog['options']
            app.handle(pg.event.Event(pg.MOUSEBUTTONDOWN, button=1, pos=rect.center))
            assert app.dialog['options'] != before
            toggle(app, index)  # restore all checks for next case
    finally: app.close()


def test_dialog_rejects_non_export_target():
    app = App(audio=False)
    try:
        with pytest.raises(ValueError): open_dialog(app, 'sidpulse')
        assert app.dialog is None
    finally: app.close()
