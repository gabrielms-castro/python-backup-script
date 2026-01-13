import os
import sys
import logging

from datetime import datetime
from pathlib import Path

from utils import (
    search_for_files,
    get_files_over_nth_day
)

now = datetime.now()
logging.basicConfig(
    level=logging.INFO,
    filename=f"backup_script_{now}.log", 
    encoding="utf-8",
    filemode="a",
    format="{asctime} - {levelname} - {message}",
    style="{",
    datefmt="%Y-%m-%d %H:%M",
)

BASE_DIR = Path.home()
BACKUP_PATH = Path("/srv/sales-core/backups")
BACKUP_PATH_DEV = Path("/srv/test_app/backup")


def main():

    logging.info("Backup script started")

    try:
        files = search_for_files(BACKUP_PATH_DEV)
        print(files)

        dates = get_files_over_nth_day(nth_day=7, files=files)
        print("\n", dates)
        os.chdir(BACKUP_PATH_DEV)

    except Exception as e:
        logging.error(e)
        sys.exit(1)

    logging.info("Backup script finished")

if __name__ == "__main__":
    main()


