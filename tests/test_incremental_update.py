"""Standard-library updater regression cases; no downloads or Git writes."""
import importlib.util
from pathlib import Path
import os
import sys
import zipfile
import pytest

SPEC=importlib.util.spec_from_file_location('sidpulse_incremental_update',Path(__file__).resolve().parents[1]/'scripts'/'incremental_update.py')
u=importlib.util.module_from_spec(SPEC);sys.modules[SPEC.name]=u;SPEC.loader.exec_module(u)


def fixture(tmp_path,crlf=False):
    repo=tmp_path/'sidpulse-tracker';repo.mkdir()
    (repo/'VERSION').write_bytes(b'0.2.12\r\n' if crlf else b'0.2.12\n')
    (repo/'module.py').write_bytes(b'old\r\n' if crlf else b'old\n')
    archive=tmp_path/'update.zip'
    before={'VERSION':b'0.2.12\n','module.py':b'old\n','new.py':None}
    after={'VERSION':b'0.2.13\n','module.py':b'new\n','new.py':b'added\n'}
    files={name:{'before':u.content_digest(before[name],True) if before[name] is not None else None,
                 'after':u.content_digest(data,True),'text':True,'mode':0o644} for name,data in after.items()}
    with zipfile.ZipFile(archive,'w') as z:
        for name,data in after.items():z.writestr('sidpulse-tracker/'+name,data)
    return repo,archive,files,u.digest(archive.read_bytes())


def plan(values):return u.preflight(*values,'0.2.12','0.2.13')


@pytest.mark.parametrize('crlf',[False,True])
def test_apply_backup_idempotency_and_private_files(tmp_path,crlf):
    values=fixture(tmp_path,crlf);repo=values[0]
    for name in ('.git/HEAD','.venv/private','user_songs/private.sidpulse','autosaves/keep','preferences.json'):
        p=repo/name;p.parent.mkdir(exist_ok=True);p.write_bytes(b'leave me alone')
    expected=(repo/'module.py').read_bytes()
    todo=plan(values);assert todo[-1].relative=='VERSION'
    backup=u.apply_plan(repo,todo,'v0.2.13-test')
    assert (backup/'module.py').read_bytes()==expected
    assert (repo/'VERSION').read_text().strip()=='0.2.13'
    assert plan(values)==[]
    for name in ('.git/HEAD','.venv/private','user_songs/private.sidpulse','autosaves/keep','preferences.json'):
        assert (repo/name).read_bytes()==b'leave me alone'


def test_local_conflict_is_all_or_nothing(tmp_path):
    values=fixture(tmp_path);repo=values[0];(repo/'module.py').write_text('local edit')
    with pytest.raises(u.UpdateError,match='Local changes'):plan(values)
    assert (repo/'VERSION').read_text().strip()=='0.2.12' and not (repo/'new.py').exists()


def test_modified_archive_is_rejected(tmp_path):
    values=fixture(tmp_path);values[1].write_bytes(values[1].read_bytes()+b'changed')
    with pytest.raises(u.UpdateError,match='SHA-256'):plan(values)


def test_wrong_base_version_is_rejected(tmp_path):
    values=fixture(tmp_path);(values[0]/'VERSION').write_text('0.2.11\n')
    with pytest.raises(u.UpdateError,match='Expected'):plan(values)


@pytest.mark.parametrize('relative',['../oops','/absolute','a/../b','a\\b','.git/config','.venv/file','user_songs/song','preferences.json','assets/font.ttf'])
def test_unsafe_and_protected_paths_are_rejected(tmp_path,relative):
    with pytest.raises(u.UpdateError):u.target_path(tmp_path,relative)


def test_symlink_target_is_not_followed(tmp_path):
    values=fixture(tmp_path);repo=values[0];outside=tmp_path/'outside';outside.write_text('do not edit')
    (repo/'module.py').unlink()
    try:(repo/'module.py').symlink_to(outside)
    except OSError:pytest.skip('Host does not permit symlinks')
    with pytest.raises(u.UpdateError,match='symlink'):plan(values)
    assert outside.read_text()=='do not edit'


