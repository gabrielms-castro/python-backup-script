import os

from datetime import datetime, timedelta

def get_datetime(filename):
    splited = filename.split("_")
    date_string = f"{splited[1]} {splited[2].replace(".txt", "")}"
    return datetime.strptime(date_string, "%Y%m%d %H%M%S")

def search_for_files(src):
    if not src.exists():
        raise Exception(f"Directory '{src} cannot be found.")

    files_info = []
    for filename in os.listdir(src):

        filepath = os.path.join(src, filename)
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
    
def is_file_backed_up(filepath, dest) -> bool:
    # for checking if the file is already backed up on the destination server (back up server)
    ...

def establish_connection():
    ...

