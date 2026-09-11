import json
from copy import deepcopy
from pathlib import Path
import sys
import pygame as pg
import pytest
from sidpulse.preferences import save_preferences,config_path
from sidpulse.recovery import Autosave,preferences
from sidpulse.commands.editor import Editor
from sidpulse.song.model import Song
from sidpulse.project.format import load,save
from sidpulse.app import App
from sidpulse.ui.dialogs import choices
from test_checkpoint_026 import key,click


@pytest.fixture
def folder(tmp_path):
    path=tmp_path/'autosave'
    save_preferences({'autosave_directory':str(path)})
    return path


def edited():
    ed=Editor(Song());ed.enter_note(48)
    return ed


def snapshot(manager,ed,source=None,now=0):
    manager.tick(ed,{'row':ed.row},source,now=now)
    manager.tick(ed,{'row':ed.row},source,now=now+300)
    manager.flush()
    return Path(manager.state['autosave'])


def test_default_enabled_five_minutes_and_independent_atomic_copy(folder,tmp_path):
    prefs=preferences();assert prefs['autosave_enabled'] and prefs['autosave_minutes']==5
    manager=Autosave();manager.start();ed=edited();before=deepcopy(ed.song)
    source=save(tmp_path/'source.sidpulse',Song());source_bytes=source.read_bytes()
    manager.tick(ed,{},source,now=0);manager.tick(ed,{},source,now=299)
    assert not list(folder.iterdir())
    path=snapshot(manager,ed,source)
    assert load(path)[0]==before and ed.dirty and source.read_bytes()==source_bytes
    assert not list(folder.glob('*.tmp'))
    manager.tick(ed,{},source,now=601);manager.flush()
    assert len(list(folder.glob('*.sidpulse')))==1
    manager.close()
    assert Autosave().candidates()==[]


def test_unclean_session_offers_latest_and_live_session_is_skipped(folder):
    old=Autosave();old.start();ed=edited();first=snapshot(old,ed)
    probe=Autosave();assert probe.candidates()==[]
    ed.enter_note(55);old.tick(ed,{},now=601);old.flush()
    latest=old.state['autosave'];assert latest!=str(first)
    old.close(clean=False)
    candidates=probe.candidates();assert candidates[0][1]['autosave']==latest
    probe.acknowledge(candidates[0][0]);assert probe.candidates()==[]
    assert first.exists() and Path(latest).exists()


def test_disabled_and_reenabled_with_custom_interval(folder):
    save_preferences({'autosave_enabled':False})
    manager=Autosave();manager.start();ed=edited()
    manager.tick(ed,{},now=10000)
    assert not folder.exists() and not manager.state_path.exists() and not manager.candidates()
    manager.configure(True,1,folder)
    manager.tick(ed,{},now=0);manager.tick(ed,{},now=59)
    assert not manager.future
    manager.tick(ed,{},now=60);manager.flush()
    assert len(list(folder.glob('*.sidpulse')))==1
    manager.configure(False,1,folder);ed.enter_note(60);manager.tick(ed,{},now=60000)
    assert len(list(folder.glob('*.sidpulse')))==1
    manager.close()


def test_failed_save_keeps_previous_snapshot_and_retry_saves_revision(folder,monkeypatch):
    import sidpulse.recovery as recovery
    manager=Autosave();manager.start();ed=edited();path=snapshot(manager,ed)
    previous=manager.state_path.read_bytes()
    ed.enter_note(63)
    real=recovery.save
    def fail(*args,**kwargs):raise OSError('disk full')
    monkeypatch.setattr(recovery,'save',fail)
    manager.tick(ed,{},now=601);manager.flush()
    assert manager.blocked and 'disk full' in manager.warning
    assert manager.state_path.read_bytes()==previous and path.exists()
    monkeypatch.setattr(recovery,'save',real)
    manager.configure(True,5,folder);manager.next_due=602
    manager.tick(ed,{},now=602);manager.flush()
    assert load(manager.state['autosave'])[0]==ed.song
    manager.close()


