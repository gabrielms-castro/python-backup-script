import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

# app modules use sys.path style imports (from utils import ...)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))
os.environ.setdefault('ENVIRONMENT', 'dev')

import backup  # noqa: E402
from directory_cleaner import source_dir_cleaner  # noqa: E402

FILENAME = 'backup_20260111_151836.fbk.gz'


class TestSourceDirCleaner(unittest.TestCase):
    def test_deletes_only_backed_up_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            kept = os.path.join(tmp, 'backup_20260110_151836.fbk.gz')
            deleted = os.path.join(tmp, FILENAME)
            for path in (kept, deleted):
                with open(path, 'w') as f:
                    f.write('x')

            source_dir_cleaner(
                [{'filepath': kept}, {'filepath': deleted}], {FILENAME}
            )

            self.assertTrue(os.path.exists(kept))
            self.assertFalse(os.path.exists(deleted))


class FakeStorage:
    def __init__(self, name, uploaded=None, connect_error=None):
        self.name = name
        self.uploaded = uploaded if uploaded is not None else set()
        self.connect_error = connect_error
        self.retention_applied = False

    def connect(self):
        if self.connect_error:
            raise self.connect_error

    def upload(self, src_files):
        return set(self.uploaded)

    def apply_retention(self):
        self.retention_applied = True


@patch('backup.source_dir_cleaner')
@patch('backup.search_for_backup_files')
@patch('backup.generate_backup', return_value=f'/srv/backup/{FILENAME}')
class TestRunBackup(unittest.TestCase):
    def setUp(self):
        self.src_files = [{'filepath': f'/srv/backup/{FILENAME}'}]

    def run_backup(self, storages, summary=None):
        return backup.run_backup(
            src_path='/srv/backup',
            dump_strategy=MagicMock(),
            storages=storages,
            summary=summary,
        )

    def test_all_targets_ok(self, _gen, mock_search, mock_clean):
        mock_search.return_value = self.src_files
        ssh = FakeStorage('ssh', {FILENAME})

        summary = {}
        self.run_backup([ssh, FakeStorage('s3', {FILENAME})], summary)

        mock_clean.assert_called_once_with(self.src_files, {FILENAME})
        self.assertTrue(ssh.retention_applied)
        self.assertEqual(summary['backup_file'], FILENAME)
        self.assertEqual(summary['target_results'], {'ssh': 'ok', 's3': 'ok'})
        self.assertEqual(summary['failed_targets'], [])
        self.assertEqual(summary['files_backed_up'], 1)

    def test_ssh_connection_failed_keeps_local_file(
        self, _gen, mock_search, mock_clean
    ):
        """
        SSH connection fails: upload to S3, keep the local file
        """
        mock_search.return_value = self.src_files
        storages = [
            FakeStorage('ssh', connect_error=Exception('connection refused')),
            FakeStorage('s3', {FILENAME}),
        ]

        summary = {}
        with self.assertRaises(Exception) as ctx:
            self.run_backup(storages, summary)

        self.assertIn('ssh', str(ctx.exception))
        mock_clean.assert_called_once_with(self.src_files, set())
        self.assertEqual(
            summary['target_results'], {'ssh': 'failed', 's3': 'ok'}
        )
        self.assertEqual(summary['failed_targets'], ['ssh'])
        self.assertEqual(summary['files_backed_up'], 0)

    def test_s3_upload_failed_keeps_local_file(
        self, _gen, mock_search, mock_clean
    ):
        mock_search.return_value = self.src_files
        storages = [FakeStorage('ssh', {FILENAME}), FakeStorage('s3')]

        with self.assertRaises(Exception) as ctx:
            self.run_backup(storages)

        self.assertIn('s3', str(ctx.exception))
        mock_clean.assert_called_once_with(self.src_files, set())

    def test_s3_only(self, _gen, mock_search, mock_clean):
        mock_search.return_value = self.src_files

        self.run_backup([FakeStorage('s3', {FILENAME})])

        mock_clean.assert_called_once_with(self.src_files, {FILENAME})

    def test_no_storage(self, _gen, mock_search, mock_clean):
        self.assertRaises(Exception, self.run_backup, [])
