"""Pure browser state and real file-operation regressions (no SDL)."""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import pytest
from sidpulse.ui.file_browser import FileBrowser, default_name, SUFFIXES, FOCI
from sidpulse.ui.file_actions import FileActions
from sidpulse.commands.editor import Editor
from sidpulse.song.model import Song
from sidpulse.project.format import save, load
from sidpulse.export.psid import compile_song
from sidpulse.export.prg import compile_prg


@pytest.mark.parametrize('mode', SUFFIXES)
def test_defaults_current_name_and_mode_filter(tmp_path,mode):
    for name in ['a.sidpulse','b.SIDPULSE','c.sid','d.prg','ignore.txt','.hidden.sidpulse']:
        (tmp_path/name).touch()
    (tmp_path/'z-directory').mkdir()
    b=FileBrowser(tmp_path);b.start(mode,tmp_path/'work_v09.sidpulse')
    assert b.name.text=='work_v09'+SUFFIXES[mode]
    assert not b.name.selected_text
    assert b.selected is not None and b.entries[1].is_dir()
    assert all(p.is_dir() or p.suffix.lower()==SUFFIXES[mode] for p in b.entries)
    assert all(not p.name.startswith('.') for p in b.entries[1:])
    assert b.focus==('list' if mode=='open' else 'name')


@pytest.mark.parametrize('mode', SUFFIXES)
def test_default_name_roundtrip_latest_incremental_save(tmp_path,mode):
    b=FileBrowser(tmp_path);b.remember_project(tmp_path/'work_v21.sidpulse')
    b.start(mode,tmp_path/'work_v22.sidpulse')
    assert b.name.text=='work_v22'+SUFFIXES[mode]
    b.start(mode,None);assert b.name.text=='untitled'+SUFFIXES[mode]


def test_directory_navigation_never_clears_filename_draft(tmp_path):
    sub=tmp_path/'sub';sub.mkdir();b=FileBrowser(tmp_path);b.start('save',tmp_path/'work_01.sidpulse')
    b.name.delete(True);b.name.insert('2');assert b.name.text=='work_02.sidpulse'
    b.navigate(sub);b.navigate(tmp_path)
    assert b.name.text=='work_02.sidpulse' and b.selected==sub
    b.location.reset(str(sub));assert b.enter_directory()
    assert b.name.text=='work_02.sidpulse' and b.target()==sub/'work_02.sidpulse'


def test_directory_failure_preserves_valid_directory_and_draft(tmp_path):
    b=FileBrowser(tmp_path);b.start('save');name=b.name.text;entries=b.entries[:]
    assert not b.navigate(tmp_path/'absent')
    assert b.directory==tmp_path and b.entries==entries and b.name.text==name and b.error
    b.location.reset('');assert not b.enter_directory()


def test_refresh_permission_failure_can_be_recovered(tmp_path,monkeypatch):
    b=FileBrowser(tmp_path);b.start('save');name=b.name.text
    original=Path.iterdir
    with monkeypatch.context() as m:
        m.setattr(Path,'iterdir',lambda p: (_ for _ in ()).throw(PermissionError('denied')))
        assert not b.refresh() and b.error and not b.entries
    assert b.refresh() and not b.error and b.name.text==name


def test_tab_and_shift_tab_visit_every_control(tmp_path):
    b=FileBrowser(tmp_path)
    for expected in FOCI[1:]+FOCI[:1]:b.tab();assert b.focus==expected
    for expected in tuple(reversed(FOCI)):b.tab(True);assert b.focus==expected


@pytest.mark.parametrize('mode', ['save','sid','prg'])
def test_extension_relative_absolute_and_directory_error(tmp_path,mode):
    b=FileBrowser(tmp_path);b.start(mode)
    b.set_name('new revision');assert b.target()==tmp_path/('new revision'+SUFFIXES[mode])
    b.set_name(str(tmp_path/('absolute'+SUFFIXES[mode])));assert b.target().name=='absolute'+SUFFIXES[mode]
    b.set_name(' x ');assert b.target().name==' x '+SUFFIXES[mode]
    b.set_name(str(tmp_path))
    with pytest.raises(ValueError,match='directory'):b.target()
    b.set_name('  ')
    with pytest.raises(ValueError,match='filename'):b.target()
    b.set_name('bad\x00name')
    with pytest.raises(ValueError,match='control'):b.target()


class Host(FileActions):
    """FileActions host using real Editor/serializers; substitutes UI/audio only."""
    def __init__(self, folder):
        self.browser=FileBrowser(folder);self.editor=Editor(Song());self.path=None
        self.page='pattern';self.previous_page='pattern';self.dialog=None;self.after_save=None
        self.text_active=False
    def sync_file_text_input(self):
        self.text_active=self.page=='files' and self.dialog is None and self.browser.field is not None
    def release_audition(self):pass
    def notice(self,title,message):self.dialog={'kind':'notice','title':title,'message':message}
    def save_project(self,target):
        self.path=save(target,self.editor.song);self.browser.remember_project(self.path)
        self.editor.mark_saved();self.page=self.browser.return_page;self.sync_file_text_input()
        if self.after_save:
            callback,self.after_save=self.after_save,None;callback()
    def open_project(self,target):
        song,metadata=load(target);self.path=target;self.editor=Editor(song)
        self.browser.remember_project(target);self.page='pattern';self.sync_file_text_input()


