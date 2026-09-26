"""Dropped projects must be checked and explicitly accepted before replacing work."""
from copy import deepcopy

import pygame as pg
import pytest

from sidpulse.app import App
from sidpulse.project.format import load, save
from sidpulse.song.model import example_song
from sidpulse.ui.dialogs import choices, focus


def key(app, value):
    app.handle(pg.event.Event(pg.KEYDOWN, key=value, scancode=0, mod=0, unicode=''))


def drop(app, path):
    app.handle(pg.event.Event(pg.DROPFILE, file=str(path)))


@pytest.fixture
def app():
    instance = App(example_song(), audio=False)
    yield instance
    instance.close()


@pytest.mark.parametrize('name,contents', [
    ('broken.sidpulse', b'{this is not JSON'),
    ('wrong.sidpulse', b'{"format":"SIDPULSE","format_version":10,"song":{}}'),
    ('wrong.txt', b'not a project'),
])
def test_invalid_drop_shows_error_and_preserves_project(app, tmp_path, name, contents):
    source = tmp_path / name
    source.write_bytes(contents)
    before = deepcopy(app.editor.song)
    app.path = tmp_path / 'original.sidpulse'
    drop(app, source)
    assert app.dialog['kind'] == 'notice'
    assert 'cannot be opened' in app.dialog['title']
    assert app.editor.song == before and app.path.name == 'original.sidpulse'


def test_valid_clean_drop_requires_open_confirmation(app, tmp_path):
    song = example_song()
    song.title = 'Dropped song'
    source = save(tmp_path / 'new.sidpulse', song)
    before = deepcopy(app.editor.song)
    drop(app, source)
    assert [label for label, _ in choices(app.dialog)] == ['Open project', 'Cancel']
    assert choices(app.dialog)[focus(app.dialog)][0] == 'Cancel'
    key(app, pg.K_RETURN)
    assert app.dialog is None and app.editor.song == before
    drop(app, source)
    key(app, pg.K_y)
    assert app.path == source and app.editor.song.title == 'Dropped song'


def test_dirty_drop_offers_save_open_and_cancel(app, tmp_path):
    source = save(tmp_path / 'new.sidpulse', example_song())
    app.editor.edit('Rename', [(('title',), 'Unsaved edits')])
    before = deepcopy(app.editor.song)
    app.path = tmp_path / 'working.sidpulse'
    drop(app, source)
    assert [label for label, _ in choices(app.dialog)] == [
        'Save & open', 'Open without saving', 'Cancel']
    assert choices(app.dialog)[focus(app.dialog)][0] == 'Cancel'
    key(app, pg.K_RETURN)
    assert app.editor.song == before and app.editor.dirty
    drop(app, source)
    key(app, pg.K_s)
    assert load(tmp_path / 'working.sidpulse')[0] == before
    assert app.path == source and not app.editor.dirty


def test_unnamed_save_first_and_cancel_browser_aborts_drop(app, tmp_path):
    source = save(tmp_path / 'new.sidpulse', example_song())
    app.editor.edit('Rename', [(('title',), 'Unsaved edits')])
    app.file_dir = tmp_path
    before = deepcopy(app.editor.song)
    drop(app, source)
    key(app, pg.K_s)
    assert app.page == 'files' and app.after_save is not None
    app.cancel_browser()
    assert app.after_save is None and app.editor.song == before
    drop(app, source)
    key(app, pg.K_s)
    app.file_name = 'saved-before-drop.sidpulse'
    app.submit_file()
    assert load(tmp_path / 'saved-before-drop.sidpulse')[0] == before
    assert app.path == source


def test_drop_rechecked_before_open_and_failed_save_does_not_later_open(app, tmp_path, monkeypatch):
    source = save(tmp_path / 'new.sidpulse', example_song())
    before = deepcopy(app.editor.song)
    drop(app, source)
    source.write_text('damaged after prompt')
    key(app, pg.K_y)
    assert app.dialog['kind'] == 'notice' and app.editor.song == before
    assert app.path is None
    key(app, pg.K_RETURN)

    source = save(source, example_song())
    app.path = tmp_path / 'working.sidpulse'
    app.editor.edit('Rename', [(('title',), 'Unsaved edits')])
    before = deepcopy(app.editor.song)
    from sidpulse import app as app_module
    monkeypatch.setattr(app_module, 'save', lambda *args: (_ for _ in ()).throw(OSError('disk full')))
    drop(app, source)
    key(app, pg.K_s)
    assert app.editor.song == before and app.path.name == 'working.sidpulse'
    assert app.after_save is None and 'disk full' in app.editor.status
