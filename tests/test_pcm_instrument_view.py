from copy import deepcopy

import pygame as pg
import pytest

from sidpulse.app import App
from sidpulse.project.format import save,load
from sidpulse.ui.instruments import PCM_FIELDS
from test_pcm_media import pcm_song


@pytest.mark.parametrize('size',[(640,480),(960,1080),(1280,900)])
def test_sample_mapping_hides_sid_controls_and_unmap_restores_saved_settings(size,tmp_path):
    song=pcm_song()
    song.instruments[1].wave_sequence=[128,64]
    song.instruments[1].pulse_depth=33
    app=App(song,audio=False,size=size)
    try:
        app.change_page('instrument')
        before=deepcopy(app.editor.song)
        for tab in ('general','adsr','sample','motion'):
            app.choose_instrument_tab(tab)
            app.renderer.render(app)
            assert app.instrument_tab in ('sample','motion')
            hits=app.renderer.hits
            assert not any(a in ('waveform','pulse_record_arm') for r,a,v in hits)
            assert all(v in PCM_FIELDS for r,a,v in hits if a in ('property','edit_instrument_field'))
            assert not any(a=='toggle_program' and v in ('pulse','wave_sequence') for r,a,v in hits)
            assert all(v in ('sample','motion','roll') for r,a,v in hits if a=='instrument_tab')
        app.choose_instrument_tab('motion')
        app.property_index=10
        app.page_key(pg.event.Event(pg.KEYDOWN,key=pg.K_DOWN,mod=0))
        assert app.property_index==12
        app.property_index=13
        app.change_property(1)
        assert app.editor.song==before
        app.toggle_instrument_program('wave_sequence')
        assert app.editor.song==before
        assert load(save(tmp_path/'mapped.sidpulse',app.editor.song))[0]==before
        app.choose_instrument_tab('sample')
        app.renderer.render(app)
        rect=next(r for r,a,v in app.renderer.hits if a=='pcm_setting' and v=='sample_override')
        assert app.screen.get_rect().contains(rect)
        app.handle(pg.event.Event(pg.MOUSEBUTTONDOWN,button=1,pos=rect.center))
        assert not app.editor.song.instruments[1].sample_override
        assert app.instrument_tab=='general'
        expected=deepcopy(before);expected.instruments[1].sample_override=False
        assert app.editor.song==expected
        app.renderer.render(app)
        assert any(a=='waveform' for r,a,v in app.renderer.hits)
        app.editor.history.undo(app.editor.song)
        app.renderer.render(app)
        assert app.editor.song==before and app.instrument_tab=='sample'
        assert not any(a=='waveform' for r,a,v in app.renderer.hits)
    finally:app.close()
