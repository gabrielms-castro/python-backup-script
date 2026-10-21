import json
import logging
import os
import sys
import unittest
from datetime import datetime
from pathlib import Path

# app modules use sys.path style imports (from utils import ...)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from logger import (  # noqa: E402
    ConsoleFormatter,
    ErrorCounter,
    JsonFormatter,
    RunContextFilter,
    log_event,
)
from main import get_run_status  # noqa: E402


class CaptureHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.records = []

    def emit(self, record):
        self.records.append(record)


class LoggerTestCase(unittest.TestCase):
    def setUp(self):
        self.logger = logging.getLogger(f'test.{self.id()}')
        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False
        self.handler = CaptureHandler()
        self.handler.addFilter(RunContextFilter('abc12345'))
        self.logger.addHandler(self.handler)

    def tearDown(self):
        self.logger.removeHandler(self.handler)

    def json_line(self, index=-1):
        line = JsonFormatter().format(self.handler.records[index])
        return json.loads(line)


class TestJsonFormatter(LoggerTestCase):
    def test_base_fields_and_extras(self):
        log_event(self.logger, 's3.upload.ok', file='a.gz', size_bytes=10)

        actual = self.json_line()

        self.assertEqual(actual['event'], 's3.upload.ok')
        self.assertEqual(actual['level'], 'INFO')
        self.assertEqual(actual['run_id'], 'abc12345')
        self.assertEqual(actual['file'], 'a.gz')
        self.assertEqual(actual['size_bytes'], 10)
        self.assertIn('ts', actual)
        datetime.fromisoformat(actual['ts'])

    def test_exception_fields(self):
        try:
            raise ValueError('boom')
        except ValueError:
            log_event(
                self.logger, 'target.failed', logging.ERROR,
                exc_info=True, target='ssh'
            )

        actual = self.json_line()

        self.assertEqual(actual['level'], 'ERROR')
        self.assertEqual(actual['error'], 'boom')
        self.assertEqual(actual['error_type'], 'ValueError')
        self.assertIn('Traceback', actual['traceback'])

    def test_non_serializable_values_become_strings(self):
        log_event(
            self.logger, 'run.started',
            path=Path('/srv/backup'), when=datetime(2026, 1, 1)
        )

        actual = self.json_line()

        self.assertEqual(actual['path'], '/srv/backup')
        self.assertEqual(actual['when'], '2026-01-01 00:00:00')


class TestLogEvent(LoggerTestCase):
    def test_reserved_keys_are_prefixed(self):
        log_event(self.logger, 'x', filename='a.gz', module='m')

        actual = self.json_line()

        self.assertEqual(actual['field_filename'], 'a.gz')
        self.assertEqual(actual['field_module'], 'm')


class TestConsoleFormatter(LoggerTestCase):
    def test_human_readable_line(self):
        log_event(
            self.logger, 'target.failed', logging.ERROR,
            target='ssh', error='SSH client not available', files=['a', 'b']
        )

        actual = ConsoleFormatter().format(self.handler.records[-1])

        self.assertIn('ERROR [abc12345] target.failed target=ssh', actual)
        self.assertIn('error="SSH client not available"', actual)
        self.assertIn('files=a,b', actual)


class TestErrorCounter(LoggerTestCase):
    def test_counts_warnings_and_errors(self):
        counter = ErrorCounter()
        self.logger.addHandler(counter)

        log_event(self.logger, 'a')
        log_event(self.logger, 'b', logging.WARNING)
        log_event(self.logger, 'c', logging.ERROR)
        log_event(self.logger, 'd', logging.ERROR)

        self.logger.removeHandler(counter)
        self.assertEqual(counter.warnings, 1)
        self.assertEqual(counter.errors, 2)


class TestGetRunStatus(unittest.TestCase):
    def test_success(self):
        self.assertEqual(get_run_status(0, {}), 'success')

    def test_partial(self):
        summary = {'target_results': {'ssh': 'failed', 's3': 'ok'}}
        self.assertEqual(get_run_status(1, summary), 'partial')

    def test_failed(self):
        summary = {'target_results': {'ssh': 'failed'}}
        self.assertEqual(get_run_status(1, summary), 'failed')
        self.assertEqual(get_run_status(1, {}), 'failed')
