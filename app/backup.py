import logging
import os
import shlex

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
from s3_client import has_s3_object, make_s3_key, upload_file_s3
from scp import SCPClient
from utils import (
    generate_n_days_array,
    get_datetime,
    get_file_name,
    is_file_backed_up,
    search_for_files_ssh_server,
)


def run_backup(
    src_path,
    backup_days,
    targets: list,
    ssh_client=None,
    dest_path=None,
    s3_client=None
):
    """
    Generates the backup and sends it to every configured target (SSH and/or S3).
    A source file is only deleted after being backed up on all targets.
    A configured target without a client (e.g. SSH connection failed) counts as failed.
    """
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

    src_files = search_for_backup_files(src_path)

    backed_up_per_target = []
    failed_targets = []

    if "ssh" in targets:
        try:
            if not ssh_client:
                raise Exception("SSH client not available")

            backed_up_per_target.append(
                run_ssh_backup(ssh_client, src_files, dest_path, backup_days)
            )
        except Exception as exc:
            logging.error(f"[FAIL] SSH backup failed: {exc}")
            backed_up_per_target.append(set())
            failed_targets.append("ssh")

    if "s3" in targets:
        try:
            if not s3_client:
                raise Exception("S3 client not available")

            s3_done = copy_files_s3(s3_client, src_files)
            backed_up_per_target.append(s3_done)
            if len(s3_done) < len(src_files):
                failed_targets.append("s3")
        except Exception as exc:
            logging.error(f"[FAIL] S3 backup failed: {exc}")
            backed_up_per_target.append(set())
            failed_targets.append("s3")

    backed_up_filenames = set.intersection(*backed_up_per_target)
    source_dir_cleaner(src_files, backed_up_filenames)

    if failed_targets:
        raise Exception(f"Backup failed on target(s): {', '.join(failed_targets)}")


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
            logging.info(f"[SKIP] file <{src_filename}> was already uploaded to S3.")
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
            logging.info(f"[FAIL] file <{src_filename}> was already backed up.")
            continue

        if os.path.isfile(src_filepath):
            dest_filepath = os.path.join(dest_path, src_filename)

            copy_files_scp(ssh_client, src_filepath, dest_filepath)
            logging.info(f"[OK] file <{src_filename}> copied to destination dir <{dest_filepath}>")


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
                logging.warning(f"Skipping file without datetime: {filename}")
                continue

            file_metada = {
                "filepath": filepath,
                "created_at": file_created_time
            }

            files_info.append(file_metada)

    except Exception as exc:
        logging.error(exc)

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
