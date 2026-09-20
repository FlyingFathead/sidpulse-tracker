"""Channel remapping is an export operation; native channel semantics survive."""
from copy import deepcopy

import pygame as pg
import pytest

from sidpulse.export.pcm import compile_pcm, prepare_pcm
from sidpulse.export.psid import ExportError
from sidpulse.export.squeeze import SqueezeOptions
from sidpulse.song.model import Cell, ControlCell, Instrument
from test_pcm_media import pcm_song


def channel_song(voice):
    song=pcm_song(4005)
    song.instruments[2]=Instrument(waveform=32)
    # Includes inherited instrument numbers, note cuts and returning to SID.
    song.patterns[0].rows=[
        [Cell(), Cell(), Cell(48,1)],
        [Cell(), Cell(), Cell(53)],
        [Cell(), Cell(), Cell(-2)],
        [Cell(), Cell(), Cell(40,2)],
        [Cell(), Cell(), Cell(48,1)],
    ]
    song.patterns[0].controls={0:ControlCell(routing=7,volume=11),2:ControlCell(routing=0,volume=15)}
    for row in song.patterns[0].rows:
        row[voice],row[2]=row[2],row[voice]
    return song


def tick_states(prepared):
    registers=[0]*25
    result=[]
    for period,idle,events in prepared.records:
        samples=[]
        for reg,value in events:
            if reg<25:registers[reg]=value
            elif reg==30:samples.append(b''.join(value))
            elif reg==31:samples.append('cut')
        result.append((period,idle,tuple(registers),samples))
    return result


@pytest.mark.parametrize('voice',[0,1,2])
def test_remapped_export_matches_ch3_playback_with_instrument_memory(voice):
    song=channel_song(voice)
    before=deepcopy(song)
    expected=prepare_pcm(channel_song(2))
    prepared=prepare_pcm(song)
    assert tick_states(prepared)==tick_states(expected)
    result=compile_pcm(song,kind='prg',squeeze=SqueezeOptions(version=1))
    assert result.squeeze_report.pcm_source_channel==voice+1
    assert f'TRACKER CH{voice+1}'.encode() in result.data
    assert song==before
    if voice!=2:
        with pytest.raises(ExportError,match='Enable Auto-remap PCM to CH3'):
            compile_pcm(song,squeeze=SqueezeOptions(pcm_auto_remap=False))


def test_pcm_on_multiple_channels_is_never_silently_discarded():
    song=channel_song(0)
    song.patterns[0].rows[-1]=[Cell(),Cell(48,1),Cell()]
    with pytest.raises(ExportError,match='more than one tracker channel'):
        compile_pcm(song)


@pytest.mark.parametrize('size',[(640,480),(960,1080),(1280,900)])
def test_export_remap_warning_and_persisted_mouse_keyboard_option(size):
    from sidpulse.app import App
    from sidpulse.preferences import save_preferences, load_squeeze_options
    from sidpulse.ui import export_squeezer as ui
    from export_gui_helpers import finish_export_analysis
    save_preferences({'export_compare_squeezers':False})
    app=App(channel_song(0),audio=False,size=size)
    try:
        before=deepcopy(app.editor.song)
        ui.open_dialog(app,'prg')
        finish_export_analysis(app)
        assert app.dialog['pcm_source_channel']==1
        app.renderer.render(app)
        assert app.screen.get_rect().contains(app.dialog['pcm_warning_rect'])
        rect=next(r for r,a,v in app.renderer.hits if a=='squeeze_pcm_remap')
        app.handle(pg.event.Event(pg.MOUSEBUTTONDOWN,button=1,pos=rect.center))
        assert not app.dialog['options'].pcm_auto_remap
        ui.analyze(app)
        with pytest.raises(AssertionError,match='Enable Auto-remap'):
            finish_export_analysis(app)
        assert app.dialog['result'] is None and 'Auto-remap' in app.dialog['error']
        app.renderer.render(app)
        assert 'pcm_warning_rect' in app.dialog
        app.dialog['focus']=21
        app.handle(pg.event.Event(pg.KEYDOWN,key=pg.K_SPACE,mod=0))
        assert app.dialog['options'].pcm_auto_remap
        ui.analyze(app)
        finish_export_analysis(app)
        app.prompt_export=lambda *args:None
        ui.activate(app,'export')
        assert load_squeeze_options().pcm_auto_remap and app.editor.song==before
    finally:app.close()
