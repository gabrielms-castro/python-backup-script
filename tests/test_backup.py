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


@patch('backup.source_dir_cleaner')
@patch('backup.search_for_backup_files')
@patch('backup.generate_backup', return_value=f'/srv/backup/{FILENAME}')
class TestRunBackup(unittest.TestCase):
    def setUp(self):
        self.src_files = [{'filepath': f'/srv/backup/{FILENAME}'}]

    def run_backup(self, targets, ssh_client=None, s3_client=None):
        return backup.run_backup(
            src_path='/srv/backup',
            backup_days=7,
            targets=targets,
            ssh_client=ssh_client,
            dest_path='/backups',
            s3_client=s3_client,
        )

    @patch('backup.copy_files_s3', return_value={FILENAME})
    @patch('backup.run_ssh_backup', return_value={FILENAME})
    def test_all_targets_ok(self, _ssh, _s3, _gen, mock_search, mock_clean):
        mock_search.return_value = self.src_files

        self.run_backup(['ssh', 's3'], MagicMock(), MagicMock())

        mock_clean.assert_called_once_with(self.src_files, {FILENAME})

    @patch('backup.copy_files_s3', return_value={FILENAME})
    def test_ssh_connection_failed_keeps_local_file(
        self, _s3, _gen, mock_search, mock_clean
    ):
        """
        SSH configured but client missing: upload to S3, keep the local file
        """
        mock_search.return_value = self.src_files

        with self.assertRaises(Exception) as ctx:
            self.run_backup(['ssh', 's3'], ssh_client=None, s3_client=MagicMock())

        self.assertIn('ssh', str(ctx.exception))
        mock_clean.assert_called_once_with(self.src_files, set())

    @patch('backup.copy_files_s3', return_value=set())
    @patch('backup.run_ssh_backup', return_value={FILENAME})
    def test_s3_upload_failed_keeps_local_file(
        self, _ssh, _s3, _gen, mock_search, mock_clean
    ):
        mock_search.return_value = self.src_files

        with self.assertRaises(Exception) as ctx:
            self.run_backup(['ssh', 's3'], MagicMock(), MagicMock())

        self.assertIn('s3', str(ctx.exception))
        mock_clean.assert_called_once_with(self.src_files, set())

    @patch('backup.copy_files_s3', return_value={FILENAME})
    def test_s3_only(self, mock_s3, _gen, mock_search, mock_clean):
        mock_search.return_value = self.src_files

        self.run_backup(['s3'], s3_client=MagicMock())

        mock_clean.assert_called_once_with(self.src_files, {FILENAME})


class TestCopyFilesS3(unittest.TestCase):
    @patch('backup.upload_file_s3', return_value=True)
    @patch('backup.has_s3_object')
    def test_skips_existing_and_uploads_new(self, mock_has, mock_upload):
        existing = 'backup_20260110_151836.fbk.gz'
        mock_has.side_effect = lambda client, bucket, key: key.endswith(existing)

        actual = backup.copy_files_s3(
            MagicMock(),
            [
                {'filepath': f'/srv/backup/{existing}'},
                {'filepath': f'/srv/backup/{FILENAME}'},
            ],
        )

        self.assertEqual(actual, {existing, FILENAME})
        mock_upload.assert_called_once()
