import os
import sys
import unittest
from dataclasses import replace
from unittest.mock import MagicMock, patch

# app modules use sys.path style imports (from logger import ...)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))
os.environ.setdefault('ENVIRONMENT', 'dev')

from config import settings  # noqa: E402
from storages import build_storages  # noqa: E402
from storages.s3 import S3Storage  # noqa: E402
from storages.ssh import SSHStorage  # noqa: E402

FILENAME = 'backup_20260111_151836.fbk.gz'
EXISTING = 'backup_20260110_151836.fbk.gz'
SRC_FILES = [
    {'filepath': f'/srv/backup/{EXISTING}'},
    {'filepath': f'/srv/backup/{FILENAME}'},
]


def with_s3(**changes):
    return replace(settings, s3=replace(settings.s3, **changes))


def make_s3_storage():
    return S3Storage(
        bucket='bucket', prefix='backups', storage_class='STANDARD',
        access_key='key', secret_key='secret', region='sa-east-1',
    )


def make_ssh_storage(dest_path='/backups'):
    return SSHStorage(
        server='backup.local', port='22', user='backup',
        key_filepath='/home/backup/.ssh/id_ed25519',
        dest_path=dest_path, backup_days=7,
    )


class TestS3Storage(unittest.TestCase):
    @patch('storages.s3.upload_file_s3', return_value=True)
    @patch('storages.s3.has_s3_object')
    def test_skips_existing_and_uploads_new(self, mock_has, mock_upload):
        mock_has.side_effect = lambda client, bucket, key: key.endswith(
            EXISTING
        )
        storage = make_s3_storage()
        storage.client = MagicMock()

        actual = storage.upload(SRC_FILES)

        self.assertEqual(actual, {EXISTING, FILENAME})
        mock_upload.assert_called_once()
        self.assertEqual(mock_upload.call_args.args[3], f'backups/{FILENAME}')

    def test_upload_without_client_fails(self):
        self.assertRaises(Exception, make_s3_storage().upload, SRC_FILES)


class TestSSHStorage(unittest.TestCase):
    def test_connect_without_dest_path_fails(self):
        self.assertRaises(Exception, make_ssh_storage(dest_path=None).connect)

    @patch('storages.ssh.create_ssh_client')
    def test_connect_and_close(self, mock_create):
        storage = make_ssh_storage()

        storage.connect()
        client = storage.client
        storage.close()
        storage.close()

        client.close.assert_called_once()

    @patch('storages.ssh.copy_files_scp')
    @patch('storages.ssh.ensure_dest_path')
    @patch('storages.ssh.os.path.isfile', return_value=True)
    @patch('storages.ssh.search_for_files_ssh_server')
    def test_copies_only_missing_files(
        self, mock_search, _isfile, mock_ensure, mock_scp
    ):
        mock_search.side_effect = [[EXISTING], [EXISTING, FILENAME]]
        storage = make_ssh_storage()
        storage.client = MagicMock()

        actual = storage.upload(SRC_FILES)

        self.assertEqual(actual, {EXISTING, FILENAME})
        mock_ensure.assert_called_once_with(storage.client, '/backups')
        mock_scp.assert_called_once_with(
            storage.client, f'/srv/backup/{FILENAME}', f'/backups/{FILENAME}'
        )


class TestBuildStorages(unittest.TestCase):
    def test_invalid_target(self):
        self.assertRaises(ValueError, build_storages, ['ssh', 'ftp'])

    def test_empty_targets(self):
        self.assertRaises(ValueError, build_storages, [])

    @patch('storages.settings', with_s3(access_key_id=None))
    def test_s3_without_credentials(self):
        self.assertRaises(Exception, build_storages, ['s3'])

    @patch(
        'storages.settings',
        with_s3(
            bucket='bucket', access_key_id='key', secret_access_key='secret'
        ),
    )
    def test_builds_in_target_order(self):
        actual = build_storages(['s3', 'ssh'])

        self.assertEqual([storage.name for storage in actual], ['s3', 'ssh'])
