import os
import sqlite3
from pathlib import Path
from contextlib import contextmanager

@contextmanager
def connect(write=False):
    path = Path(os.getenv('DATABASE_PATH', 'data/library.db'))
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=15)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys=ON')
    db.execute('PRAGMA busy_timeout=15000')
    try:
        if write:
            db.execute('BEGIN IMMEDIATE')
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

def migrate():
    with connect() as db:
        db.execute('PRAGMA journal_mode=WAL')
        if db.execute('PRAGMA user_version').fetchone()[0] == 0:
            db.executescript((Path(__file__).parents[1] / 'migrations/001_initial.sql').read_text())

def get(db, table, id):
    from fastapi import HTTPException
    row = db.execute(f'SELECT * FROM {table} WHERE id=?', (id,)).fetchone()
    if row is None:
        raise HTTPException(404, 'NOT_FOUND')
    return dict(row)
