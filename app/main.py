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
    AWS_ACCESS_KEY_ID,
    AWS_REGION,
    AWS_SECRET_ACCESS_KEY,
    BACKUP_DAYS,
    BACKUP_TARGETS,
    DB_ENGINE,
    DEST_PATH,
    LOGS_DIR,
    NOW,
    PUB_KEY_PATH,
    S3_BUCKET,
    SOURCE_PATH,
    SSH_PORT,
    SSH_SERVER,
    SSH_USER,
)
from s3_client import create_s3_client
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

    logging.info(
        f"Backup script started (engine: {DB_ENGINE}, "
        f"targets: {', '.join(BACKUP_TARGETS)})"
    )

    ssh_client = None
    s3_client = None
    exit_code = 0

    try:

        if "ssh" in BACKUP_TARGETS:
            try:
                ssh_client = create_ssh_client(
                    server=SSH_SERVER,
                    port=SSH_PORT,
                    user=SSH_USER,
                    # password=SSH_PASSWORD,
                    key_filepath=PUB_KEY_PATH
                )
            except Exception:
                # Keeps going with the other targets; run_backup marks SSH as failed
                ssh_client = None

        if "s3" in BACKUP_TARGETS:
            if not (S3_BUCKET and AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY):
                raise Exception(
                    "S3_BUCKET, AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY "
                    "are required when BACKUP_TARGETS contains s3."
                )

            s3_client = create_s3_client(
                access_key=AWS_ACCESS_KEY_ID,
                secret_key=AWS_SECRET_ACCESS_KEY,
                region=AWS_REGION
            )

        run_backup(
            src_path=SOURCE_PATH,
            backup_days=BACKUP_DAYS,
            targets=BACKUP_TARGETS,
            ssh_client=ssh_client,
            dest_path=DEST_PATH,
            s3_client=s3_client
        )

    except Exception as e:
        logging.error(e)
        exit_code = 1

    finally:
        if ssh_client:
            ssh_client.close()
            logging.info("Closed SSH connection")

        logging.info("Backup script finished")
        logging.info(f"{'#' * 100}")

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
