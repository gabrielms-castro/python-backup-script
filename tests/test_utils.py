import datetime
import unittest

from app.utils import (
    get_datetime,
    get_file_name,
    get_files_older_than_n_days,
    get_files_within_last_n_days,
)

"""
Tests were written with .txt extension but this will be used to parse .sql documents.
"""


class TestUtils(unittest.TestCase):
    def test_get_files_older_than_n_days_1(self):
        """
        Testing with output
        """
        files_dict = [
            {'filepath': '/srv/test_app/backup/file2_20260111_151836.txt', 'created_at': datetime.datetime(2026, 1, 11, 15, 18, 36)},
            {'filepath': '/srv/test_app/backup/file2_20260112_151836.txt', 'created_at': datetime.datetime(2026, 1, 12, 15, 18, 36)},
            {'filepath': '/srv/test_app/backup/file2_20260113_151836.txt', 'created_at': datetime.datetime(2026, 1, 13, 15, 18, 36)},
            {'filepath': '/srv/test_app/backup/file2_20260114_151836.txt', 'created_at': datetime.datetime(2026, 1, 14, 15, 18, 36)},
        ]

        last_n_days = [
            '2026-01-11',
            '2026-01-12',
            '2026-01-13',
        ]

        actual = get_files_older_than_n_days(
            last_n_days=last_n_days,
            files=files_dict
        )

        expected = [
            '/srv/test_app/backup/file2_20260114_151836.txt'
        ]

        self.assertEqual(actual, expected)

    def test_get_files_older_than_n_days_2(self):
        """
        Testing with no output
        """
        files_dict = [
            {'filepath': '/srv/test_app/backup/file2_20260111_151836.txt', 'created_at': datetime.datetime(2026, 1, 11, 15, 18, 36)},
            {'filepath': '/srv/test_app/backup/file2_20260112_151836.txt', 'created_at': datetime.datetime(2026, 1, 12, 15, 18, 36)},
            {'filepath': '/srv/test_app/backup/file2_20260113_151836.txt', 'created_at': datetime.datetime(2026, 1, 13, 15, 18, 36)},
        ]

        last_n_days = [
            '2026-01-11',
            '2026-01-12',
            '2026-01-13',
        ]

        actual = get_files_older_than_n_days(
            last_n_days=last_n_days,
            files=files_dict
        )

        expected = []

        self.assertEqual(actual, expected)

    def test_get_files_older_than_n_days_3(self):
        """
        Testing with no last_n_days array
        """
        files_dict = [
            {'filepath': '/srv/test_app/backup/file2_20260111_151836.txt', 'created_at': datetime.datetime(2026, 1, 11, 15, 18, 36)},
            {'filepath': '/srv/test_app/backup/file2_20260112_151836.txt', 'created_at': datetime.datetime(2026, 1, 12, 15, 18, 36)},
            {'filepath': '/srv/test_app/backup/file2_20260113_151836.txt', 'created_at': datetime.datetime(2026, 1, 13, 15, 18, 36)},
        ]

        last_n_days = []

        self.assertRaises(
            Exception,
            get_files_older_than_n_days,
            last_n_days=last_n_days,
            files=files_dict
        )

    def test_get_files_within_last_n_days_1(self):
        """
        Testing with output
        """
        files_dict = [
            {'filepath': '/srv/test_app/backup/file1_20260111_151836.txt', 'created_at': datetime.datetime(2026, 1, 11, 15, 18, 36)},
            {'filepath': '/srv/test_app/backup/file2_20260112_151836.txt', 'created_at': datetime.datetime(2026, 1, 12, 15, 18, 36)},
            {'filepath': '/srv/test_app/backup/file3_20260113_151836.txt', 'created_at': datetime.datetime(2026, 1, 13, 15, 18, 36)},
            {'filepath': '/srv/test_app/backup/file4_20260114_151836.txt', 'created_at': datetime.datetime(2026, 1, 14, 15, 18, 36)},
        ]

        last_n_days = [
            '2026-01-11',
            '2026-01-12',
            '2026-01-13',
        ]

        actual = get_files_within_last_n_days(
            last_n_days=last_n_days,
            files=files_dict
        )

        expected = [
            '/srv/test_app/backup/file1_20260111_151836.txt',
            '/srv/test_app/backup/file2_20260112_151836.txt',
            '/srv/test_app/backup/file3_20260113_151836.txt'
        ]

        self.assertEqual(actual, expected)

    def test_get_files_within_last_n_days_2(self):
        """
        Testing with no output
        """
        files_dict = [
            {'filepath': '/srv/test_app/backup/file1_20260110_151836.txt', 'created_at': datetime.datetime(2026, 1, 10, 15, 18, 36)},
            {'filepath': '/srv/test_app/backup/file2_20260109_151836.txt', 'created_at': datetime.datetime(2026, 1, 9, 15, 18, 36)},
            {'filepath': '/srv/test_app/backup/file3_20260108_151836.txt', 'created_at': datetime.datetime(2026, 1, 8, 15, 18, 36)},
        ]

        last_n_days = [
            '2026-01-11',
            '2026-01-12',
            '2026-01-13',
        ]

        actual = get_files_within_last_n_days(
            last_n_days=last_n_days,
            files=files_dict
        )

        expected = []

        self.assertEqual(actual, expected)

    def test_get_files_within_last_n_days_3(self):
        """
        Testing with no last_n_days array
        """
        files_dict = [
            {'filepath': '/srv/test_app/backup/file1_20260111_151836.txt', 'created_at': datetime.datetime(2026, 1, 11, 15, 18, 36)},
            {'filepath': '/srv/test_app/backup/file2_20260112_151836.txt', 'created_at': datetime.datetime(2026, 1, 12, 15, 18, 36)},
            {'filepath': '/srv/test_app/backup/file3_20260113_151836.txt', 'created_at': datetime.datetime(2026, 1, 13, 15, 18, 36)},
        ]

        last_n_days = []

        self.assertRaises(
            Exception,
            get_files_within_last_n_days,
            last_n_days=last_n_days,
            files=files_dict
        )

    def test_get_file_name(self):
        """
        Test get_file_name() with output
        """
        filepath = '/srv/test_app/backup/file1_20260111_151836.txt'
        actual = get_file_name(filepath)
        expected = "file1_20260111_151836.txt"
        self.assertEqual(actual, expected)

    def test_get_files_older_than_n_days_skips_unknown_dates(self):
        """
        Files without a parseable datetime must be ignored
        """
        files_dict = [
            {'filepath': 'notes.txt', 'created_at': None},
            {'filepath': 'backup_20260110_151836.fbk.gz', 'created_at': datetime.datetime(2026, 1, 10, 15, 18, 36)},
        ]

        actual = get_files_older_than_n_days(
            last_n_days=['2026-01-11'],
            files=files_dict
        )

        self.assertEqual(actual, ['backup_20260110_151836.fbk.gz'])

    def test_get_datetime_extensions(self):
        """
        get_datetime() must handle every backup extension
        """
        expected = datetime.datetime(2026, 1, 11, 15, 18, 36)
        for filename in [
            'backup_20260111_151836.sql',
            'backup_20260111_151836.sql.gz',
            'backup_20260111_151836.fbk',
            'backup_20260111_151836.fbk.gz',
        ]:
            with self.subTest(filename=filename):
                self.assertEqual(get_datetime(filename), expected)

    def test_get_datetime_invalid(self):
        self.assertIsNone(get_datetime('notes.txt'))
        self.assertIsNone(get_datetime('backup_2026_abc.fbk'))
