from copy import deepcopy
from pathlib import Path
import pygame as pg
import pytest

from sidpulse.app import App
from sidpulse.song.model import Song, example_song
from sidpulse.ui.keyboard import Command


def event(key, scan=0, mod=0, text="", up=False):
    return pg.event.Event(pg.KEYUP if up else pg.KEYDOWN, key=key, scancode=scan, mod=mod, unicode=text)


@pytest.fixture
def app():
    app = App(example_song(), audio=False)
    yield app
    app.close()


def test_pygame_edit_save_browser_reload(app, tmp_path):
    app.editor.song = Song()
    app.editor.saved = deepcopy(app.editor.song)
    app.handle(event(pg.K_z, 29, text="z"))
    app.handle(event(pg.K_z, 29, up=True))
    assert app.editor.song.patterns[0].rows[0][0].note == 48
    assert app.editor.row == 1
    app.file_dir = tmp_path
    app.handle(event(pg.K_F10))
    assert app.page == "files" and app.file_mode == "save"
    app.handle(event(pg.K_a, mod=pg.KMOD_CTRL))
    app.handle(pg.event.Event(pg.TEXTINPUT, text="test-song.sidpulse"))
    app.handle(event(pg.K_RETURN))
    assert app.path == tmp_path / "test-song.sidpulse"
    assert not app.editor.dirty
    app.handle(event(pg.K_x, 27, text="x"))
    assert app.editor.dirty
    app.handle(event(pg.K_F9))
    assert "discard" in app.dialog
    app.handle(event(pg.K_ESCAPE))
    assert app.editor.dirty
    app.open_project(app.path)
    assert app.editor.song.patterns[0].rows[1][0].note is None


def test_caps_lock_jazz_and_focus_loss_are_non_destructive(app):
    before = deepcopy(app.editor.song)
    app.handle(event(pg.K_z, 29, pg.KMOD_CAPS))
    assert app.held == {29}
    assert app.editor.song == before
    app.handle(pg.event.Event(pg.WINDOWFOCUSLOST))
    assert not app.held
    app.handle(event(pg.K_F4))
    app.handle(event(pg.K_q, 20))
    assert app.editor.song == before


def test_instrument_bank_and_properties_keyboard(app):
    app.handle(event(pg.K_F4))
    app.handle(event(pg.K_DOWN))
    assert app.editor.instrument == 2
    app.handle(event(pg.K_TAB))
    app.handle(event(pg.K_TAB))
    app.handle(event(pg.K_DOWN))  # waveform
    app.handle(event(pg.K_RIGHT))
    assert app.editor.song.instruments[2].waveform == 64
    app.handle(event(pg.K_BACKSPACE, mod=pg.KMOD_CTRL))
    assert app.editor.song.instruments[2].waveform == 32


@pytest.mark.parametrize("size,zoom", [((1280, 900), 1), ((1920, 1080), 1), ((923, 1042), 1),
                                      ((800, 600), .5), ((800, 600), 3), ((480, 360), 3), ((1280, 900), 3)])
def test_resize_zoom_preserve_song_and_cursor_visibility(app, size, zoom):
    before = deepcopy(app.editor.song)
    app.handle(pg.event.Event(pg.VIDEORESIZE, w=size[0], h=size[1]))
    app.zoom = zoom
    last_row=len(app.editor.pattern.rows)-1
    app.editor.voice, app.editor.column, app.editor.row = 2, 16, last_row
    app.renderer.render(app)
    hits = [rect for rect, action, data in app.renderer.hits if action == "cell" and data == (last_row, 2, 15)]
    assert len(hits) == 1
    assert app.screen.get_rect().contains(hits[0])
    assert hits[0].bottom <= (app.renderer.lines - 3) * app.renderer.rh
    assert app.editor.song == before


def test_all_function_pages_render(app, tmp_path):
    for page in ("pattern", "instrument", "samples", "orders", "settings", "help", "info"):
        app.change_page(page)
        app.renderer.render(app)
    app.file_dir = tmp_path
    app.browse("open")
    app.renderer.render(app)
    app.prompt_filename()
    app.renderer.render(app)


