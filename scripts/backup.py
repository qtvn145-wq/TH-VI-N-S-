"""Call with all application writers stopped. Restore ONLY into an empty volume."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import sys
import tarfile
import tempfile
import time
from datetime import datetime, timezone

DATA = Path(os.getenv("DATA_DIR", "/data"))
BACKUPS = Path(os.getenv("BACKUP_ROOT", "/backups"))

def verify(folder):
    manifest = json.loads((folder / "manifest.json").read_text())
    for name, digest in manifest["sha256"].items():
        path = folder / name
        if path.resolve().parent != folder.resolve() and folder.resolve() not in path.resolve().parents:
            raise ValueError("Invalid manifest path")
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError("Checksum mismatch: " + name)
    with sqlite3.connect(folder / "library.db") as db:
        if db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise ValueError("Database integrity failed")
        if db.execute("PRAGMA foreign_key_check").fetchall():
            raise ValueError("Database foreign keys failed")

def backup():
    BACKUPS.mkdir(parents=True, exist_ok=True)
    if not (DATA / "library.db").is_file():
        raise ValueError("No database to back up")
    with tempfile.TemporaryDirectory(dir=BACKUPS) as temp:
        folder = Path(temp)
        with sqlite3.connect(f"file:{DATA / 'library.db'}?mode=ro", uri=True) as src, sqlite3.connect(folder / "library.db") as dst:
            src.backup(dst)
        shutil.copytree(DATA / "covers", folder / "covers")
        hashes = {str(p.relative_to(folder)): hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.rglob("*") if p.is_file()}
        (folder / "manifest.json").write_text(json.dumps({"sha256": hashes, "created": datetime.now(timezone.utc).isoformat()}, indent=2))
        verify(folder)
        name = datetime.now(timezone.utc).strftime("library-%Y%m%dT%H%M%S%fZ.tar.gz")
        target = BACKUPS / name
        with tarfile.open(str(target) + ".partial", "w:gz") as tar:
            for p in folder.iterdir(): tar.add(p, arcname=p.name)
        os.replace(str(target) + ".partial", target)
        target.chmod(0o600)
        # Prune only complete archives after a new verified backup succeeds.
        for old in BACKUPS.glob("library-*.tar.gz"):
            if old != target and old.stat().st_mtime < time.time() - 14 * 86400:
                old.unlink()
        print(target, flush=True)

def restore(name):
    target = BACKUPS / name
    if Path(name).name != name: raise ValueError("Use backup filename only")
    DATA.mkdir(parents=True, exist_ok=True)
    if any(p.name != "covers" or any(p.iterdir()) for p in DATA.iterdir()):
        raise ValueError("Restore requires an empty data volume")
    with tempfile.TemporaryDirectory() as temp:
        folder = Path(temp)
        with tarfile.open(target) as tar:
            for member in tar.getmembers():
                if not (member.isfile() or member.isdir()): raise ValueError("Unsupported archive entry")
            tar.extractall(folder, filter="data")
        verify(folder)
        shutil.copy2(folder / "library.db", DATA / "library.db")
        shutil.copytree(folder / "covers", DATA / "covers", dirs_exist_ok=True)
        if os.geteuid() == 0:
            for path in [DATA, *DATA.rglob("*")]: os.chown(path, 10001, 10001)
        print("Restore verified; start backend and run smoke checks.")

if __name__ == "__main__":
    if sys.argv[1:] == ["backup"]: backup()
    elif len(sys.argv) == 3 and sys.argv[1] == "restore": restore(sys.argv[2])
    else: raise SystemExit("Usage: backup.py backup | restore FILENAME")
