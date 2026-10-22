import logging
import os
import shlex
import time

from directory_cleaner import remote_dir_cleaner
from logger import log_event
from scp import SCPClient
from ssh_client import create_ssh_client
from storages.base import StorageAdapter
from utils import (
    generate_n_days_array,
    get_file_name,
    get_file_size,
    is_file_backed_up,
    search_for_files_ssh_server,
)

logger = logging.getLogger(__name__)


class SSHStorage(StorageAdapter):
    """
    Backup server reached via SSH/SCP. Retention (BACKUP_DAYS) is done here.
    """

    name = "ssh"

    def __init__(
        self, server, port, user, key_filepath, dest_path, backup_days
    ):
        self.server = server
        self.port = port
        self.user = user
        self.key_filepath = key_filepath
        self.dest_path = dest_path
        self.backup_days = backup_days
        self.client = None

    def connect(self) -> None:
        if not self.dest_path:
            raise Exception("DEST_PATH is required for the SSH target")

        self.client = create_ssh_client(
            server=self.server,
            port=self.port,
            user=self.user,
            key_filepath=self.key_filepath
        )

    def upload(self, src_files: list[dict]) -> set:
        if not self.client:
            raise Exception("SSH client not available")

        ensure_dest_path(self.client, self.dest_path)
        copy_files(self.client, src_files, self.dest_path)

        return set(search_for_files_ssh_server(self.client, self.dest_path))

    def apply_retention(self) -> None:
        last_n_days_array = generate_n_days_array(self.backup_days)
        remote_dir_cleaner(self.client, last_n_days_array, self.dest_path)

    def close(self) -> None:
        if self.client:
            self.client.close()
            self.client = None
            log_event(logger, "ssh.connection.closed")


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


def ensure_dest_path(ssh_client, dest_path):
    """
    Ensure the creation of the backup folder
    """
    cmd = f"mkdir -p {shlex.quote(str(dest_path))}"
    stdin, stdout, stderr = ssh_client.exec_command(cmd)
    exit_code = stdout.channel.recv_exit_status()

    if exit_code != 0:
        error_msg = stderr.read().decode().strip()
        raise Exception(
            f"Backup directory '{dest_path}' could not be created: "
            f"{error_msg}"
        )