def test_save_as_then_f9_f10_offer_new_revision(tmp_path):
    h=Host(tmp_path);h.browse('save');assert h.dialog is None and h.text_active
    h.file_name='work_v01.sidpulse';h.submit_file();first=h.path;original=first.read_bytes()
    h.editor.song.title='Revision two';h.browse('save')
    h.browser.name.delete(True);h.browser.name.insert('2');h.submit_file()
    assert h.path==tmp_path/'work_v02.sidpulse' and first.read_bytes()==original
    for mode in ('open','save','sid','prg'):
        h.browse(mode);assert h.file_name=='work_v02'+SUFFIXES[mode]


def test_save_overwrite_cancel_retains_draft_and_pending_followup(tmp_path):
    h=Host(tmp_path);h.path=save(tmp_path/'existing.sidpulse',h.editor.song)
    old=h.path.read_bytes();h.editor.song.title='new';h.browse('save')
    followup=[];h.after_save=lambda:followup.append(True);h.submit_file()
    assert 'yes' in h.dialog and h.path.read_bytes()==old
    cancel=h.dialog['on_cancel'];h.dialog=None;cancel()
    assert h.text_active and h.after_save is not None and h.file_name=='existing.sidpulse'
    h.file_name='new.sidpulse';h.submit_file()
    assert followup==[True] and h.path.read_bytes()!=old and (tmp_path/'existing.sidpulse').read_bytes()==old


def test_confirm_overwrite_saves_backup(tmp_path):
    h=Host(tmp_path);h.path=save(tmp_path/'same.sidpulse',h.editor.song);old=h.path.read_bytes()
    h.editor.song.title='new';h.browse('save');h.submit_file()
    write=h.dialog['yes'];h.dialog=None;write()
    assert h.path.with_suffix('.sidpulse.bak').read_bytes()==old
    assert load(h.path)[0].title=='new'


def test_cancel_never_writes_or_runs_after_save(tmp_path):
    h=Host(tmp_path);h.editor.song.title='unsaved';before=deepcopy(h.editor.song)
    h.browse('save');h.after_save=lambda:pytest.fail('cancel ran follow-up');h.cancel_browser()
    assert not list(tmp_path.iterdir()) and h.page=='pattern' and h.after_save is None
    assert h.editor.song==before and h.editor.dirty


@pytest.mark.parametrize('kind',['sid','prg'])
def test_export_shared_browser_and_backups_keep_native_state(tmp_path,kind):
    h=Host(tmp_path);h.path=save(tmp_path/'song_02.sidpulse',h.editor.song)
    h.editor.song.title='unsaved source';before=deepcopy(h.editor.song);source=h.path.read_bytes()
    result=compile_song(h.editor.song) if kind=='sid' else compile_prg(h.editor.song)
    h.prompt_export(result,kind)
    assert h.page=='files' and h.file_mode==kind and h.dialog is None
    assert h.file_name=='song_02.'+kind
    h.submit_file();target=tmp_path/('song_02.'+kind);old=target.read_bytes()
    assert old==result.data and h.path.read_bytes()==source and h.editor.dirty and h.editor.song==before
    h.dialog=None;h.prompt_export(result,kind);h.submit_file()
    assert 'yes' in h.dialog;write=h.dialog['yes'];h.dialog=None;write()
    assert target.with_suffix('.'+kind+'.bak').read_bytes()==old


def test_save_failure_keeps_visible_draft(tmp_path,monkeypatch):
    h=Host(tmp_path);h.browse('save');h.file_name='keep_this_001.sidpulse'
    monkeypatch.setattr(h,'save_project',lambda p:(_ for _ in ()).throw(OSError('disk full')))
    h.submit_file()
    assert h.page=='files' and h.file_name=='keep_this_001.sidpulse' and 'disk full' in h.browser.error and h.text_active


def test_uncommitted_directory_is_checked_before_save(tmp_path):
    h=Host(tmp_path);h.browse('save');h.file_name='revision_2.sidpulse'
    h.browser.location.reset(str(tmp_path/'missing'));h.submit_file()
    assert not (tmp_path/h.file_name).exists() and h.path is None
    folder=tmp_path/'sub';folder.mkdir();h.browser.location.reset(str(folder));h.submit_file()
    assert h.path==folder/'revision_2.sidpulse'


def test_open_error_does_not_replace_song_or_name(tmp_path):
    h=Host(tmp_path);h.path=save(tmp_path/'good.sidpulse',h.editor.song);before=deepcopy(h.editor.song)
    (tmp_path/'bad.sidpulse').write_text('bad JSON')
    h.browse('open');h.file_name='bad.sidpulse';h.submit_file()
    assert h.editor.song==before and h.path.name=='good.sidpulse' and h.browser.error
    assert h.file_name=='bad.sidpulse'


def test_reopening_after_export_returns_to_current_project_directory(tmp_path):
    export_dir=tmp_path/'exports';export_dir.mkdir();b=FileBrowser(export_dir)
    source=tmp_path/'work_v24.sidpulse'
    for mode in SUFFIXES:
        b.directory=export_dir;b.start(mode,source)
        assert b.directory==tmp_path and b.name.text=='work_v24'+SUFFIXES[mode]
