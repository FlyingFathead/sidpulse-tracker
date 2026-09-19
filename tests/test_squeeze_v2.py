"""Version selection, lossless phrase joining and PRG startup credits."""
from dataclasses import replace
import random
import pytest
import pygame as pg
from sidpulse.export.squeeze import SqueezeOptions, squeezer_version_label
from sidpulse.export.stream_packer import pack_streams,verify_streams
from sidpulse.export.squeeze_v2 import optimize_bank
from sidpulse.export.psid import compile_song
from sidpulse.export.prg import compile_prg,stamp_export
from sidpulse.preferences import load_squeeze_options,save_squeeze_options,save_preferences
from sidpulse.song.model import Song,example_song
from sidpulse.song.welcome import welcome_song
from sidpulse.app import App
from sidpulse import __version__
from export_gui_helpers import finish_export_analysis
from test_prg import machine,step_until


@pytest.mark.parametrize('seed',range(6))
def test_overlaps_and_full_match_lookup_preserve_random_and_repeated_streams(seed):
    rng=random.Random(seed)
    phrases=[rng.randbytes(27) for _ in range(8)]
    streams=tuple(b''.join(rng.choice(phrases)[rng.randrange(6):] for _ in range(35))
                  for _ in range(4))+(b'',bytes(range(256))*4,b'ABCD'*600)
    packed=optimize_bank(streams,pack_streams(streams,16))
    verify_streams(packed,streams)
    assert packed==optimize_bank(streams,pack_streams(streams,16))


@pytest.mark.parametrize('factory',[Song,example_song,welcome_song])
def test_v2_cannot_choose_a_larger_export_than_v1(factory):
    song=factory()
    original=compile_song(song,squeeze=SqueezeOptions(version=1))
    new=compile_song(song,squeeze=SqueezeOptions(version=2))
    assert len(new.data)<=len(original.data)
    assert new.ticks==original.ticks and new.seconds==original.seconds
    assert original.squeeze_report.squeezer_version==1 and new.squeeze_report.squeezer_version==2


@pytest.mark.parametrize('value',[True,False,0,3,'1',None])
def test_invalid_squeezer_version_is_rejected_but_saved_unknown_defaults_safely(value):
    with pytest.raises(ValueError):SqueezeOptions(version=value)
    save_preferences({'export_squeeze':{'version':value}})
    assert load_squeeze_options().version==202


def test_explicit_original_selection_survives_preferences():
    save_squeeze_options(SqueezeOptions(version=1))
    assert load_squeeze_options().version==1


@pytest.mark.parametrize('version',[1,2,201,202])
@pytest.mark.parametrize('compact',[False,True])
def test_prg_prints_actual_versions_and_returns_safely_on_wrong_clock(version,compact):
    # streams=False exercises the legacy wrapper while still using cleanup.
    result=compile_prg(Song(),squeeze=SqueezeOptions(version=version,streams=compact))
    cpu,mem=machine(result.data,pal=False);calls=[]
    step_until(cpu,lambda:cpu.pc==0x0200,calls)
    display=''.join(chr(a) for pc,a in calls if pc==0xffd2)
    # Credits are printed when music starts; mismatch exits before that point.
    assert 'DIFFERENT VIDEO CLOCK' in display and not mem.events
    cpu,mem=machine(result.data,pal=True);calls=[]
    step_until(cpu,lambda:bool(mem.events),calls)
    display=''.join(chr(a) for pc,a in calls if pc==0xffd2)
    assert f'EXPORTED FROM V{__version__}' in display
    assert f'SQUEEZER VER: {squeezer_version_label(version)}' in display


def click(app,action,value=None):
    app.renderer.render(app)
    rect=next(r for r,a,v in app.renderer.hits if a==action and (value is None or v==value))
    app.handle(pg.event.Event(pg.MOUSEBUTTONDOWN,button=1,pos=rect.center))


@pytest.mark.parametrize('size',[(480,360),(960,1080)])
def test_version_dropdown_reuses_comparison_and_is_hidden_with_squeeze_off(size):
    app=App(audio=False,size=size)
    try:
        app.begin_export();finish_export_analysis(app)
        app.dialog['focus']=9;app.dialog['ensure_focus']=True
        click(app,'squeeze_version')
        app.renderer.render(app)
        assert all(app.screen.get_rect().contains(r) for r,a,_ in app.renderer.hits if a=='squeeze_version_pick')
        assert [v for _,a,v in app.renderer.hits if a=='squeeze_version_pick']==[202,201,2,1]
        click(app,'squeeze_version_pick',1)
        assert app.dialog['options'].version==1 and app.dialog['result'].squeeze_report.squeezer_version==1
        assert app.dialog['source']==app.editor.song and not app.dialog['version_open']
        app.handle(pg.event.Event(pg.KEYDOWN,key=pg.K_RETURN,mod=0,unicode=''))
        assert app.dialog['version_open']
        app.handle(pg.event.Event(pg.KEYDOWN,key=pg.K_ESCAPE,mod=0,unicode=''))
        assert app.dialog is not None and not app.dialog['version_open']
        app.handle(pg.event.Event(pg.KEYDOWN,key=pg.K_RETURN,mod=0,unicode=''))
        app.handle(pg.event.Event(pg.KEYDOWN,key=pg.K_DOWN,mod=0,unicode=''))
        assert app.dialog['version_choice']==202
        app.handle(pg.event.Event(pg.KEYDOWN,key=pg.K_UP,mod=0,unicode=''))
        assert app.dialog['version_choice']==1
        app.handle(pg.event.Event(pg.KEYDOWN,key=pg.K_UP,mod=0,unicode=''))
        app.handle(pg.event.Event(pg.KEYDOWN,key=pg.K_RETURN,mod=0,unicode=''))
        assert app.dialog['options'].version==2 and not app.dialog['version_open']
        from sidpulse.ui.export_squeezer import toggle
        toggle(app,0);app.renderer.render(app)
        assert not any(a in ('squeeze_version','squeeze_version_pick') for _,a,_ in app.renderer.hits)
    finally:app.close()
