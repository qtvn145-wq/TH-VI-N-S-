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
        version=db.execute('PRAGMA user_version').fetchone()[0]
        scripts=Path(__file__).parents[1] / 'migrations'
        if version == 0:
            db.executescript((scripts / '000_ebook_fresh.sql').read_text())
        elif version in (1,2):
            if version == 1:
                db.executescript((scripts / '002_favorites.sql').read_text())
            db.executescript((scripts / '003_ebooks.sql').read_text())
        elif version not in (3,4):
            raise RuntimeError('Unsupported database schema')
        if version < 4:
            db.executescript((scripts / '004_password_reset.sql').read_text())

def get(db, table, id):
    from fastapi import HTTPException
    row = db.execute(f'SELECT * FROM {table} WHERE id=?', (id,)).fetchone()
    if row is None:
        raise HTTPException(404, 'NOT_FOUND')
    return dict(row)
