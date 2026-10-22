import os
import sys
import unittest
from dataclasses import replace
from unittest.mock import patch

# app modules use sys.path style imports (from logger import ...)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))
os.environ.setdefault('ENVIRONMENT', 'dev')

from config import settings  # noqa: E402
from databases import build_dump_strategy  # noqa: E402
from databases.firebird import FirebirdDump  # noqa: E402
from databases.mysql import MySQLDump  # noqa: E402
from databases.postgres import PostgresDump  # noqa: E402

MYSQL_CONFIG = {
    'host': 'db.local',
    'port': '3306',
    'database': 'shop',
    'user': 'backup',
    'password': 'se"cr\\et',
}


def with_mysql(**changes):
    return replace(settings, mysql=replace(settings.mysql, **changes))


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


class TestMySQLDump(unittest.TestCase):
    def run_dump(self, strategy, returncode=0):
        """
        Runs the dump capturing the command and the option file content
        (the file is deleted when dump returns).
        """
        captured = {}

        def fake_run(cmd, **kwargs):
            options_file = cmd[1].split('=', 1)[1]
            with open(options_file) as f:
                captured['options'] = f.read()
            captured['mode'] = os.stat(options_file).st_mode & 0o777
            captured['options_file'] = options_file
            captured['cmd'] = cmd
            captured['env'] = kwargs['env']
            if returncode:
                raise OSError('dump binary not found')

        with patch('generate_backup.subprocess.run', side_effect=fake_run):
            captured['result'] = strategy.dump('/tmp/out.sql')

        return captured

    def test_command_and_credentials(self):
        actual = self.run_dump(MySQLDump(binary='mysqldump', **MYSQL_CONFIG))

        self.assertTrue(actual['result'])
        cmd = actual['cmd']
        self.assertEqual(cmd[0], 'mysqldump')
        self.assertTrue(cmd[1].startswith('--defaults-extra-file='))
        self.assertIn('--host=db.local', cmd)
        self.assertIn('--port=3306', cmd)
        self.assertIn('--user=backup', cmd)
        self.assertIn('--single-transaction', cmd)
        self.assertIn('--result-file=/tmp/out.sql', cmd)
        self.assertEqual(cmd[-1], 'shop')
        self.assertFalse(any('cr\\et' in arg for arg in cmd))
        self.assertNotIn('MYSQL_PWD', actual['env'])
        self.assertEqual(
            actual['options'], '[client]\npassword="se\\"cr\\\\et"\n'
        )
        self.assertEqual(actual['mode'], 0o600)
        self.assertFalse(os.path.exists(actual['options_file']))

    def test_options_file_removed_on_failure(self):
        actual = self.run_dump(
            MySQLDump(binary='mysqldump', **MYSQL_CONFIG), returncode=1
        )

        self.assertFalse(actual['result'])
        self.assertFalse(os.path.exists(actual['options_file']))


class TestBuildDumpStrategy(unittest.TestCase):
    def test_engines(self):
        self.assertIsInstance(build_dump_strategy('postgres'), PostgresDump)
        self.assertIsInstance(build_dump_strategy('firebird'), FirebirdDump)

    @patch('databases.settings', with_mysql(dump_path=None))
    def test_mysql_and_mariadb_binaries(self):
        mysql = build_dump_strategy('mysql')
        mariadb = build_dump_strategy('mariadb')

        self.assertEqual(mysql.binary, 'mysqldump')
        self.assertIn('--set-gtid-purged=OFF', mysql.extra_args)
        self.assertEqual(mariadb.binary, 'mariadb-dump')
        self.assertEqual(mariadb.tool, 'mariadb-dump')
        self.assertEqual(mariadb.extra_args, [])

    @patch(
        'databases.settings',
        with_mysql(dump_path='/opt/mariadb/bin/mariadb-dump'),
    )
    def test_custom_dump_path(self):
        actual = build_dump_strategy('mariadb')

        self.assertEqual(actual.binary, '/opt/mariadb/bin/mariadb-dump')
        self.assertEqual(actual.tool, 'mariadb-dump')

    def test_invalid_engine(self):
        self.assertRaises(ValueError, build_dump_strategy, 'oracle')
