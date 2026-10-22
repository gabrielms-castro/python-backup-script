import logging
import os
from typing import Optional

from config import NOW
from directory_cleaner import source_dir_cleaner
from generate_backup import generate_backup
from logger import log_event
from utils import get_datetime, get_file_name

logger = logging.getLogger(__name__)


def run_backup(
    src_path,
    dump_strategy,
    storages: list,
    compress: bool = True,
    summary: Optional[dict] = None
):
    """
    Generates the backup with the engine's dump strategy and sends it to
    every configured storage (SSH, S3, ...).
    A source file is only deleted after being backed up on all storages.
    A storage that cannot connect or upload counts as failed.
    The optional `summary` dict is filled with the run results for auditing.
    """
    if summary is None:
        summary = {}

    if not storages:
        raise Exception("No backup target configured.")

    make_backup_file = generate_backup(
        strategy=dump_strategy,
        output_dir=src_path,
        timestamp=NOW.strftime('%Y%m%d_%H%M%S'),
        compress=compress
    )

    if not make_backup_file:
        raise Exception("Backup generation failed.")

    summary["backup_file"] = get_file_name(make_backup_file)

    src_files = search_for_backup_files(src_path)

    summary["target_results"] = {}
    summary["failed_targets"] = []
    backed_up_per_target = [
        _backup_target(storage, src_files, summary) for storage in storages
    ]

    backed_up_filenames = set.intersection(*backed_up_per_target)
    summary["files_backed_up"] = len(backed_up_filenames)
    source_dir_cleaner(src_files, backed_up_filenames)

    if summary["failed_targets"]:
        failed = ", ".join(summary["failed_targets"])
        raise Exception(f"Backup failed on target(s): {failed}")


def _backup_target(storage, src_files, summary) -> set:
    try:
        storage.connect()
        done = storage.upload(src_files)
        storage.apply_retention()
    except Exception:
        log_event(
            logger, "target.failed", logging.ERROR, exc_info=True,
            target=storage.name
        )
        _set_target_result(summary, storage.name, ok=False)
        return set()

    missing = {get_file_name(item["filepath"]) for item in src_files} - done
    if missing:
        log_event(
            logger, "target.failed", logging.ERROR,
            target=storage.name,
            error=f"{len(missing)} file(s) not uploaded"
        )
        _set_target_result(summary, storage.name, ok=False)
    else:
        log_event(logger, "target.ok", target=storage.name, files=len(done))
        _set_target_result(summary, storage.name, ok=True)

    # Partial uploads still count, so those files can be cleaned locally
    return done


def _set_target_result(summary: dict, target: str, ok: bool) -> None:
    summary["target_results"][target] = "ok" if ok else "failed"
    if not ok:
        summary["failed_targets"].append(target)


def search_for_backup_files(source_path: str) -> list[dict]:
    """
    Meant to be used on the SSH Client (origin) to check for backup files
    """
    if not source_path.exists():
        raise Exception(f"Directory '{source_path} cannot be found.")

    files_info = []
    try:
        for filename in os.listdir(source_path):

            filepath = os.path.join(source_path, filename)

            file_created_time = get_datetime(filename)
            if not file_created_time:
                log_event(
                    logger, "source.file.skipped", logging.WARNING,
                    file=filename, reason="no datetime in filename"
                )
                continue

            file_metada = {
                "filepath": filepath,
                "created_at": file_created_time
            }

            files_info.append(file_metada)

    except Exception:
        log_event(
            logger, "source.scan.failed", logging.ERROR, exc_info=True,
            path=source_path
        )

    log_event(
        logger, "source.scan",
        path=source_path,
        count=len(files_info),
        files=[get_file_name(item["filepath"]) for item in files_info]
    )

    return files_info
