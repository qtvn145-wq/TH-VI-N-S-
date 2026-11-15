import importlib.util
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app

spec = importlib.util.spec_from_file_location('backup_tool', Path(__file__).parents[1] / 'scripts/backup.py')
backup_tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(backup_tool)

class DevOpsTests(unittest.TestCase):
    def test_restore_database_and_cover_and_refuse_overwrite(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / 'source'
            (source / 'covers').mkdir(parents=True)
            (source / 'covers/a.png').write_bytes(b'cover-content')
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
                    with sqlite3.connect(restored / 'library.db') as db:
                        self.assertEqual(db.execute('SELECT title FROM sample').fetchone()[0], 'Thu vien')
                    with self.assertRaisesRegex(ValueError, 'empty'):
                        backup_tool.restore(archive.name)

    def test_health_fails_without_schema_when_migrations_disabled(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, {'DATABASE_PATH': temp+'/empty.db', 'AUTO_MIGRATE': 'false'}):
            with TestClient(app, raise_server_exceptions=False) as client:
                self.assertGreaterEqual(client.get('/api/v1/health').status_code, 500)

    def test_smtp_password_file(self):
        from app.cli import reminders
        from app.db import connect
        from app.main import today
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, {
            'DATABASE_PATH':temp+'/smtp.db', 'SMTP_HOST':'smtp.example.test', 'SMTP_FROM':'library@example.test',
            'SMTP_USER':'library', 'SMTP_PASSWORD_FILE':temp+'/password', 'AUTO_MIGRATE':'true'
        }):
            Path(temp+'/password').write_text('test-password\n')
            with TestClient(app):
                with connect(True) as db:
                    db.execute("INSERT INTO users VALUES (1,'reader@example.test','Reader','hash','reader')")
                    db.execute("INSERT INTO books(id,title) VALUES (1,'Book')")
                    db.execute("INSERT INTO copies(id,book_id,barcode) VALUES (1,1,'B1')")
                    db.execute("INSERT INTO loans(id,user_id,copy_id,status,reserved_at,due_date,daily_fine) VALUES (1,1,1,'borrowed','2026-01-01',?,2000)",(today().isoformat(),))
                with patch('app.cli.smtplib.SMTP') as smtp:
                    self.assertEqual(reminders(True)['sent'],1)
                    smtp.return_value.__enter__.return_value.login.assert_called_once_with('library','test-password', initial_response_ok=False)
                    self.assertEqual(reminders(True)['sent'],0)

    def test_gmail_grouped_password_only_normalized_for_gmail(self):
        from app.cli import smtp_password
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'password'
            path.write_text('abcd efgh ijkl mnop\n')
            with patch.dict(os.environ, {'SMTP_PASSWORD_FILE': str(path), 'SMTP_HOST': 'smtp.gmail.com'}):
                self.assertEqual(smtp_password(), 'abcdefghijklmnop')
            with patch.dict(os.environ, {'SMTP_PASSWORD_FILE': str(path), 'SMTP_HOST': 'smtp.example.test'}):
                self.assertEqual(smtp_password(), 'abcd efgh ijkl mnop')
