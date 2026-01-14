import logging
import os
import shlex
from datetime import datetime, timedelta

from scp import SCPClient


def get_datetime(filename):
    splited = filename.split("_")
    date_string = f"{splited[1]} {splited[2].replace('.txt', '')}"
    return datetime.strptime(date_string, "%Y%m%d %H%M%S")


def search_for_backup_files(source_path: str) -> list[dict]:
    """
    Meant to be used on the SSH Client (origin) to check for backup files
    """
    if not source_path.exists():
        raise Exception(f"Directory '{source_path} cannot be found.")

    files_info = []
    for filename in os.listdir(source_path):

        filepath = os.path.join(source_path, filename)
        file_created_time = get_datetime(filename)

        file_metada = {}
        file_metada["filepath"] = filepath
        file_metada["created_at"] = file_created_time

        files_info.append(file_metada)

    return files_info


def get_files_infos(files_list) -> list[dict]:
    if not files_list:
        return []

    files_info = []
    for filename in files_list:
        file_metada = {}
        file_created_time = get_datetime(filename)
        file_metada["filepath"] = filename
        file_metada["created_at"] = file_created_time
        files_info.append(file_metada)

    return files_info


def search_for_files_ssh_server(ssh_client, dest_path) -> list:
    stdin, stdout, stderr = ssh_client.exec_command(f"ls -1 {dest_path}")
    remote_files = stdout.read().decode().splitlines()

    if not remote_files:
        return []

    return remote_files


def generate_n_days_array(n: int) -> list:
    today = datetime.now().date()
    last_n_days = [str(today - timedelta(days=i)) for i in range(n - 1, -1, -1)]
    return last_n_days


def get_files_older_than_n_days(last_n_days: list, files: list[dict]) -> list:
    if not last_n_days:
        raise Exception("Last 'n' days array is required")

    files_older_than_n_days = []
    for _file in files:
        file_date = _file["created_at"].date().strftime("%Y-%m-%d")
        if file_date not in last_n_days:
            files_older_than_n_days.append(_file['filepath'])

    return files_older_than_n_days


def get_files_within_last_n_days(last_n_days: list, files: list[dict]) -> list:
    if not last_n_days:
        raise Exception("Last 'n' days array is required")

    files_within_last_n_days = []
    for _file in files:
        file_date = _file["created_at"].date().strftime("%Y-%m-%d")
        if file_date in last_n_days:
            files_within_last_n_days.append(_file['filepath'])

    return files_within_last_n_days


def copy_files(ssh_client, src_files: list[dict], dest_path: str) -> None:
    if not src_files:
        return None

    dest_files_list = search_for_files_ssh_server(ssh_client, dest_path)

    for src_file in src_files:
        src_filepath = src_file["filepath"]
        src_filename = get_file_name(src_filepath)
        is_backed_up = is_file_backed_up(src_filename, dest_files_list)

        if is_backed_up:
            logging.info(f"[FAIL] file <{src_filename}> was already backed up.")
            continue

        if os.path.isfile(src_filepath):
            dest_filepath = os.path.join(dest_path, src_filename)

            copy_files_scp(ssh_client, src_filepath, dest_filepath)
            logging.info(f"[OK] file <{src_filename}> copied to <{dest_filepath}>")
            logging.info(f"Deleting file <{src_filename}>")  # TODO - implementar permissao para o usuario que executa o script para remover o arquivo


def is_file_backed_up(src_filename: str, dest_files: list) -> bool:
    return src_filename in dest_files


def get_file_name(filepath: str) -> str:
    if not filepath:
        raise Exception("A filepath is required")

    return filepath.rsplit("/", maxsplit=1)[-1]


def list_files_names(files: list[dict]) -> list:
    if not files:
        return []

    files_names_set = set()
    for item in files:
        filepath = item['filepath']
        filename = get_file_name(filepath)

        if filename not in files_names_set:
            files_names_set.add(filename)

    return list(files_names_set)


def ensure_dest_path(ssh_client, ssh_user, dest_path):
    """
    Ensure the creation of the backup folder
    
    :param ssh_client: paramiko SSH Client object reference
    :param bkp_dir: backup directory name
    """
    stdin, stdout, stderr = ssh_client.exec_command(f"ls -1 /home/{ssh_user}")
    remote_files = stdout.read().decode().splitlines()

    bkp_dir = f"{dest_path}".split("/")[-1]
    if bkp_dir in remote_files:
        return

    logging.info("Backup directory cannot be found. Creating...")
    ssh_client.exec_command(f"mkdir {bkp_dir}")
    logging.info("Backup directory created")


def copy_files_scp(ssh_client, src_file, dest_path):
    with SCPClient(ssh_client.get_transport()) as scp:
        scp.put(src_file, remote_path=dest_path)


def delete_remote_file(ssh_client, dest_filepath, dest_filename) -> bool:
    absolute_path = f"{dest_filepath}/{dest_filename}"
    try:
        stdin, stdout, stderr = ssh_client.exec_command(f"rm -f {shlex.quote(absolute_path)}")
        exit_code = stdout.channel.recv_exit_status()

        if exit_code == 0:
            logging.info(f"[OK] Remote file deleted: {dest_filename}")
            return True
        else:
            error_msg = stderr.read().decode().strip()
            logging.error(f"[FAIL] Could not delete {dest_filename}: {error_msg}")
            return False

    except Exception as e:
        logging.error(f"[ERROR] Exception deleting {dest_filename}: {e}")
        return False


def delete_files_older_than_n_days(ssh_client, dest_path, dest_files_older_than_n_days, ):
    logging.info("Deleting older files...")
    for _file_to_delete in dest_files_older_than_n_days:

        if remote_file_exists(ssh_client, dest_path):
            delete_remote_file(ssh_client, dest_path, _file_to_delete)
            logging.info(f" * <{_file_to_delete}> deleted")
        logging.error(f"[FAIL] Remote file not found, keeping local copy: {src_filename}") # TODO - deixar arquivo independente de src ou dest

def remote_file_exists(ssh_client, dest_path: str) -> bool:
    cmd = f"test -f {shlex.quote(dest_path)} && echo 'EXISTS'"
    stdin, stdout, stderr = ssh_client.exec_command(cmd)
    return stdout.read().decode().strip() == "EXISTS"
