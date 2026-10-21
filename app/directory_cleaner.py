import logging
import os
import shlex

from logger import log_event
from utils import (
    get_file_name,
    get_files_infos,
    get_files_older_than_n_days,
    is_file_backed_up,
    make_dest_file_abs_path,
    search_for_files_ssh_server,
)

logger = logging.getLogger(__name__)


def remote_delete_file(ssh_client, dest_filepath, dest_filename) -> bool:
    absolute_path = make_dest_file_abs_path(dest_filepath, dest_filename)

    if not has_remote_file(ssh_client, absolute_path):
        log_event(
            logger, "remote.file.delete_failed", logging.ERROR,
            file=dest_filename, path=absolute_path, error="remote file not found"
        )
        return False

    try:
        stdin, stdout, stderr = ssh_client.exec_command(f"rm -f {shlex.quote(absolute_path)}")
        exit_code = stdout.channel.recv_exit_status()

        if exit_code == 0:
            log_event(logger, "remote.file.deleted", file=dest_filename, path=absolute_path)
            return True

        error_msg = stderr.read().decode().strip()
        log_event(
            logger, "remote.file.delete_failed", logging.ERROR,
            file=dest_filename, path=absolute_path, exit_code=exit_code, error=error_msg
        )
        return False

    except Exception:
        log_event(
            logger, "remote.file.delete_failed", logging.ERROR, exc_info=True,
            file=dest_filename, path=absolute_path
        )
        return False


def remote_delete_older_files(ssh_client, dest_path, dest_files_older_than_n_days):
    """
    Checks remote files to be deleted
    """
    log_event(
        logger, "remote.cleanup.started",
        path=dest_path,
        count=len(dest_files_older_than_n_days),
        files=dest_files_older_than_n_days
    )

    for _file_to_delete in dest_files_older_than_n_days:
        remote_delete_file(ssh_client, dest_path, _file_to_delete)


def has_remote_file(ssh_client, dest_path: str) -> bool:
    cmd = f"test -f {shlex.quote(dest_path)} && echo 'EXISTS'"
    stdin, stdout, stderr = ssh_client.exec_command(cmd)
    return stdout.read().decode().strip() == "EXISTS"


def remote_dir_cleaner(ssh_client, last_n_days_array, dest_path):
    """
    Cleans up older files on the backup server.
    Destination server (aka Backup Server) must be cleaned. This consists on deleting files older than N days.
    """
    dest_files_list = search_for_files_ssh_server(ssh_client, dest_path)
    dest_files_infos = get_files_infos(dest_files_list)
    dest_files_older_than_n_days = get_files_older_than_n_days(last_n_days_array, dest_files_infos)
    remote_delete_older_files(ssh_client, dest_path, dest_files_older_than_n_days)


def source_delete_file(src_filepath):
    filename = get_file_name(src_filepath)
    try:
        os.remove(src_filepath)
        log_event(logger, "source.file.deleted", file=filename, path=src_filepath)
    except Exception:
        log_event(
            logger, "source.file.delete_failed", logging.ERROR, exc_info=True,
            file=filename, path=src_filepath
        )


def source_dir_cleaner(src_files, backed_up_filenames: set):
    """
    Deletes files after backing up on the destination targets.
    Source directory must be cleaned only if the file was successfully backed up
    on every active target (backed_up_filenames).
    """

    for source_file in src_files:
        source_path = source_file["filepath"]
        filename = get_file_name(source_path)

        if is_file_backed_up(filename, backed_up_filenames):
            source_delete_file(source_path)
        else:
            log_event(
                logger, "source.file.kept",
                file=filename, reason="not confirmed on every target"
            )
