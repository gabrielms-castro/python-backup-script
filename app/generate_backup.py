import gzip
import logging
import os
import shutil
import subprocess
import time
from typing import Optional

from logger import log_event
from utils import get_file_size

logger = logging.getLogger(__name__)

# dump tools run in verbose mode; only the end of stderr is useful on failure
STDERR_TAIL_CHARS = 2000


def run_dump_command(
    tool: str, cmd: list, env: dict, output_file: str
) -> bool:
    started = time.monotonic()

    try:
        subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            text=True,
            check=True
        )

        log_event(
            logger, "dump.ok",
            tool=tool,
            file=os.path.basename(output_file),
            size_bytes=get_file_size(output_file),
            duration_s=round(time.monotonic() - started, 3)
        )
        return True

    except subprocess.CalledProcessError as e:
        log_event(
            logger, "dump.failed", logging.ERROR,
            tool=tool,
            file=os.path.basename(output_file),
            returncode=e.returncode,
            stderr_tail=(e.stderr or "")[-STDERR_TAIL_CHARS:],
            duration_s=round(time.monotonic() - started, 3)
        )

    except Exception:
        log_event(
            logger, "dump.failed", logging.ERROR, exc_info=True,
            tool=tool,
            file=os.path.basename(output_file),
            duration_s=round(time.monotonic() - started, 3)
        )

    remove_partial_file(output_file)
    return False


def compress_file(filepath: str) -> Optional[str]:
    gz_filepath = f"{filepath}.gz"
    started = time.monotonic()

    try:
        original_size = get_file_size(filepath)
        with open(filepath, "rb") as src, gzip.open(gz_filepath, "wb") as dst:
            shutil.copyfileobj(src, dst)

        os.remove(filepath)
        log_event(
            logger, "compress.ok",
            file=os.path.basename(gz_filepath),
            size_bytes=get_file_size(gz_filepath),
            original_size_bytes=original_size,
            duration_s=round(time.monotonic() - started, 3)
        )
        return gz_filepath

    except Exception:
        log_event(
            logger, "compress.failed", logging.ERROR, exc_info=True,
            file=os.path.basename(filepath)
        )
        remove_partial_file(gz_filepath)
        return None


def generate_backup(
    strategy,
    output_dir: str,
    timestamp: str,
    compress: bool = True
) -> Optional[str]:
    """
    Generates the database backup file with the engine's dump strategy.
    Returns the final file path or None if the backup failed.
    """
    output_file = os.path.join(
        str(output_dir), f"backup_{timestamp}{strategy.extension}"
    )

    if not strategy.dump(output_file):
        return None

    if compress:
        return compress_file(output_file)

    return output_file


def remove_partial_file(filepath: str) -> None:
    try:
        if os.path.isfile(filepath):
            os.remove(filepath)
            log_event(logger, "partial_file.removed", path=filepath)
    except Exception:
        log_event(
            logger, "partial_file.remove_failed", logging.ERROR, exc_info=True,
            path=filepath
        )
