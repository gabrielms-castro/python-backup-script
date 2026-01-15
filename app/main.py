import logging
import os
import sys

# ===== FIX PARA PYINSTALLER =====
# Garante que a pasta 'app' esteja no path tanto rodando como .py quanto como binário
if getattr(sys, 'frozen', False):
    # Rodando como binário (PyInstaller)
    application_path = sys._MEIPASS
else:
    # Rodando como script Python
    application_path = os.path.dirname(os.path.abspath(__file__))

sys.path.insert(0, application_path)
# ================================

from backup import run_backup
from config import (
    BACKUP_DAYS,
    DEST_PATH,
    LOGS_DIR,
    NOW,
    PORT,
    PUB_KEY_PATH,
    SOURCE_PATH,
    SSH_SERVER,
    SSH_USER,
)
from ssh_client import create_ssh_client


def main():

    os.makedirs(LOGS_DIR, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        filename=f"{LOGS_DIR}/backup_script_{NOW.date()}.log",
        encoding="utf-8",
        filemode="a",
        format="{asctime} - {levelname} - {message}",
        style="{",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    logging.info("Backup script started")

    ssh_client = None

    try:

        ssh_client = create_ssh_client(
            server=SSH_SERVER,
            port=PORT,
            user=SSH_USER,
            # password=SSH_PASSWORD,
            key_filepath=PUB_KEY_PATH
        )

        run_backup(
            ssh_client=ssh_client,
            ssh_user=SSH_USER,
            src_path=SOURCE_PATH,
            dest_path=DEST_PATH,
            backup_days=BACKUP_DAYS
        )

    except Exception as e:
        logging.error(e)

    finally:
        if ssh_client:
            ssh_client.close()
            logging.info("Closed SSH connection")

        logging.info("Backup script finished")
        logging.info(f"{'#' * 100}")
        sys.exit(1)


if __name__ == "__main__":
    main()
