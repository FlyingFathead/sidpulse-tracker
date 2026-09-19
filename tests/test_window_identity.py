import pygame as pg
from sidpulse.app import App
from sidpulse.ui import window_identity


def test_icon_is_loaded_before_window_creation_and_not_on_each_frame(monkeypatch):
    events=[]
    icon=pg.display.set_icon
    mode=pg.display.set_mode
    def set_icon(surface):
        assert surface.get_size()==(128,128)
        assert len({surface.get_at((x,y))[:3] for x in range(128) for y in range(128)})>5
        events.append('icon');icon(surface)
    def set_mode(*args,**kwargs):
        events.append('window');return mode(*args,**kwargs)
    monkeypatch.setattr(pg.display,'set_icon',set_icon)
    monkeypatch.setattr(pg.display,'set_mode',set_mode)
    app=App(audio=False)
    try:
        for _ in range(3):app.renderer.render(app)
        assert events==['icon','window']
    finally:app.close()


def test_windows_identity_is_set_before_ui_and_failure_is_nonfatal(monkeypatch):
    import ctypes
    from types import SimpleNamespace
    calls=[]
    class Identify:
        def __call__(self,value):calls.append(value);return -1
    monkeypatch.setattr(window_identity.sys,'platform','win32')
    monkeypatch.setattr(ctypes,'windll',SimpleNamespace(shell32=SimpleNamespace(SetCurrentProcessExplicitAppUserModelID=Identify())),raising=False)
    window_identity.prepare()
    assert calls==[window_identity.APP_ID]
