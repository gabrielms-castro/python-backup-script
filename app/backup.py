import logging
import os

from directory_cleaner import remote_dir_cleaner, source_dir_cleaner
from generate_backup import pg_dump_database
from scp import SCPClient
from utils import (
    generate_n_days_array,
    get_datetime,
    get_file_name,
    is_file_backed_up,
    search_for_files_ssh_server,
)

from config import NOW, PG_DB_NAME, PG_HOST, PG_PASSWORD, PG_PORT, PG_USER


def run_backup(ssh_client, ssh_user, src_path, dest_path, backup_days):
    ensure_dest_path(ssh_client, ssh_user, dest_path)

    last_n_days_array = generate_n_days_array(backup_days)
    make_backup_file = pg_dump_database(
        host=PG_HOST,
        port=PG_PORT,
        database=PG_DB_NAME,
        user=PG_USER,
        password=PG_PASSWORD,
        output_file=f"{src_path}/backup_{NOW.strftime("%Y%m%d_%H%M%S")}.sql"
    )
    
    if not make_backup_file:
        raise Exception("Backup generation failed.")
    
    src_files = search_for_backup_files(src_path)

    copy_files(ssh_client, src_files, dest_path)

    remote_dir_cleaner(ssh_client, last_n_days_array, dest_path)

    source_dir_cleaner(ssh_client, src_files, dest_path)


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


def ensure_dest_path(ssh_client, ssh_user, dest_path):
    """
    Ensure the creation of the backup folder
    """
    stdin, stdout, stderr = ssh_client.exec_command(f"ls -1 /home/{ssh_user}")
    remote_files = stdout.read().decode().splitlines()

    bkp_dir = f"{dest_path}".split("/")[-1]
    if bkp_dir in remote_files:
        return

    logging.info("Backup directory cannot be found. Creating...")
    ssh_client.exec_command(f"mkdir {bkp_dir}")
    logging.info("Backup directory created")
