from copy import deepcopy
from dataclasses import replace

import pygame as pg
import pytest

from sidpulse.app import App
from sidpulse.project.format import save, load
from sidpulse.song.model import Cell, Song
from test_graphical_instruments import click, key
from test_pcm_media import pcm_song


@pytest.mark.parametrize('size',[(640,480),(960,1080),(1280,900)])
def test_header_shortcuts_focus_title_and_displayed_instrument(size,monkeypatch):
    app=App(audio=False,size=size)
    try:
        before=deepcopy(app.editor.song)
        app.change_page('settings');app.renderer.render(app)
        # Even clicking from F12 with a manually scrolled view returns to title.
        app.renderer.scrollbars.states['settings']['scroll']=20
        click(app,'song_title_settings')
        app.renderer.render(app)
        assert app.page=='settings' and app.property_index==0
        assert app.renderer.scrollbars.states['settings']['scroll']==0
        assert any(a=='setting_edit' and v==0 for r,a,v in app.renderer.hits)
        from sidpulse.ui import renderer
        labels=[];original=app.renderer.text
        def text(x,y,label,color=None,*args,**kw):
            labels.append((label,color))
            return original(x,y,label,color,*args,**kw) if color is not None else original(x,y,label,*args,**kw)
        monkeypatch.setattr(app.renderer,'text',text)
        app.renderer.render(app)
        assert ('Song title',renderer.CREAM) in labels
        app.change_page('pattern');app.editor.instrument=3;app.instrument_slot=1
        click(app,'header_instrument',3)
        assert app.page=='instrument' and app.instrument_slot==app.editor.instrument==3
        assert app.editor.song==before and not app.editor.history.undo_stack
    finally:app.close()


@pytest.mark.parametrize('size',[(640,480),(960,1080),(1280,900)])
def test_f4_copy_paste_warns_for_used_slot_and_is_undoable(size,tmp_path):
    app=App(audio=False,size=size)
    try:
        app.editor.song.patterns[0].rows[0][1]=Cell(36,2)
        app.change_page('instrument')
        before=deepcopy(app.editor.song)
        for action in ('copy_instrument','paste_instrument'):
            app.renderer.render(app)
            rect=next(r for r,a,v in app.renderer.hits if a==action)
            assert app.screen.get_rect().contains(rect)
        click(app,'copy_instrument')
        assert app.editor.song==before and app.editor.clipboard is None
        app.select_instrument_slot(number=2)
        click(app,'paste_instrument')
        assert 'used by 1 pattern references' in app.dialog['message']
        key(app,pg.K_RETURN)  # defaults to Cancel
        assert app.editor.song==before
        click(app,'paste_instrument');click(app,'confirm_instrument',True)
        assert app.editor.song.instruments[2]==before.instruments[1]
        assert app.editor.song.patterns==before.patterns
        assert load(save(tmp_path/'copy.sidpulse',app.editor.song))[0]==app.editor.song
        app.editor.history.undo(app.editor.song);assert app.editor.song==before
        app.editor.history.redo(app.editor.song)
        app.editor.song.instruments[2].arpeggio.append(12)
        assert not app.editor.song.instruments[1].arpeggio
        assert not app.instrument_clipboard[0].arpeggio
    finally:app.close()


def test_pcm_clipboard_across_projects_preserves_samples_without_overwriting(tmp_path):
    song=pcm_song();song.instruments[1].arpeggio=[0,7];song.instruments[1].pulse_depth=42
    app=App(song,audio=False)
    try:
        app.change_page('instrument');click(app,'copy_instrument')
        target=pcm_song();target.samples['1']['name']='Existing sample'
        path=save(tmp_path/'other.sidpulse',target);app.open_project(path)
        app.dialog=None;app.change_page('instrument');app.select_instrument_slot(number=8)
        before=deepcopy(app.editor.song)
        app.instrument_focus='buttons'
        app.instrument_button=app.instrument_buttons().index(('paste_instrument',None))
        key(app,pg.K_RETURN)
        assert app.dialog is None and app.instrument_slot==8
        assert app.editor.song.instruments[8]==replace(song.instruments[1],sample_slot=2)
        assert app.editor.song.samples['1']==before.samples['1']
        assert app.editor.song.samples['2']==song.samples['1']
        assert app.instrument_tab=='sample'
        assert len(app.editor.history.undo_stack)==1
        app.editor.history.undo(app.editor.song);assert app.editor.song==before
    finally:app.close()


def test_empty_clipboard_and_empty_copy_leave_document_untouched():
    app=App(Song(),audio=False)
    try:
        app.change_page('instrument');before=deepcopy(app.editor.song)
        click(app,'paste_instrument')
        assert 'empty' in app.clipboard_notice[0]
        app.select_instrument_slot(number=99);click(app,'copy_instrument')
        assert app.instrument_clipboard is None
        assert app.editor.song==before and not app.editor.history.undo_stack
    finally:app.close()
