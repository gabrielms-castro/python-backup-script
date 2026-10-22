import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

# app modules use sys.path style imports (from logger import ...)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))
os.environ.setdefault('ENVIRONMENT', 'dev')

from config import BASE_DIR, Settings  # noqa: E402

PROD_ENV = {
    'ENVIRONMENT': 'prod',
    'SOURCE_PATH': '/var/backups/db',
    'LOGS_DIR': '/var/log/backup_script',
}


def load(**env):
    with patch.dict(os.environ, env, clear=True):
        return Settings.from_env()


class TestSettings(unittest.TestCase):
    def test_defaults(self):
        actual = load(**PROD_ENV)

        self.assertEqual(actual.source_path, Path('/var/backups/db'))
        self.assertEqual(actual.logs_dir, Path('/var/log/backup_script'))
        self.assertEqual(actual.db_engine, 'postgres')
        self.assertTrue(actual.compress_backup)
        self.assertEqual(actual.backup_targets, ('ssh',))
        self.assertIsNone(actual.healthcheck_url)
        self.assertEqual(actual.pg.port, '5432')
        self.assertEqual(actual.firebird.user, 'SYSDBA')
        self.assertEqual(actual.ssh.backup_days, 7)
        self.assertIsNone(actual.ssh.dest_path)
        self.assertEqual(actual.s3.region, 'us-east-1')

    def test_empty_values_use_defaults(self):
        actual = load(**{
            **PROD_ENV,
            'BACKUP_DAYS': '',
            'COMPRESS_BACKUP': '  ',
            'DB_ENGINE': '',
            'LOGS_DIR': '',
            'S3_PREFIX': '',
        })

        self.assertEqual(actual.ssh.backup_days, 7)
        self.assertTrue(actual.compress_backup)
        self.assertEqual(actual.db_engine, 'postgres')
        self.assertEqual(actual.logs_dir, BASE_DIR / 'logs')
        self.assertEqual(actual.s3.prefix, '')

    def test_casts(self):
        actual = load(
            **PROD_ENV,
            BACKUP_DAYS='30',
            COMPRESS_BACKUP='False',
            DB_ENGINE='Firebird',
            BACKUP_TARGETS=' SSH, s3 ,',
            DEST_PATH='/srv/backups',
        )

        self.assertEqual(actual.ssh.backup_days, 30)
        self.assertFalse(actual.compress_backup)
        self.assertEqual(actual.db_engine, 'firebird')
        self.assertEqual(actual.backup_targets, ('ssh', 's3'))
        self.assertEqual(actual.ssh.dest_path, Path('/srv/backups'))

    def test_dev_overrides_paths(self):
        actual = load(ENVIRONMENT='dev', SOURCE_PATH='/ignored', LOGS_DIR='/x')

        self.assertEqual(actual.source_path, Path('/srv/test_app/backup'))
        self.assertEqual(actual.logs_dir, BASE_DIR / 'logs')

    def test_ssh_port_fallback(self):
        self.assertEqual(load(**PROD_ENV).ssh.port, '22')
        self.assertEqual(load(**PROD_ENV, PORT='2222').ssh.port, '2222')
        self.assertEqual(
            load(**PROD_ENV, PORT='2222', SSH_PORT='2200').ssh.port, '2200'
        )

    def test_source_path_required_in_prod(self):
        self.assertRaises(ValueError, load, ENVIRONMENT='prod')
        self.assertRaises(
            ValueError, load, ENVIRONMENT='prod', SOURCE_PATH=' '
        )

    def test_secrets_not_in_repr(self):
        actual = load(
            **PROD_ENV,
            PG_PASSWORD='pg-secret',
            FB_PASSWORD='fb-secret',
            MYSQL_PASSWORD='mysql-secret',
            SSH_PASSWORD='ssh-secret',
            AWS_ACCESS_KEY_ID='AKIA-secret',
            AWS_SECRET_ACCESS_KEY='aws-secret',
        )

        text = repr(actual)
        for secret in ('pg-secret', 'fb-secret', 'mysql-secret',
                       'ssh-secret', 'AKIA-secret', 'aws-secret'):
            self.assertNotIn(secret, text)
        self.assertEqual(actual.pg.password, 'pg-secret')


if __name__ == '__main__':
    unittest.main()
