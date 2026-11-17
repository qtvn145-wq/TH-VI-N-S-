import importlib.util
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from backend.app.main import app

spec = importlib.util.spec_from_file_location('backup_tool', Path(__file__).parents[2] / 'devops/scripts/backup.py')
backup_tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(backup_tool)

class DevOpsTests(unittest.TestCase):
    def test_restore_database_and_cover_and_refuse_overwrite(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / 'source'
            (source / 'covers').mkdir(parents=True)
            (source / 'covers/a.png').write_bytes(b'cover-content')
            (source / 'ebooks').mkdir()
            (source / 'ebooks/book.pdf').write_bytes(b'pdf-content')
            with sqlite3.connect(source / 'library.db') as db:
                db.execute('CREATE TABLE sample(id INTEGER PRIMARY KEY, title TEXT)')
                db.execute("INSERT INTO sample VALUES (1, 'Thu vien')")
            with patch.object(backup_tool, 'DATA', source), patch.object(backup_tool, 'BACKUPS', root / 'backups'):
                backup_tool.backup()
                archive = next((root / 'backups').glob('*.tar.gz'))
                restored = root / 'restored'
                with patch.object(backup_tool, 'DATA', restored):
                    backup_tool.restore(archive.name)
                    self.assertEqual((restored / 'covers/a.png').read_bytes(), b'cover-content')
                    self.assertEqual((restored / 'ebooks/book.pdf').read_bytes(), b'pdf-content')
                    with sqlite3.connect(restored / 'library.db') as db:
                        self.assertEqual(db.execute('SELECT title FROM sample').fetchone()[0], 'Thu vien')
                    with self.assertRaisesRegex(ValueError, 'empty'):
                        backup_tool.restore(archive.name)

    def test_health_fails_without_schema_when_migrations_disabled(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, {'DATABASE_PATH': temp+'/empty.db', 'AUTO_MIGRATE': 'false'}):
            with TestClient(app, raise_server_exceptions=False) as client:
                self.assertGreaterEqual(client.get('/api/v1/health').status_code, 500)
