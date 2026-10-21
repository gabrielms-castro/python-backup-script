import gzip
import os
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

# app modules use sys.path style imports (from logger import ...)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from app.generate_backup import (  # noqa: E402
    compress_file,
    gbak_backup_database,
    generate_backup,
)

FB_CONFIG = {
    'gbak_path': '/opt/firebird/bin/gbak',
    'host': 'localhost',
    'port': '3050',
    'database': '/data/db.fdb',
    'user': 'SYSDBA',
    'password': 'masterkey',
}


class TestGbakBackupDatabase(unittest.TestCase):
    @patch('app.generate_backup.subprocess.run')
    def test_gbak_command_and_credentials(self, mock_run):
        """
        Credentials must go through env, never through the command line
        """
        actual = gbak_backup_database(output_file='/tmp/out.fbk', **FB_CONFIG)

        self.assertTrue(actual)
        cmd = mock_run.call_args.args[0]
        env = mock_run.call_args.kwargs['env']
        self.assertEqual(
            cmd,
            [
                '/opt/firebird/bin/gbak',
                '-b',
                '-v',
                '-g',
                'localhost/3050:/data/db.fdb',
                '/tmp/out.fbk',
            ],
        )
        self.assertNotIn('masterkey', cmd)
        self.assertEqual(env['ISC_USER'], 'SYSDBA')
        self.assertEqual(env['ISC_PASSWORD'], 'masterkey')
        self.assertIn('PATH', env)

    @patch('app.generate_backup.subprocess.run')
    def test_gbak_failure_removes_partial_file(self, mock_run):
        mock_run.side_effect = subprocess.CalledProcessError(
            1, 'gbak', stderr='boom'
        )

        with tempfile.TemporaryDirectory() as tmp:
            output_file = os.path.join(tmp, 'backup_20260111_151836.fbk')
            with open(output_file, 'w') as f:
                f.write('partial')

            actual = gbak_backup_database(
                output_file=output_file, **FB_CONFIG
            )

            self.assertFalse(actual)
            self.assertFalse(os.path.exists(output_file))


class TestCompressFile(unittest.TestCase):
    def test_compress_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            filepath = os.path.join(tmp, 'backup_20260111_151836.fbk')
            content = b'firebird backup content' * 100
            with open(filepath, 'wb') as f:
                f.write(content)

            actual = compress_file(filepath)

            self.assertEqual(actual, f'{filepath}.gz')
            self.assertFalse(os.path.exists(filepath))
            with gzip.open(actual, 'rb') as f:
                self.assertEqual(f.read(), content)


class TestGenerateBackup(unittest.TestCase):
    @patch('app.generate_backup.gbak_backup_database', return_value=True)
    def test_firebird_extension(self, mock_gbak):
        actual = generate_backup(
            engine='firebird',
            output_dir='/srv/backup',
            timestamp='20260111_151836',
            db_config=FB_CONFIG,
            compress=False,
        )

        self.assertEqual(actual, '/srv/backup/backup_20260111_151836.fbk')
        mock_gbak.assert_called_once()

    @patch('app.generate_backup.pg_dump_database', return_value=True)
    def test_postgres_extension(self, mock_pg_dump):
        actual = generate_backup(
            engine='postgres',
            output_dir='/srv/backup',
            timestamp='20260111_151836',
            db_config={},
            compress=False,
        )

        self.assertEqual(actual, '/srv/backup/backup_20260111_151836.sql')
        mock_pg_dump.assert_called_once()

    @patch('app.generate_backup.gbak_backup_database', return_value=False)
    def test_failed_backup_returns_none(self, mock_gbak):
        actual = generate_backup(
            engine='firebird',
            output_dir='/srv/backup',
            timestamp='20260111_151836',
            db_config=FB_CONFIG,
        )

        self.assertIsNone(actual)

    def test_invalid_engine(self):
        self.assertRaises(
            ValueError,
            generate_backup,
            engine='mysql',
            output_dir='/srv/backup',
            timestamp='20260111_151836',
            db_config={},
        )
