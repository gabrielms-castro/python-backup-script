import os
import sys
import unittest
from unittest.mock import MagicMock

from botocore.exceptions import ClientError

# app modules use sys.path style imports (from logger import ...)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from app.s3_client import (  # noqa: E402
    has_s3_object,
    make_s3_key,
    upload_file_s3,
)


def client_error(code):
    return ClientError({'Error': {'Code': code}}, 'HeadObject')


class TestMakeS3Key(unittest.TestCase):
    def test_make_s3_key(self):
        filename = 'backup_20260111_151836.fbk.gz'
        cases = [
            ('', filename),
            (None, filename),
            ('backups/firebird', f'backups/firebird/{filename}'),
            ('backups/firebird/', f'backups/firebird/{filename}'),
            ('/backups/firebird/', f'backups/firebird/{filename}'),
        ]
        for prefix, expected in cases:
            with self.subTest(prefix=prefix):
                self.assertEqual(make_s3_key(prefix, filename), expected)


class TestHasS3Object(unittest.TestCase):
    def test_object_exists(self):
        s3_client = MagicMock()

        self.assertTrue(has_s3_object(s3_client, 'bucket', 'key'))
        s3_client.head_object.assert_called_once_with(
            Bucket='bucket', Key='key'
        )

    def test_object_missing(self):
        """
        Without s3:ListBucket a missing object returns 403
        """
        for code in ('404', '403'):
            with self.subTest(code=code):
                s3_client = MagicMock()
                s3_client.head_object.side_effect = client_error(code)

                self.assertFalse(has_s3_object(s3_client, 'bucket', 'key'))

    def test_unexpected_error_is_raised(self):
        s3_client = MagicMock()
        s3_client.head_object.side_effect = client_error('500')

        self.assertRaises(
            ClientError, has_s3_object, s3_client, 'bucket', 'key'
        )


class TestUploadFileS3(unittest.TestCase):
    def test_upload_ok(self):
        s3_client = MagicMock()

        actual = upload_file_s3(
            s3_client, '/srv/backup/f.fbk.gz', 'bucket', 'p/f.fbk.gz', 'STANDARD'
        )

        self.assertTrue(actual)
        s3_client.upload_file.assert_called_once_with(
            '/srv/backup/f.fbk.gz',
            'bucket',
            'p/f.fbk.gz',
            ExtraArgs={
                'StorageClass': 'STANDARD',
                'ServerSideEncryption': 'AES256',
            },
        )

    def test_upload_fail(self):
        s3_client = MagicMock()
        s3_client.upload_file.side_effect = client_error('AccessDenied')

        actual = upload_file_s3(
            s3_client, '/srv/backup/f.fbk.gz', 'bucket', 'p/f.fbk.gz', 'STANDARD'
        )

        self.assertFalse(actual)
