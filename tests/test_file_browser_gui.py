"""Real pygame/SDL browser tests. Skipped when pygame-ce is unavailable."""
from export_gui_helpers import finish_export_analysis
from copy import deepcopy
import pytest
pg=pytest.importorskip('pygame')
from sidpulse.app import App
from sidpulse.song.model import Song
from sidpulse.project.format import save,load
from sidpulse.ui.keyboard import Command,dispatch
from sidpulse.export.psid import compile_song
from sidpulse.export.prg import compile_prg


def key(a,k,mod=0,text='',scan=0):
    a.handle(pg.event.Event(pg.KEYDOWN,key=k,mod=mod,unicode=text,scancode=scan))


def text(a,s):a.handle(pg.event.Event(pg.TEXTINPUT,text=s))


def replace(a,s):
    key(a,pg.K_a,pg.KMOD_CTRL);text(a,s)


def click(a,action,value=None):
    a.renderer.render(a)
    rect=next(r for r,k,v in a.renderer.hits if (k,v)==(action,value))
    a.handle(pg.event.Event(pg.MOUSEBUTTONDOWN,button=1,pos=rect.center))
    return rect


@pytest.fixture
def app(tmp_path):
    a=App(Song(),audio=False);a.file_dir=tmp_path
    yield a
    a.close()


def test_f10_known_project_opens_picker_and_edits_only_version(app,tmp_path):
    source=tmp_path/'test_v21.sidpulse';save(source,app.editor.song);app.open_project(source)
    original=source.read_bytes();before=deepcopy(app.editor.song)
    key(app,pg.K_F10)
    assert app.page=='files' and app.dialog is None and app.file_name=='test_v21.sidpulse'
    assert app.browser.focus=='name' and app.browser.name.selected_text==''
    key(app,pg.K_BACKSPACE);text(app,'2');key(app,pg.K_RETURN)
    assert app.path==tmp_path/'test_v22.sidpulse'
    assert source.read_bytes()==original and app.editor.song==before
    key(app,pg.K_F9)
    assert app.file_name=='test_v22.sidpulse' and app.file_dir==tmp_path


def test_caret_keys_never_move_buttons_or_note_cursor(app):
    app.browse('save');app.file_name='melody_007.sidpulse';before=deepcopy(app.editor.song)
    row,voice,column=app.editor.row,app.editor.voice,app.editor.column
    key(app,pg.K_LEFT);key(app,pg.K_LEFT);key(app,pg.K_DELETE);text(app,'1')
    assert app.file_name=='melody_017.sidpulse' and app.browser.focus=='name'
    key(app,pg.K_HOME);text(app,'A_');key(app,pg.K_END);key(app,pg.K_LEFT,pg.KMOD_SHIFT)
    assert app.browser.name.selected_text=='e'
    assert app.editor.song==before and (app.editor.row,app.editor.voice,app.editor.column)==(row,voice,column)


def test_typing_piano_keys_and_unicode_only_enters_filename(app):
    app.browse('save');key(app,pg.K_a,pg.KMOD_CTRL)
    before=deepcopy(app.editor.song)
    key(app,pg.K_z,text='z',scan=29);text(app,'sävel_新_v04.sidpulse')
    assert app.file_name=='sävel_新_v04.sidpulse' and app.editor.song==before
    assert not app.held


def test_tab_directory_and_parent_preserve_incremental_name(app,tmp_path):
    folder=tmp_path/'sub';folder.mkdir();app.browse('save');app.file_name='work_009.sidpulse'
    key(app,pg.K_BACKSPACE);text(app,'8')
    key(app,pg.K_l,pg.KMOD_CTRL);replace(app,str(folder));key(app,pg.K_RETURN)
    assert app.file_dir==folder and app.file_name=='work_008.sidpulse'
    key(app,pg.K_BACKSPACE);assert app.file_dir==tmp_path
    key(app,pg.K_TAB);assert app.browser.focus=='name'
    key(app,pg.K_TAB,pg.KMOD_SHIFT);assert app.browser.focus=='list'


def test_overwrite_cancel_reopens_same_editable_field(app,tmp_path):
    source=save(tmp_path/'same.sidpulse',app.editor.song);app.open_project(source);old=source.read_bytes()
    app.editor.song.title='edited';key(app,pg.K_F10);key(app,pg.K_RETURN)
    assert 'yes' in app.dialog
    key(app,pg.K_RETURN)  # default is Cancel, never accidental overwrite
    assert app.dialog is None and app.browser.focus=='name' and source.read_bytes()==old
    key(app,pg.K_BACKSPACE);text(app,'2');key(app,pg.K_RETURN)
    assert app.path.name=='sam2.sidpulse' and source.read_bytes()==old


@pytest.mark.parametrize('kind',['sid','prg'])
def test_export_only_uses_browser_and_does_not_rename_source(app,tmp_path,kind):
    source=save(tmp_path/'song_v31.sidpulse',app.editor.song);app.open_project(source)
    app.editor.song.title='unsaved';before=deepcopy(app.editor.song)
    app.begin_export(kind);finish_export_analysis(app);key(app,pg.K_e)
    assert app.dialog is None and app.page=='files' and app.file_mode==kind
    assert app.file_name=='song_v31.'+kind
    replace(app,'take_02.'+kind);key(app,pg.K_RETURN)
    assert (tmp_path/('take_02.'+kind)).exists() and app.path==source
    assert app.editor.song==before and app.editor.dirty


