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

# gbak/pg_dump run in verbose mode; only the end of stderr is useful on failure
STDERR_TAIL_CHARS = 2000

BACKUP_EXTENSIONS = {
    "postgres": ".sql",
    "firebird": ".fbk",
}


def pg_dump_database(
    host: str,
    port: int,
    database: str,
    user: str,
    password: str,
    output_file: str
) -> bool:

    cmd = [
        "pg_dump",
        f"--host={host}",
        f"--port={port}",
        f"--username={user}",
        f"--dbname={database}",
        f"--file={output_file}",
        "--format=plain",
        "--verbose"
    ]

    env = {**os.environ, "PGPASSWORD": password or ""}

    return _run_dump_command("pg_dump", cmd, env, output_file)


def gbak_backup_database(
    gbak_path: str,
    host: str,
    port: int,
    database: str,
    user: str,
    password: str,
    output_file: str
) -> bool:

    cmd = [
        gbak_path,
        "-b",
        "-v",
        "-g",
        f"{host}/{port}:{database}",
        output_file
    ]

    # Credentials via env so the password does not show up in `ps`
    env = {**os.environ, "ISC_USER": user or "", "ISC_PASSWORD": password or ""}

    return _run_dump_command("gbak", cmd, env, output_file)


def _run_dump_command(tool: str, cmd: list, env: dict, output_file: str) -> bool:
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

    _remove_partial_file(output_file)
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
        _remove_partial_file(gz_filepath)
        return None


def generate_backup(
    engine: str,
    output_dir: str,
    timestamp: str,
    db_config: dict,
    compress: bool = True
) -> Optional[str]:
    """
    Generates the database backup file for the given engine.
    Returns the final file path or None if the backup failed.
    """
    if engine not in BACKUP_EXTENSIONS:
        raise ValueError(f"Unsupported DB_ENGINE: '{engine}'")

    output_file = os.path.join(
        str(output_dir), f"backup_{timestamp}{BACKUP_EXTENSIONS[engine]}"
    )

    if engine == "postgres":
        success = pg_dump_database(output_file=output_file, **db_config)
    else:
        success = gbak_backup_database(output_file=output_file, **db_config)

    if not success:
        return None

    if compress:
        return compress_file(output_file)

    return output_file


def _remove_partial_file(filepath: str) -> None:
    try:
        if os.path.isfile(filepath):
            os.remove(filepath)
            log_event(logger, "partial_file.removed", path=filepath)
    except Exception:
        log_event(
            logger, "partial_file.remove_failed", logging.ERROR, exc_info=True,
            path=filepath
        )
