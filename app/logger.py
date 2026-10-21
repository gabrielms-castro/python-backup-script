import json
import logging
import os
import sys
from datetime import datetime

# Attributes every LogRecord has; anything else came from `extra`
_RESERVED_ATTRS = set(
    logging.LogRecord("", 0, "", 0, "", (), None).__dict__
) | {"message", "asctime", "run_id"}

_NOISY_LOGGERS = ("boto3", "botocore", "s3transfer", "urllib3", "paramiko")


def _extra_fields(record: logging.LogRecord) -> dict:
    return {
        key: value
        for key, value in record.__dict__.items()
        if key not in _RESERVED_ATTRS
    }


class JsonFormatter(logging.Formatter):
    """
    One JSON object per line (JSON Lines).
    """

    def format(self, record: logging.LogRecord) -> str:
        ts = datetime.fromtimestamp(record.created).astimezone()

        payload = {
            "ts": ts.isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "run_id": getattr(record, "run_id", None),
            "logger": record.name,
            "event": record.getMessage(),
        }
        payload.update(_extra_fields(record))

        if record.exc_info and record.exc_info[0]:
            exc_type, exc_value, _ = record.exc_info
            payload.setdefault("error", str(exc_value))
            payload["error_type"] = exc_type.__name__
            payload["traceback"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str, ensure_ascii=False)


class ConsoleFormatter(logging.Formatter):
    """
    Short human readable line: ts level [run_id] event key=value ...
    """

    def format(self, record: logging.LogRecord) -> str:  # noqa: PLR6301
        ts = datetime.fromtimestamp(record.created)
        ts = ts.strftime("%Y-%m-%d %H:%M:%S")
        fields = _extra_fields(record)

        if record.exc_info and record.exc_info[0]:
            fields.setdefault("error", str(record.exc_info[1]))

        parts = [
            ts,
            record.levelname,
            f"[{getattr(record, 'run_id', '-')}]",
            record.getMessage(),
        ]
        parts += [
            f"{key}={_console_value(value)}" for key, value in fields.items()
        ]

        return " ".join(parts)


def _console_value(value) -> str:
    if isinstance(value, dict):
        return json.dumps(value, default=str, separators=(",", ":"))

    if isinstance(value, (list, tuple, set)):
        value = ",".join(str(item) for item in value)

    value = str(value)
    if not value or any(char.isspace() for char in value):
        return json.dumps(value, ensure_ascii=False)
    return value


class RunContextFilter(logging.Filter):
    """
    Adds the run_id to every record, grouping all events of one execution.
    """

    def __init__(self, run_id: str):
        super().__init__()
        self.run_id = run_id

    def filter(self, record: logging.LogRecord) -> bool:
        record.run_id = self.run_id
        return True


class ErrorCounter(logging.Handler):
    """
    Counts warnings and errors logged during the run (used on run.finished).
    """

    def __init__(self):
        super().__init__(level=logging.WARNING)
        self.warnings = 0
        self.errors = 0

    def emit(self, record: logging.LogRecord) -> None:
        if record.levelno >= logging.ERROR:
            self.errors += 1
        else:
            self.warnings += 1


def setup_logging(logs_dir, run_id: str, log_date) -> ErrorCounter:
    os.makedirs(logs_dir, exist_ok=True)

    context = RunContextFilter(run_id)

    file_handler = logging.FileHandler(
        os.path.join(str(logs_dir), f"backup_script_{log_date}.jsonl"),
        mode="a",
        encoding="utf-8",
    )
    file_handler.setFormatter(JsonFormatter())
    file_handler.addFilter(context)

    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setFormatter(ConsoleFormatter())
    console_handler.addFilter(context)

    counter = ErrorCounter()

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    for handler in list(root.handlers):
        root.removeHandler(handler)
    for handler in (file_handler, console_handler, counter):
        root.addHandler(handler)

    for name in _NOISY_LOGGERS:
        logging.getLogger(name).setLevel(logging.WARNING)

    return counter


def log_event(
    logger, event: str, level=logging.INFO, exc_info=False, **fields
):
    """
    Logs a structured event. Fields clashing with LogRecord attributes
    (e.g. filename, module) are prefixed with 'field_' instead of raising.
    """
    extra = {
        (f"field_{key}" if key in _RESERVED_ATTRS else key): value
        for key, value in fields.items()
    }
    logger.log(level, event, exc_info=exc_info, extra=extra)
