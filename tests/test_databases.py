import os
import sys
import unittest
from unittest.mock import patch

# app modules use sys.path style imports (from logger import ...)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))
os.environ.setdefault('ENVIRONMENT', 'dev')

from databases import build_dump_strategy  # noqa: E402
from databases.firebird import FirebirdDump  # noqa: E402
from databases.postgres import PostgresDump  # noqa: E402


class TestPostgresDump(unittest.TestCase):
    @patch('generate_backup.subprocess.run')
    def test_command_and_credentials(self, mock_run):
        strategy = PostgresDump(
            host='localhost', port='5432', database='app',
            user='backup', password='pgpass',
        )

        actual = strategy.dump('/tmp/out.sql')

        self.assertTrue(actual)
        cmd = mock_run.call_args.args[0]
        env = mock_run.call_args.kwargs['env']
        self.assertEqual(cmd[0], 'pg_dump')
        self.assertIn('--file=/tmp/out.sql', cmd)
        self.assertNotIn('pgpass', ' '.join(cmd))
        self.assertEqual(env['PGPASSWORD'], 'pgpass')
        self.assertEqual(strategy.extension, '.sql')


class TestFirebirdDump(unittest.TestCase):
    @patch('generate_backup.subprocess.run')
    def test_command_and_credentials(self, mock_run):
        """
        Credentials must go through env, never through the command line
        """
        strategy = FirebirdDump(
            gbak_path='/opt/firebird/bin/gbak',
            host='localhost',
            port='3050',
            database='/data/db.fdb',
            user='SYSDBA',
            password='masterkey',
        )

        actual = strategy.dump('/tmp/out.fbk')

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
        self.assertEqual(env['ISC_USER'], 'SYSDBA')
        self.assertEqual(env['ISC_PASSWORD'], 'masterkey')
        self.assertIn('PATH', env)
        self.assertEqual(strategy.extension, '.fbk')


class TestBuildDumpStrategy(unittest.TestCase):
    def test_engines(self):
        self.assertIsInstance(build_dump_strategy('postgres'), PostgresDump)
        self.assertIsInstance(build_dump_strategy('firebird'), FirebirdDump)

    def test_invalid_engine(self):
        self.assertRaises(ValueError, build_dump_strategy, 'oracle')
