import pygame as pg
from sidpulse.ui import registry
from sidpulse.ui.keyboard import dispatch
from sidpulse.ui.menus import menu_items


def test_registry_disable_gates_actual_keyboard_and_help(monkeypatch):
    entry = next(e for e in registry.COMMANDS if e['id'] == 'pattern.copy')
    event = pg.event.Event(pg.KEYDOWN, key=pg.K_c, scancode=6, mod=pg.KMOD_ALT, unicode='c')
    assert dispatch(event).name == 'copy'
    monkeypatch.setitem(entry, 'keybind_in_use', False)
    assert dispatch(event).name == 'pending'
    assert not registry.available(entry, keyboard=True)
    monkeypatch.setitem(entry, 'visible_in_help', False)
    assert entry not in registry.help_entries('pattern')


def test_menu_visibility_and_execution_follow_registry(monkeypatch):
    entry = next(e for e in registry.COMMANDS if e['id'] == 'future.psid')
    item = next(i for i in menu_items('File Menu') if i.command == 'export')
    assert item.enabled
    monkeypatch.setitem(entry, 'visible_in_menu', False)
    assert all(i.command != 'export' for i in menu_items('File Menu'))


def test_transport_bindings_now_route_to_correct_actions():
    for key in (pg.K_F5, pg.K_F6, pg.K_F7):
        event = pg.event.Event(pg.KEYDOWN, key=key, scancode=0, mod=0, unicode='')
        assert dispatch(event).name == 'play'
    event = pg.event.Event(pg.KEYDOWN, key=pg.K_F8, scancode=0, mod=0, unicode='')
    assert dispatch(event).name == 'panic'


def test_stereo_is_inapplicable_only_in_correct_context():
    event = pg.event.Event(pg.KEYDOWN, key=pg.K_s, scancode=22, mod=pg.KMOD_ALT, unicode='s')
    assert dispatch(event, 'info').name == 'pending'
    assert dispatch(event, 'pattern').name == 'block_instrument'


def test_registry_flags_and_ids_are_valid():
    entries = registry.read_registry()
    assert len(entries) >= 200
    assert len({e['id'] for e in entries}) == len(entries)
    for entry in entries:
        assert entry['target']
        if not entry['implemented'] or not entry['applicable']:
            assert not entry['keybind_in_use']
