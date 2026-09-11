"""Restore bundled development history without overwriting working files."""
from pathlib import Path
import subprocess

root = Path(__file__).resolve().parents[1]
if (root / ".git").exists():
    raise SystemExit("Git already exists; left untouched.")
bundle = root / "bootstrap-history.bundle"
if not bundle.exists():
    raise SystemExit("Use the full ZIP for its bootstrap-history.bundle.")


def git(*args):
    subprocess.run(["git", *args], cwd=root, check=True)


git("init", "-b", "main")
git("fetch", str(bundle), "refs/heads/main")
git("reset", "--mixed", "FETCH_HEAD")
git("fetch", str(bundle), "refs/tags/*:refs/tags/*")
print("Restored main and release tags. Working files were not overwritten.")