def test_new_document_gets_own_interval_even_with_same_revision(folder):
    manager=Autosave();manager.start();snapshot(manager,edited())
    other=edited();other.song.title='Another project'
    manager.tick(other,{},now=700);manager.tick(other,{},now=999)
    assert len(list(folder.glob('*.sidpulse')))==1
    manager.tick(other,{},now=1000);manager.flush()
    assert len(list(folder.glob('*.sidpulse')))==2
    assert load(manager.state['autosave'])[0].title=='Another project'
    manager.close()


def test_unwritable_folder_ok_warning_and_create_retry(folder,tmp_path):
    folder.write_text('this is a file')
    app=App(audio=False)
    try:
        app.start_services()
        assert app.dialog['title']=='Autosave unavailable'
        assert [label for label,_ in choices(app.dialog)]==['OK']
        key(app,pg.K_RETURN);assert app.dialog is None
        from sidpulse.ui.autosave_settings import open_dialog,activate
        open_dialog(app);app.dialog['directory']=str(tmp_path/'new-folder');activate(app,'create')
        assert (tmp_path/'new-folder').is_dir()
        activate(app,'ok');assert app.autosave.enabled and not app.autosave.blocked
        assert app.dialog is None
    finally:app.close()


@pytest.mark.parametrize('restore',[True,False])
def test_recovery_prompt_load_and_skip_keep_source_safe(folder,tmp_path,restore):
    manager=Autosave();manager.start();ed=edited()
    source=save(tmp_path/'my-song.sidpulse',Song());before=source.read_bytes()
    saved=snapshot(manager,ed,source);manager.close(clean=False)
    app=App(audio=False)
    try:
        app.start_services();assert 'recover' in app.dialog
        click(app,'dialog_button',pg.K_y if restore else pg.K_n)
        assert app.dialog is None
        if restore:
            assert app.editor.song==ed.song and app.path==source and app.editor.dirty
        assert source.read_bytes()==before and saved.exists()
    finally:app.close()


def test_main_failure_records_traceback_and_emergency_recovery(folder,monkeypatch):
    from sidpulse.__main__ import main
    def fail(app,*args,**kwargs):
        app.editor.enter_note(61)
        raise RuntimeError('reproduced pattern failure')
    monkeypatch.setattr(App,'run',fail)
    monkeypatch.setattr(sys,'argv',['sidpulse','--headless-smoke','--silent'])
    assert main()==2
    logs=list((config_path().parent/'logs').glob('*.log'))
    assert len(logs)==1 and 'reproduced pattern failure' in logs[0].read_text()
    candidates=Autosave().candidates();assert len(candidates)==1
    assert load(candidates[0][1]['autosave'])[0].patterns[0].rows[0][0].note==61


def test_callback_failure_is_reported_once_and_silenced(monkeypatch):
    from sidpulse.audio.stream import PCMStream
    import sidpulse.diagnostics as diagnostics
    calls=[];monkeypatch.setattr(diagnostics,'record_exception',lambda *a:calls.append(a))
    stream=PCMStream(256,False)
    def fail(buffer):raise RuntimeError('callback broke')
    monkeypatch.setattr(stream,'_fill',fail)
    output=bytearray(b'x'*512)
    stream.callback(None,output);stream.callback(None,output)
    assert output==bytes(512) and len(calls)==1 and stream.callback_error


def test_hang_watchdog_writes_thread_stacks(folder):
    from test_checkpoint_026 import child
    child('''
        import faulthandler,time
        from sidpulse.diagnostics import Diagnostics
        diagnostic=Diagnostics();diagnostic.start()
        # Exercise the same native watchdog with a short deadline in this test.
        faulthandler.dump_traceback_later(.06,file=diagnostic.stream)
        time.sleep(.15)
        diagnostic.close()
        report=diagnostic.path.read_text()
        assert 'Timeout' in report and 'File' in report and '<module>' in report
    ''')