def test_invalid_open_keeps_current_song_and_path(app, tmp_path):
    app.path = tmp_path / "good.sidpulse"
    bad = tmp_path / "bad.sidpulse"
    bad.write_text("not valid JSON")
    before = deepcopy(app.editor.song)
    with pytest.raises(ValueError):
        app.open_project(bad)
    assert app.editor.song == before
    assert app.path == tmp_path / "good.sidpulse"


def test_modal_text_input_cannot_write_notes(app):
    before = deepcopy(app.editor.song)
    app.text_dialog("Value", "", lambda value: None)
    app.handle(event(pg.K_z, 29))
    app.handle(pg.event.Event(pg.TEXTINPUT, text="z"))
    assert app.dialog["text"] == "z"
    assert app.editor.song == before


def test_context_help_topic_menu_and_return(app):
    app.change_page("instrument")
    app.handle(event(pg.K_F1))
    assert app.page == "help" and app.help_topic == 2
    app.renderer.render(app)
    app.handle(event(pg.K_6, 35, text="6"))
    assert app.help_topic == 5
    app.handle(event(pg.K_ESCAPE))
    assert app.page == "instrument"


def test_disabled_menu_and_shortcuts_do_not_act(app):
    before = deepcopy(app.editor.song)
    app.open_menu("Settings Menu")
    from sidpulse.ui.menus import menu_items
    app.activate_menu(next(i for i,item in enumerate(menu_items('Settings Menu')) if item.value=='MIDI configuration'))
    assert app.menu_path and "not implemented" in app.editor.status
    app.menu_path.clear()
    app.handle(event(pg.K_F1, mod=pg.KMOD_SHIFT))  # MIDI shortcut remains inactive
    assert app.page == "pattern"
    assert app.editor.song == before
    app.handle(event(pg.K_F9, mod=pg.KMOD_SHIFT))
    assert app.dialog["title"] == "Song comments"


def test_waveform_buttons_reach_actual_instrument_setting(app):
    app.change_page("instrument")
    app.renderer.render(app)
    hit = next(rect for rect, action, value in app.renderer.hits if action == "waveform" and value == 16)
    app.handle(pg.event.Event(pg.MOUSEBUTTONDOWN, button=1, pos=hit.center))
    assert app.editor.song.instruments[1].waveform == 16


def test_helper_toggle_is_ui_only_and_persists_in_editor_metadata(app):
    before = deepcopy(app.editor.song)
    app.execute(Command('helper_toggle'))
    assert not app.helper_strip
    assert not app.metadata()['helper_strip']
    app.renderer.render(app)
    assert app.renderer.footer_rows == 2
    assert app.editor.song == before


def test_channel_mute_solo_mouse_and_schism_shortcuts_preserve_song(app):
    before = deepcopy(app.editor.song)
    app.handle(event(pg.K_F2, mod=pg.KMOD_ALT))
    assert app.muted == [False, True, False]
    app.editor.voice = 2
    app.handle(event(pg.K_F10, mod=pg.KMOD_ALT))
    assert app.solo_voice == 2 and app.monitor_mask() == (True, True, False)
    app.renderer.render(app)
    hit = next(rect for rect, action, value in app.renderer.hits if action == "solo" and value == 2)
    app.handle(pg.event.Event(pg.MOUSEBUTTONDOWN, button=1, pos=hit.center))
    assert app.solo_voice is None and app.monitor_mask() == (False, True, False)
    app.handle(event(pg.K_F9, mod=pg.KMOD_ALT))
    assert app.muted[2]
    app.change_page('info')
    app.handle(event(pg.K_q, scan=20, text='q'))
    assert not app.muted[2]
    assert app.editor.song == before and not app.editor.dirty


def test_effect_help_is_selectable_and_does_not_execute_effects(app):
    from sidpulse.ui.effects import lookup_effect
    before = deepcopy(app.editor.song)
    app.handle(event(pg.K_F1))
    app.handle(event(pg.K_9, scan=38, text='9'))
    assert app.help_topic == 8
    app.renderer.render(app)
    assert lookup_effect('S', 0x91)['status'] == 'not_applicable'
    assert lookup_effect('S', 0xB0)['code'] == 'SB0'
    assert lookup_effect('H', 0x24)['preview_implemented']
    assert app.editor.song == before
