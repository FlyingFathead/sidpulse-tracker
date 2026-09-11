"""Playback deadlock reproductions, complete piano input, and F11 order entry."""
from copy import deepcopy
import os
from pathlib import Path
import subprocess
import sys
import textwrap
import pygame as pg
import pytest
from sidpulse.app import App
from sidpulse.song.model import Song, Pattern, example_song
from sidpulse.ui.keyboard import NOTE_SCANCODES, Command


def key(app, key, text='', scan=0, mod=0, up=False):
    app.handle(pg.event.Event(pg.KEYUP if up else pg.KEYDOWN,key=key,unicode=text,scancode=scan,mod=mod))


def click(app, action, value=None):
    app.renderer.render(app)
    rect=next(r for r,a,v in app.renderer.hits if a==action and v==value)
    app.handle(pg.event.Event(pg.MOUSEBUTTONDOWN,button=1,pos=rect.center))
    app.handle(pg.event.Event(pg.MOUSEBUTTONUP,button=1,pos=rect.center))


@pytest.fixture
def app():
    instance=App(example_song(),audio=False)
    yield instance
    instance.close()


@pytest.mark.parametrize('column',[0,1])
def test_whole_piano_range_in_both_note_subcolumns(app,column):
    for voice in range(3):
        for scan,offset in NOTE_SCANCODES.items():
            app.editor.column=column;app.editor.voice=voice;app.editor.row=0
            key(app,pg.K_b,'b',scan)
            assert app.editor.pattern.rows[0][voice].note==app.editor.octave*12+offset
            key(app,pg.K_b,'b',scan,up=True)
            assert not app.dialog


def test_caps_lock_piano_from_every_voice_field_preserves_song(app,monkeypatch):
    calls=[];monkeypatch.setattr(app.audio,'send',lambda *args:calls.append(args))
    before=deepcopy(app.editor.song)
    for column in range(9):
        app.editor.column=column
        for scan in NOTE_SCANCODES:
            key(app,pg.K_b,'b',scan,pg.KMOD_CAPS)
            key(app,pg.K_b,'b',scan,pg.KMOD_CAPS,True)
    assert len([c for c in calls if c[0]=='on'])==9*len(NOTE_SCANCODES)
    assert app.editor.song==before and not app.dialog


def test_f11_three_digits_auto_advance_delete_and_undo(app):
    key(app,pg.K_F11)
    original=deepcopy(app.editor.song)
    click(app,'order_value',1)
    for ch in '123004007':key(app,ord(ch),ch)
    assert app.editor.song.orders[1:4]==[123,4,7]
    assert app.order_entry_index==4 and app.dialog is None
    # Deleting immediately after auto-advance must remove row 4, not row 3.
    before=list(app.editor.song.orders);key(app,pg.K_DELETE)
    assert app.editor.song.orders==before[:4]+before[5:]
    app.execute(Command("undo"));assert app.editor.song.orders==before
    assert 123 in app.editor.song.patterns
    key(app,pg.K_F11);click(app,'order_value',2)
    key(app,pg.K_9,'9');key(app,pg.K_ESCAPE)
    assert app.editor.song.orders==before and not app.menu_path
    assert original.patterns[4]==app.editor.song.patterns[4]


def test_f11_append_empty_row_and_invalid_number(app):
    key(app,pg.K_F11);n=len(app.editor.song.orders)
    click(app,'order_value',n)
    for ch in '042003':key(app,ord(ch),ch)
    assert app.editor.song.orders[-2:]==[42,3] and app.order_entry_index==n+2
    for ch in '999':key(app,ord(ch),ch)
    assert len(app.editor.song.orders)==n+2 and '0..255' in app.editor.status
    key(app,pg.K_ESCAPE);assert not app.menu_path


def test_f11_bank_shows_unused_patterns_and_opens_in_f2(app):
    app.editor.song.patterns[255]=Pattern(name='Unused bridge')
    key(app,pg.K_F11);key(app,pg.K_TAB);key(app,pg.K_END)
    assert app.bank_pattern==255
    before=deepcopy(app.editor.song)
    app.renderer.render(app)
    assert any(a=='bank_pattern' and v==255 for _,a,v in app.renderer.hits)
    key(app,pg.K_RETURN)
    assert app.page=='pattern' and app.editor.pattern_id==255 and app.editor.song==before