def test_write_failure_rolls_back_replaced_files(tmp_path,monkeypatch):
    values=fixture(tmp_path);repo=values[0];todo=plan(values)
    real=os.replace;calls=0
    def replace(source,target):
        nonlocal calls
        calls+=1
        if calls==2:raise OSError('injected write failure')
        return real(source,target)
    monkeypatch.setattr(u.os,'replace',replace)
    with pytest.raises(u.UpdateError,match='rolled back'):u.apply_plan(repo,todo,'test')
    assert (repo/'module.py').read_bytes()==b'old\n'
    assert (repo/'VERSION').read_bytes()==b'0.2.12\n'
    assert not (repo/'new.py').exists()


def test_change_after_preflight_aborts_before_first_write(tmp_path):
    values=fixture(tmp_path);todo=plan(values);repo=values[0]
    (repo/'module.py').write_bytes(b'racing editor')
    with pytest.raises(u.UpdateError,match='changed during preflight'):u.apply_plan(repo,todo,'test')
    assert (repo/'VERSION').read_bytes()==b'0.2.12\n'
    assert (repo/'module.py').read_bytes()==b'racing editor'


@pytest.mark.parametrize("baseline", ["0.2.11", "0.2.12"])
def test_cumulative_release_accepts_only_listed_versions_and_file_hashes(tmp_path, baseline):
    repo, archive, files, digest = fixture(tmp_path)
    (repo / "VERSION").write_text(baseline + "\n")
    files["VERSION"]["before"] = [u.content_digest((v + "\n").encode(), True) for v in ("0.2.11", "0.2.12")]
    files["module.py"]["before"] = [files["module.py"]["before"], u.content_digest(b"another known baseline\n", True)]
    files["new.py"]["before"] = [None]
    todo = u.preflight(repo, archive, files, digest, ("0.2.11", "0.2.12"), "0.2.13")
    assert len(todo) == 3
    (repo / "module.py").write_text("not a published baseline")
    with pytest.raises(u.UpdateError, match="Local changes"):
        u.preflight(repo, archive, files, digest, ("0.2.11", "0.2.12"), "0.2.13")


def test_known_obsolete_candidate_file_is_backed_up_and_removed(tmp_path):
    repo, archive, files, sha = fixture(tmp_path)
    obsolete = repo/'old.py'; obsolete.write_bytes(b'known old backend\n')
    files['old.py'] = {'before': [None, u.content_digest(obsolete.read_bytes(), True)],
                       'after': None, 'text': True, 'mode': 0o644}
    todo = plan((repo, archive, files, sha))
    backup = u.apply_plan(repo, todo, 'cleanup-test')
    assert not obsolete.exists()
    assert (backup/'old.py').read_bytes() == b'known old backend\n'
    assert plan((repo, archive, files, sha)) == []


def test_obsolete_but_locally_edited_file_is_never_removed(tmp_path):
    repo, archive, files, sha = fixture(tmp_path)
    (repo/'old.py').write_bytes(b'user changed this\n')
    files['old.py'] = {'before': [None, u.content_digest(b'known backend', True)],
                       'after': None, 'text': True, 'mode': 0o644}
    with pytest.raises(u.UpdateError, match='Local changes'):
        plan((repo, archive, files, sha))
    assert (repo/'VERSION').read_bytes() == b'0.2.12\n'


def test_removed_file_is_restored_if_later_write_fails(tmp_path, monkeypatch):
    repo, archive, files, sha = fixture(tmp_path)
    obsolete = repo/'aaa-old.py'; obsolete.write_bytes(b'old backend')
    files['aaa-old.py'] = {'before': [u.content_digest(obsolete.read_bytes(), True)],
                           'after': None, 'text': True, 'mode': 0o644}
    real = u.os.replace
    attempted = False
    def fail_once(src, dst):
        nonlocal attempted
        if not attempted:
            attempted = True
            raise OSError('injected failure after removal')
        return real(src, dst)
    monkeypatch.setattr(u.os, 'replace', fail_once)
    with pytest.raises(u.UpdateError, match='rolled back'):
        u.apply_plan(repo, plan((repo, archive, files, sha)), 'cleanup-test')
    assert obsolete.read_bytes() == b'old backend'
