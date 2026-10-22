import gzip
import os
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

# app modules use sys.path style imports (from logger import ...)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from generate_backup import (  # noqa: E402
    compress_file,
    generate_backup,
    run_dump_command,
)


class FakeStrategy:
    tool = 'fake_dump'
    extension = '.fbk'

    def __init__(self, success=True):
        self.success = success
        self.output_files = []

    def dump(self, output_file):
        self.output_files.append(output_file)
        return self.success


class TestRunDumpCommand(unittest.TestCase):
    @patch('generate_backup.subprocess.run')
    def test_failure_removes_partial_file(self, mock_run):
        mock_run.side_effect = subprocess.CalledProcessError(
            1, 'gbak', stderr='boom'
        )

        with tempfile.TemporaryDirectory() as tmp:
            output_file = os.path.join(tmp, 'backup_20260111_151836.fbk')
            with open(output_file, 'w') as f:
                f.write('partial')

            actual = run_dump_command('gbak', ['gbak'], {}, output_file)

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
    def test_uses_strategy_extension(self):
        strategy = FakeStrategy()

        actual = generate_backup(
            strategy=strategy,
            output_dir='/srv/backup',
            timestamp='20260111_151836',
            compress=False,
        )

        self.assertEqual(actual, '/srv/backup/backup_20260111_151836.fbk')
        self.assertEqual(strategy.output_files, [actual])

    @patch('generate_backup.compress_file', side_effect=lambda f: f'{f}.gz')
    def test_compress(self, mock_compress):
        actual = generate_backup(
            strategy=FakeStrategy(),
            output_dir='/srv/backup',
            timestamp='20260111_151836',
        )

        self.assertEqual(actual, '/srv/backup/backup_20260111_151836.fbk.gz')
        mock_compress.assert_called_once()

    def test_failed_backup_returns_none(self):
        actual = generate_backup(
            strategy=FakeStrategy(success=False),
            output_dir='/srv/backup',
            timestamp='20260111_151836',
        )

        self.assertIsNone(actual)
