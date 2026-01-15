import logging
import os
import shlex

from utils import (
    get_file_name,
    get_files_infos,
    get_files_older_than_n_days,
    is_file_backed_up,
    make_dest_file_abs_path,
    search_for_files_ssh_server,
)


def remote_delete_file(ssh_client, dest_filepath, dest_filename) -> bool:
    absolute_path = make_dest_file_abs_path(dest_filepath, dest_filename)

    if not has_remote_file(ssh_client, absolute_path):
        logging.error(f"[FAIL] Remote file not found, keeping local copy: {absolute_path}")
        return

    try:
        stdin, stdout, stderr = ssh_client.exec_command(f"rm -f {shlex.quote(absolute_path)}")
        exit_code = stdout.channel.recv_exit_status()

        if exit_code == 0:
            logging.info(f"[OK] Remote file deleted: {dest_filename}")
            return
        else:
            error_msg = stderr.read().decode().strip()
            logging.error(f"[FAIL] Remote file could not be deleted {dest_filename}: {error_msg}")
            return

    except Exception as e:
        logging.error(f"[ERROR] Exception deleting {dest_filename}: {e}")
        return


def remote_delete_older_files(ssh_client, dest_path, dest_files_older_than_n_days):
    """
    Checks remote files to be deleted
    """
    logging.info("Deleting older files...")

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
    try:
        filename = get_file_name(src_filepath)
        os.remove(src_filepath)
        logging.info(f"\t[OK] source file deleted: {filename}")
    except Exception:
        logging.error(f"\t[FAIL] Source file cannot be deleted: {src_filepath["filepath"]}")


def source_dir_cleaner(ssh_client, src_files, dest_path):
    """
    Deletes files after backing up on the destination server.
    Source directory must be cleaned if the file was successfully backed up.
    """

    dest_files_list = search_for_files_ssh_server(ssh_client, dest_path)

    for source_file in src_files:
        source_path = source_file.get("filepath", "falhei papai")
        filename = get_file_name(source_path)

        if is_file_backed_up(filename, dest_files_list):
            logging.info(f"Deleting backed up source file: {source_path}")
            source_delete_file(source_path)
