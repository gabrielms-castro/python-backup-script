import gzip
import logging
import os
import shutil
import subprocess
from typing import Optional

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
    try:
        subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            text=True,
            check=True
        )

        logging.info(f"[OK] Database dump created ({tool}): {output_file}")
        return True

    except subprocess.CalledProcessError as e:
        logging.error(f"[FAIL] {tool} failed: {e.stderr}")

    except Exception as e:
        logging.error(f"[ERROR] Exception during {tool}: {e}")

    _remove_partial_file(output_file)
    return False


def compress_file(filepath: str) -> Optional[str]:
    gz_filepath = f"{filepath}.gz"

    try:
        with open(filepath, "rb") as src, gzip.open(gz_filepath, "wb") as dst:
            shutil.copyfileobj(src, dst)

        os.remove(filepath)
        logging.info(f"[OK] Backup compressed: {gz_filepath}")
        return gz_filepath

    except Exception as e:
        logging.error(f"[FAIL] Backup could not be compressed {filepath}: {e}")
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
            logging.info(f"Removed partial file: {filepath}")
    except Exception as e:
        logging.error(f"[ERROR] Could not remove partial file {filepath}: {e}")
