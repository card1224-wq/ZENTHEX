from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
import zenthex_enable_live as live


class LiveEnableTests(unittest.TestCase):
    def test_owner_validation_preserves_password_and_database(self):
        with tempfile.TemporaryDirectory() as temp:
            db=Path(temp)/'existing.db'
            with sqlite3.connect(db) as c:
                c.execute('CREATE TABLE users(email,role,approval_status,is_active,hashed_password)')
                c.execute('INSERT INTO users VALUES(?,?,?,?,?)',('7foliath@naver.com','owner','approved',1,'unchanged-secret-hash'))
            before=db.read_bytes()
            live.validate_owner({'ZENTHEX_DATABASE_URL':'sqlite:///'+str(db)})
            self.assertEqual(db.read_bytes(),before)

    def test_preflight_failure_never_changes_live_flag_or_restarts(self):
        with patch.object(live,'read_env',return_value={}),patch.object(live,'preflight',side_effect=RuntimeError('failed')),patch.object(live,'write_env') as write,patch.object(live.subprocess,'run') as run:
            with self.assertRaises(RuntimeError):live.enable('13.124.81.242',True)
            write.assert_not_called();run.assert_not_called()

    def test_check_only_never_changes_settings(self):
        with patch.object(live,'read_env',return_value={}),patch.object(live,'preflight'),patch.object(live,'validate_owner'),patch.object(live,'write_env') as write,patch.object(live.subprocess,'run') as run:
            live.enable('13.124.81.242',False)
            write.assert_not_called();run.assert_not_called()
