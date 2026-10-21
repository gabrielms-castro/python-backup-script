import os
import sys
import unittest
from unittest.mock import MagicMock, patch

import requests

# app modules use sys.path style imports (from logger import ...)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from healthcheck import MAX_BODY_CHARS, ping  # noqa: E402

URL = 'https://hc-ping.com/0000-check-uuid'


@patch('healthcheck.requests.post')
@patch('healthcheck.requests.get')
class TestPing(unittest.TestCase):
    def test_start(self, mock_get, mock_post):
        self.assertTrue(ping(URL, 'start'))

        mock_get.assert_called_once_with(f'{URL}/start', timeout=10)
        mock_post.assert_not_called()

    def test_success_uses_base_url(self, mock_get, _post):
        ping(f'{URL}/', '')

        mock_get.assert_called_once_with(URL, timeout=10)

    def test_fail_posts_body(self, _get, mock_post):
        self.assertTrue(ping(URL, 'fail', body='erro'))

        mock_post.assert_called_once_with(
            f'{URL}/fail', data=b'erro', timeout=10
        )

    def test_body_is_truncated(self, _get, mock_post):
        ping(URL, 'fail', body='x' * (MAX_BODY_CHARS + 500))

        self.assertEqual(
            len(mock_post.call_args.kwargs['data']), MAX_BODY_CHARS
        )

    def test_network_error_does_not_raise(self, mock_get, _post):
        mock_get.side_effect = requests.ConnectionError('down')

        self.assertFalse(ping(URL, 'start'))

    def test_error_log_does_not_leak_check_uuid(self, mock_get, _post):
        mock_get.side_effect = requests.ConnectionError(
            'Max retries exceeded with url: /0000-check-uuid/start'
        )

        with self.assertLogs('healthcheck', level='WARNING') as logs:
            ping(URL, 'start')

        record = logs.records[0]
        self.assertNotIn('0000-check-uuid', record.error)
        self.assertIn('<redacted>', record.error)
        self.assertFalse(record.exc_info)

    def test_http_error_returns_false(self, mock_get, _post):
        response = MagicMock()
        response.raise_for_status.side_effect = requests.HTTPError('404')
        mock_get.return_value = response

        self.assertFalse(ping(URL, 'start'))

    def test_disabled_without_url(self, mock_get, mock_post):
        self.assertFalse(ping(None, 'start'))
        self.assertFalse(ping('', 'fail', body='x'))

        mock_get.assert_not_called()
        mock_post.assert_not_called()
