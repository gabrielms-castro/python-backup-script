import logging
import os
import shlex
import time
from typing import Optional

from config import (
    COMPRESS_BACKUP,
    DB_ENGINE,
    FB_DATABASE,
    FB_GBAK_PATH,
    FB_HOST,
    FB_PASSWORD,
    FB_PORT,
    FB_USER,
    NOW,
    PG_DB_NAME,
    PG_HOST,
    PG_PASSWORD,
    PG_PORT,
    PG_USER,
    S3_BUCKET,
    S3_PREFIX,
    S3_STORAGE_CLASS,
)
from directory_cleaner import remote_dir_cleaner, source_dir_cleaner
from generate_backup import generate_backup
from logger import log_event
from s3_client import has_s3_object, make_s3_key, upload_file_s3
from scp import SCPClient
from utils import (
    generate_n_days_array,
    get_datetime,
    get_file_name,
    get_file_size,
    is_file_backed_up,
    search_for_files_ssh_server,
)

logger = logging.getLogger(__name__)


def run_backup(
    src_path,
    backup_days,
    targets: list,
    ssh_client=None,
    dest_path=None,
    s3_client=None,
    summary: Optional[dict] = None
):
    """
    Generates the backup and sends it to every configured target (SSH and/or S3).
    A source file is only deleted after being backed up on all targets.
    A configured target without a client (e.g. SSH connection failed) counts as failed.
    The optional `summary` dict is filled with the run results for auditing.
    """
    if summary is None:
        summary = {}

    if not targets:
        raise Exception("No backup target configured.")

    make_backup_file = generate_backup(
        engine=DB_ENGINE,
        output_dir=src_path,
        timestamp=NOW.strftime('%Y%m%d_%H%M%S'),
        db_config=get_db_config(DB_ENGINE),
        compress=COMPRESS_BACKUP
    )

    if not make_backup_file:
        raise Exception("Backup generation failed.")

    summary["backup_file"] = get_file_name(make_backup_file)

    src_files = search_for_backup_files(src_path)

    summary["target_results"] = {}
    summary["failed_targets"] = []
    backed_up_per_target = []

    if "ssh" in targets:
        backed_up_per_target.append(_backup_ssh_target(
            ssh_client, src_files, dest_path, backup_days, summary
        ))

    if "s3" in targets:
        backed_up_per_target.append(
            _backup_s3_target(s3_client, src_files, summary)
        )

    backed_up_filenames = set.intersection(*backed_up_per_target)
    summary["files_backed_up"] = len(backed_up_filenames)
    source_dir_cleaner(src_files, backed_up_filenames)

    if summary["failed_targets"]:
        failed = ", ".join(summary["failed_targets"])
        raise Exception(f"Backup failed on target(s): {failed}")


def _backup_ssh_target(ssh_client, src_files, dest_path, backup_days, summary):
    try:
        if not ssh_client:
            raise Exception("SSH client not available")

        ssh_done = run_ssh_backup(
            ssh_client, src_files, dest_path, backup_days
        )
    except Exception:
        log_event(
            logger, "target.failed", logging.ERROR, exc_info=True, target="ssh"
        )
        _set_target_result(summary, "ssh", ok=False)
        return set()

    log_event(logger, "target.ok", target="ssh", files=len(ssh_done))
    _set_target_result(summary, "ssh", ok=True)
    return ssh_done


def _backup_s3_target(s3_client, src_files, summary):
    try:
        if not s3_client:
            raise Exception("S3 client not available")

        s3_done = copy_files_s3(s3_client, src_files)
    except Exception:
        log_event(
            logger, "target.failed", logging.ERROR, exc_info=True, target="s3"
        )
        _set_target_result(summary, "s3", ok=False)
        return set()

    missing = len(src_files) - len(s3_done)
    if missing > 0:
        log_event(
            logger, "target.failed", logging.ERROR,
            target="s3", error=f"{missing} file(s) not uploaded"
        )
        _set_target_result(summary, "s3", ok=False)
    else:
        log_event(logger, "target.ok", target="s3", files=len(s3_done))
        _set_target_result(summary, "s3", ok=True)

    # Partial uploads still count, so those files can be cleaned locally
    return s3_done