def test_save_before_export_continuation_uses_new_saved_basename(app,tmp_path):
    app.begin_export('sid');finish_export_analysis(app);key(app,pg.K_s)
    assert app.page=='files' and app.file_mode=='save' and app.dialog is None
    replace(app,'fresh_v42.sidpulse');key(app,pg.K_RETURN)
    assert app.path==tmp_path/'fresh_v42.sidpulse' and app.file_mode=='sid' and app.page=='files'
    assert app.file_name=='fresh_v42.sid' and app.dialog is None
    key(app,pg.K_RETURN);assert (tmp_path/'fresh_v42.sid').read_bytes()[:4]==b'PSID'


def test_quick_save_vs_f10_and_cancel(app,tmp_path):
    source=save(tmp_path/'quick.sidpulse',app.editor.song);app.open_project(source)
    app.change_page('instrument');app.editor.song.title='saved'
    key(app,pg.K_s,pg.KMOD_CTRL)
    assert app.page=='instrument' and load(source)[0].title=='saved'
    key(app,pg.K_F10);assert app.page=='files' and app.dialog is None
    replace(app,'not_saved.sidpulse');key(app,pg.K_ESCAPE)
    assert app.page=='instrument' and not (tmp_path/'not_saved.sidpulse').exists()
    assert dispatch(pg.event.Event(pg.KEYDOWN,key=pg.K_s,mod=pg.KMOD_CTRL)).name=='quick_save'


def test_ctrl_s_in_filename_submits_visible_draft(app,tmp_path):
    app.browse('save');replace(app,'visible_draft.sidpulse');key(app,pg.K_s,pg.KMOD_CTRL)
    assert app.path==tmp_path/'visible_draft.sidpulse'


def test_directory_click_and_new_name_are_not_modal(app):
    app.browse('save');app.file_name='abcdefgh_v03.sidpulse'
    app.renderer.render(app)
    r=next(r for r,a,v in app.renderer.hits if a=='filename')
    app.handle(pg.event.Event(pg.MOUSEBUTTONDOWN,button=1,pos=(r.left+max(2,app.renderer.cw//3)+3*app.renderer.cw,r.centery)))
    assert app.dialog is None and app.browser.name.caret==3
    text(app,'X');assert app.file_name=='abcXdefgh_v03.sidpulse'


@pytest.mark.parametrize('mode',['open','save','sid','prg'])
@pytest.mark.parametrize('size,zoom',[((480,360),1),((480,360),3),((800,600),3),((1280,900),1),((1920,360),3)])
def test_browser_fields_buttons_and_file_rows_fit(app,mode,size,zoom):
    app.handle(pg.event.Event(pg.VIDEORESIZE,w=size[0],h=size[1],size=size));app.zoom=zoom
    app.browse(mode,result=compile_song(app.editor.song) if mode=='sid' else compile_prg(app.editor.song) if mode=='prg' else None)
    before=deepcopy(app.editor.song);app.renderer.render(app)
    rects=[r for r,k,v in app.renderer.hits if k in ('filename','file_directory','file_submit','file_cancel','file_parent','file_refresh','file')]
    assert len(rects)>=6 and all(app.screen.get_rect().contains(r) for r in rects)
    assert all(r.bottom <= (app.renderer.lines-app.renderer.footer_rows)*app.renderer.rh for r in rects)
    assert app.zoom==zoom and app.editor.song==before


def test_invalid_directory_on_save_does_not_fall_back_silently(app,tmp_path):
    app.browse('save');app.file_name='test.sidpulse';app.browser.location.reset(str(tmp_path/'missing'))
    click(app,'file_submit')
    assert app.path is None and not (tmp_path/'test.sidpulse').exists() and app.browser.error


def test_altgr_text_never_quick_saves_or_opens_an_export(app,tmp_path):
    app.browse('save');replace(app,'name_01.sidpulse')
    before=app.file_name
    for letter,glyph in [('s','š'),('e','€'),('l','ł')]:
        key(app,getattr(pg,'K_'+letter),pg.KMOD_LCTRL|pg.KMOD_RALT,text=glyph)
        assert app.path is None and app.dialog is None and app.page=='files'
        text(app,glyph)
    assert 'š€ł' in app.file_name and not list(tmp_path.glob('*.sidpulse'))


def test_clipboard_and_selection_preserve_extension(app,monkeypatch):
    clipboard=['']
    monkeypatch.setattr(pg.scrap,'put_text',lambda s:clipboard.__setitem__(0,s))
    monkeypatch.setattr(pg.scrap,'get_text',lambda:clipboard[0])
    app.browse('save');app.file_name='song_v12.sidpulse'
    key(app,pg.K_LEFT,pg.KMOD_SHIFT);key(app,pg.K_LEFT,pg.KMOD_SHIFT)
    key(app,pg.K_c,pg.KMOD_CTRL);assert clipboard[0]=='12'
    key(app,pg.K_x,pg.KMOD_CTRL);assert app.file_name=='song_v.sidpulse'
    clipboard[0]='34';key(app,pg.K_v,pg.KMOD_CTRL)
    assert app.file_name=='song_v34.sidpulse'
