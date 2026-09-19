import pygame as pg
import pytest
from sidpulse.app import App
from sidpulse.ui.keyboard import Command
from sidpulse.preferences import load_center_selection, save_preferences


@pytest.mark.parametrize('page,field,action',[('instrument','instrument_slot','choose_instrument'),('samples','sample_index','choose_sample')])
def test_bank_selection_centers_then_clamps_at_both_ends(page,field,action):
    app=App(audio=False,size=(960,1080))
    try:
        app.change_page(page)
        for selection in (1,50,99):
            setattr(app,field,selection);app.renderer.render(app)
            entries=[(r,v) for r,a,v in app.renderer.hits if a==action]
            values=[v for _,v in entries]
            assert selection in values
            if selection==1:assert values[0]==1
            elif selection==99:assert values[-1]==99
            else:assert values.index(selection)==len(values)//2
        app.execute(Command('center'));assert not load_center_selection()
        setattr(app,field,50);app.renderer.render(app)
        values=[v for _,a,v in app.renderer.hits if a==action]
        assert values.index(50)==len(values)//2
    finally:app.close()


@pytest.mark.parametrize('page,field,action',[
    ('instrument','instrument_slot','choose_instrument'),
    ('samples','sample_index','choose_sample'),
])
@pytest.mark.parametrize('size',[(960,1080),(1280,900)])
def test_every_bank_row_scrolls_smoothly_with_pattern_centering_disabled(page,field,action,size):
    save_preferences({'center_selection':False})
    app=App(audio=False,size=size)
    try:
        app.change_page(page)
        assert getattr(app,field)==1 and not app.editor.centered
        previous_start=None
        for key in (pg.K_DOWN,pg.K_UP):
            selections=range(1,100) if key==pg.K_DOWN else range(99,0,-1)
            for selected in selections:
                assert getattr(app,field)==selected
                app.renderer.render(app)
                visible=[v for _,a,v in app.renderer.hits if a==action]
                middle=len(visible)//2
                if selected<=middle+1:
                    assert visible[0]==1
                    assert visible.index(selected)==selected-1
                elif selected>=100-len(visible)+middle:
                    assert visible[-1]==99
                else:
                    assert visible.index(selected)==middle
                if previous_start is not None:
                    assert abs(visible[0]-previous_start)<=1
                previous_start=visible[0]
                if selected!=(99 if key==pg.K_DOWN else 1):
                    app.handle(pg.event.Event(pg.KEYDOWN,key=key,mod=0,unicode='',scancode=0))
        assert not app.editor.dirty and not app.editor.history.undo_stack
    finally:app.close()


@pytest.mark.parametrize('page,field,selection',[
    ('instrument','instrument_slot',50),('samples','sample_index',50),
])
def test_bank_selection_survives_page_round_trip_including_empty_instrument_slots(page,field,selection):
    app=App(audio=False,size=(960,1080))
    try:
        app.change_page(page)
        if page=='instrument':app.select_instrument_slot(number=selection)
        else:app.sample_index=selection
        for other in ('pattern','info','samples' if page=='instrument' else 'instrument'):
            app.change_page(other);app.change_page(page)
            assert getattr(app,field)==selection
        assert not app.editor.dirty
    finally:app.close()


def test_new_and_loaded_songs_start_banks_at_one_without_rewriting_saved_instrument_metadata(tmp_path):
    from sidpulse.project.format import save
    from sidpulse.song.model import Song,Instrument
    song=Song();song.instruments[24]=Instrument('Saved selection')
    path=save(tmp_path/'selection.sidpulse',song,{'instrument':24})
    original=path.read_bytes()
    app=App(audio=False)
    try:
        app.select_instrument_slot(number=50);app.sample_index=70
        app.open_project(path)
        assert app.editor.instrument==24  # Pattern metadata is still restored.
        assert app.instrument_slot==app.sample_index==1
        app.change_page('instrument')
        assert app.instrument_slot==app.editor.instrument==1
        app.select_instrument_slot(number=50);app.sample_index=70
        app.new_project()
        assert app.instrument_slot==app.sample_index==1
        assert path.read_bytes()==original and not app.editor.dirty
    finally:app.close()


def test_pattern_selection_centers_then_clamps_without_blank_padding():
    app=App(audio=False,size=(960,540))
    try:
        for row in (0,32,63):
            app.editor.row=row;app.renderer.render(app)
            first=app.renderer.top_row;last=app.renderer.pattern_geometry['last_row']
            if row==0:assert first==0
            elif row==63:assert last==63
            else:assert row-first==(last-first+1)//2
    finally:app.close()


@pytest.mark.parametrize('page,field,action',[
    ('instrument','instrument_slot','choose_instrument'),
    ('samples','sample_index','choose_sample'),
])
def test_click_wheel_and_keys_keep_bank_selection_in_the_same_centered_view(page,field,action,monkeypatch):
    from copy import deepcopy
    app=App(audio=False,size=(960,1080))
    try:
        app.change_page(page)
        before=deepcopy(app.editor.song)
        app.renderer.render(app)
        monkeypatch.setattr(pg.mouse,'get_pos',lambda:(10,200))
        monkeypatch.setattr(pg.key,'get_mods',lambda:0)
        # Reach the middle through wheel input, then select another visible row.
        app.handle(pg.event.Event(pg.MOUSEWHEEL,y=-49,x=0))
        assert getattr(app,field)==50
        app.renderer.render(app)
        target=next(r for r,a,v in app.renderer.hits if a==action and v==53)
        app.handle(pg.event.Event(pg.MOUSEBUTTONDOWN,button=1,pos=target.center))
        app.handle(pg.event.Event(pg.MOUSEBUTTONUP,button=1,pos=target.center))
        assert getattr(app,field)==53
        app.handle(pg.event.Event(pg.KEYDOWN,key=pg.K_DOWN,mod=0,unicode='',scancode=0))
        assert getattr(app,field)==54
        app.renderer.render(app)
        visible=[v for _,a,v in app.renderer.hits if a==action]
        assert visible.index(54)==len(visible)//2
        # Repeated scrolling clamps the selection and viewport at each end.
        for delta,selection in ((-200,99),(200,1)):
            app.handle(pg.event.Event(pg.MOUSEWHEEL,y=delta,x=0))
            assert getattr(app,field)==selection
            app.renderer.render(app)
            visible=[v for _,a,v in app.renderer.hits if a==action]
            assert visible[-1 if selection==99 else 0]==selection
        assert app.editor.song==before and not app.editor.history.undo_stack
    finally:app.close()