@pytest.mark.parametrize('size',[(480,360),(980,780),(1440,1050)])
def test_f11_and_autosave_controls_fit(app,size):
    app.handle(pg.event.Event(pg.VIDEORESIZE,w=size[0],h=size[1],size=size))
    key(app,pg.K_F11);app.renderer.render(app)
    assert all(app.screen.get_rect().contains(r) for r,a,_ in app.renderer.hits if a in ('order_value','bank_open','bank_pattern'))
    from sidpulse.ui.autosave_settings import open_dialog
    open_dialog(app);app.renderer.render(app)
    rects=[r for r,a,_ in app.renderer.hits if a=='autosave_control']
    assert len(rects)==6 and all(app.screen.get_rect().contains(r) for r in rects)
    assert not any(a.colliderect(b) for i,a in enumerate(rects) for b in rects[i+1:])


def child(code,timeout=15):
    result=subprocess.run([sys.executable,'-c',textwrap.dedent(code)],cwd=Path(__file__).resolve().parents[1],
                          env=os.environ.copy(),capture_output=True,text=True,timeout=timeout)
    assert result.returncode==0,result.stdout+result.stderr


def test_pause_and_close_with_python_callback_in_flight():
    # The old pygame pause deadlocks here: SDL waits for a callback needing GIL.
    child('''
        import time,threading
        from pygame._sdl2 import AudioDevice,AUDIO_S16,init_subsystem,INIT_AUDIO
        from sidpulse.audio.device import pause_device,close_device
        init_subsystem(INIT_AUDIO)
        for action in ('pause','close'):
            entered=threading.Event()
            def callback(device,buffer):
                entered.set();time.sleep(.12)
                memoryview(buffer).cast('B')[:]=bytes(len(buffer))
            device=AudioDevice(None,False,48000,AUDIO_S16,1,1024,0,callback)
            pause_device(device,False)
            assert entered.wait(3)
            if action=='pause': pause_device(device,True)
            close_device(device)
    ''')


def test_three_notes_f5_and_repeated_restart_do_not_freeze():
    child('''
        import time,pygame as pg
        from sidpulse.app import App
        from sidpulse.song.model import Song
        app=App(Song(),audio=True)
        app.restart_on_f5=True
        def wait(test):
            end=time.monotonic()+4
            while not test():
                assert time.monotonic()<end,(app.audio.error,app.audio.playback)
                time.sleep(.002)
        def key(k,scan=0,up=False):
            app.handle(pg.event.Event(pg.KEYUP if up else pg.KEYDOWN,key=k,scancode=scan,mod=0,unicode=pg.key.name(k)))
        try:
            wait(lambda:app.audio.ready or app.audio.error)
            assert not app.audio.error
            for n in range(15):
                key(pg.K_F2);app.editor.row=0;app.editor.voice=n%3
                for k,scan in ((pg.K_z,29),(pg.K_2,31),(pg.K_p,19)):
                    key(k,scan);key(k,scan,True)
                app.sync_audio()
                if n: wait(lambda:app.audio.playback.frames>=7000)
                key(pg.K_F5)
                wait(lambda:app.audio.playback.status=='playing' and app.audio.playback.frames<5000)
                app.renderer.render(app)
                assert not app.audio.error
        finally:app.close()
    ''',timeout=25)


def test_switch_two_sparse_patterns_while_playing_and_restarting():
    child('''
        import time,pygame as pg
        from sidpulse.app import App
        from sidpulse.song.model import Song,Pattern,Cell
        song=Song();song.patterns[1]=Pattern(rows=[[Cell() for _ in range(3)] for _ in range(16)])
        song.orders=[0,1]
        for pid,note in ((0,48),(1,55)):
            song.patterns[pid].rows[0][0]=Cell(note,1)
            song.patterns[pid].rows[3][2]=Cell(note+7,1)
        app=App(song,audio=True)
        app.restart_on_f5=True
        def key(k):app.handle(pg.event.Event(pg.KEYDOWN,key=k,scancode=0,mod=0,unicode=''))
        try:
            end=time.monotonic()+4
            while not app.audio.ready:
                assert time.monotonic()<end and not app.audio.error
                time.sleep(.002)
            for i in range(120):
                key(pg.K_F2)
                key(pg.K_KP_PLUS if i%2==0 else pg.K_KP_MINUS)
                assert app.editor.pattern_id==(1 if i%2==0 else 0)
                if i%4==0:key(pg.K_F5)
                elif i%4==2:key(pg.K_F6)
                if i%7==0:
                    key(pg.K_F2);app.editor.enter_note(48+i%24)
                app.sync_audio();app.renderer.render(app);time.sleep(.006)
                assert not app.audio.error
        finally:app.close()
    ''',timeout=25)
