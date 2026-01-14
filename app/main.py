import logging
import os
import sys

from config import DEST_PATH, LOGS_DIR, NOW, SOURCE_PATH
from utils import (
    copy_files,
)


def main():


    logging.basicConfig(
        level=logging.INFO,
        filename=f"{LOGS_DIR}/backup_script_{NOW.date()}.log",
        encoding="utf-8",
        filemode="a",
        format="{asctime} - {levelname} - {message}",
        style="{",
        datefmt="%Y-%m-%d",
    )
    logging.info("Backup script started")

    try:
        os.makedirs(LOGS_DIR, exist_ok=True)
        os.makedirs(DEST_PATH, exist_ok=True)

        copy_files(SOURCE_PATH, DEST_PATH)

    except Exception as e:
        logging.error(e)
        sys.exit(1)

    logging.info("Backup script finished")


if __name__ == "__main__":
    main()
