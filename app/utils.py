import logging
import os
import shutil
from datetime import datetime, timedelta


def get_datetime(filename):
    splited = filename.split("_")
    date_string = f"{splited[1]} {splited[2].replace(".txt", "")}"
    return datetime.strptime(date_string, "%Y%m%d %H%M%S")


def search_for_files(_dir) -> list[dict]:
    if not _dir.exists():
        raise Exception(f"Directory '{_dir} cannot be found.")

    files_info = []
    for filename in os.listdir(_dir):

        filepath = os.path.join(_dir, filename)
        file_created_time = get_datetime(filename)

        file_metada = {}
        file_metada["filepath"] = filepath
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


def copy_files_local(src_path: str, dest_path: str) -> None:
    source_files = search_for_files(src_path)
    if not source_files:
        return None

    os.makedirs(dest_path, exist_ok=True)
    dest_files = search_for_files(dest_path)
    dest_files_list = list_files_names(dest_files)

    for src_file in source_files:
        abs_filepath = src_file["filepath"]
        filename = get_file_name(abs_filepath)
        is_backed_up = is_file_backed_up(filename, dest_files_list)

        if is_backed_up:
            logging.info(f" -> {filename} already backed up.")
            continue

        if os.path.isfile(abs_filepath):
            dest_filepath = os.path.join(dest_path, filename)
            shutil.copy(src=abs_filepath, dst=dest_filepath)
            logging.info(f" * Copied {filename} to {dest_filepath}")


def is_file_backed_up(filename: str, dest_files: list) -> bool:
    return filename in dest_files


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
