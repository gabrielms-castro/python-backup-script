import os
import sys
import logging

from config import (
    NOW,
    BACKUP_PATH,
    BASE_DIR
)

from utils import (
    generate_n_days_array,
    search_for_files,
    get_files_older_than_n_days,
    get_files_within_last_n_days
)

def main():

    log_dir = BASE_DIR/"logs"
    os.makedirs(log_dir, exist_ok=True )
    logging.basicConfig(
        level=logging.INFO,
        filename=f"{log_dir}/backup_script_{NOW}.log", 
        encoding="utf-8",
        filemode="a",
        format="{asctime} - {levelname} - {message}",
        style="{",
        datefmt="%Y-%m-%d %H:%M",
    )
    logging.info("Backup script started")

    try:
        files = search_for_files(BACKUP_PATH)
        print(files)

        last_7_days = generate_n_days_array(n=7)
        files_older_than_7_days = get_files_older_than_n_days(last_n_days=last_7_days, files=files)
        print("\n", files_older_than_7_days)

        files_within_last_7_days = get_files_within_last_n_days(last_n_days=last_7_days, files=files)
        print("\n", files_within_last_7_days)

        os.chdir(BACKUP_PATH)

    except Exception as e:
        logging.error(e)
        sys.exit(1)

    logging.info("Backup script finished")

if __name__ == "__main__":
    main()