def _set_target_result(summary: dict, target: str, ok: bool) -> None:
    summary["target_results"][target] = "ok" if ok else "failed"
    if not ok:
        summary["failed_targets"].append(target)


def run_ssh_backup(ssh_client, src_files, dest_path, backup_days) -> set:
    """
    Copies files to the SSH backup server, cleans older remote files and
    returns the filenames present on the remote directory.
    """
    if not dest_path:
        raise Exception("DEST_PATH is required for the SSH target")

    ensure_dest_path(ssh_client, dest_path)

    copy_files(ssh_client, src_files, dest_path)

    last_n_days_array = generate_n_days_array(backup_days)
    remote_dir_cleaner(ssh_client, last_n_days_array, dest_path)

    return set(search_for_files_ssh_server(ssh_client, dest_path))


def copy_files_s3(s3_client, src_files: list[dict]) -> set:
    """
    Uploads files to S3 and returns the filenames confirmed on the bucket.
    Retention on S3 is handled by the bucket lifecycle rule.
    """
    uploaded = set()

    for src_file in src_files:
        src_filepath = src_file["filepath"]
        src_filename = get_file_name(src_filepath)
        key = make_s3_key(S3_PREFIX, src_filename)

        if has_s3_object(s3_client, S3_BUCKET, key):
            log_event(
                logger, "s3.upload.skipped",
                file=src_filename, bucket=S3_BUCKET, key=key,
                reason="already uploaded"
            )
            uploaded.add(src_filename)
            continue

        if upload_file_s3(s3_client, src_filepath, S3_BUCKET, key, S3_STORAGE_CLASS):
            uploaded.add(src_filename)

    return uploaded


def get_db_config(engine: str) -> dict:
    if engine == "firebird":
        return {
            "gbak_path": FB_GBAK_PATH,
            "host": FB_HOST,
            "port": FB_PORT,
            "database": FB_DATABASE,
            "user": FB_USER,
            "password": FB_PASSWORD,
        }

    return {
        "host": PG_HOST,
        "port": PG_PORT,
        "database": PG_DB_NAME,
        "user": PG_USER,
        "password": PG_PASSWORD,
    }


def copy_files(ssh_client, src_files: list[dict], dest_path: str) -> None:
    if not src_files:
        return None

    dest_files_list = search_for_files_ssh_server(ssh_client, dest_path)

    for src_file in src_files:
        src_filepath = src_file["filepath"]
        src_filename = get_file_name(src_filepath)

        if is_file_backed_up(src_filename, dest_files_list):
            log_event(
                logger, "ssh.copy.skipped",
                file=src_filename, reason="already on backup server"
            )
            continue

        if os.path.isfile(src_filepath):
            dest_filepath = os.path.join(dest_path, src_filename)
            started = time.monotonic()

            try:
                copy_files_scp(ssh_client, src_filepath, dest_filepath)
            except Exception:
                log_event(
                    logger, "ssh.copy.failed", logging.ERROR, exc_info=True,
                    file=src_filename, dest=dest_filepath
                )
                raise

            log_event(
                logger, "ssh.copy.ok",
                file=src_filename,
                dest=dest_filepath,
                size_bytes=get_file_size(src_filepath),
                duration_s=round(time.monotonic() - started, 3)
            )


def copy_files_scp(ssh_client, src_file, dest_path):
    with SCPClient(ssh_client.get_transport()) as scp:
        scp.put(src_file, remote_path=dest_path)


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


def ensure_dest_path(ssh_client, dest_path):
    """
    Ensure the creation of the backup folder
    """
    cmd = f"mkdir -p {shlex.quote(str(dest_path))}"
    stdin, stdout, stderr = ssh_client.exec_command(cmd)
    exit_code = stdout.channel.recv_exit_status()

    if exit_code != 0:
        error_msg = stderr.read().decode().strip()
        raise Exception(f"Backup directory '{dest_path}' could not be created: {error_msg}")
