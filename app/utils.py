import logging
from datetime import datetime, timedelta


def get_datetime(filename):
    splited = filename.split("_")

    if len(splited) < 3:
        return None

    try:
        date_string = f"{splited[1]} {splited[2].replace('.sql', '')}"
        return datetime.strptime(date_string, "%Y%m%d %H%M%S")

    except ValueError as exc:
        logging.warning(f"Invalid datetime format in {filename}: {exc}")
        return None


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


def search_for_files_ssh_server(ssh_client, dest_path) -> list:
    stdin, stdout, stderr = ssh_client.exec_command(f"ls -1 {dest_path}")
    remote_files = stdout.read().decode().splitlines()

    if not remote_files:
        return []

    return remote_files


def make_dest_file_abs_path(dest_path, remote_filename):
    return f"{dest_path}/{remote_filename}"


def is_file_backed_up(src_filename: str, dest_files: list) -> bool:
    return src_filename in dest_files
