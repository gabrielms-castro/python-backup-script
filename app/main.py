import json
import logging
import os
import socket
import sys
import time
import uuid

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
    COMPRESS_BACKUP,
    DB_ENGINE,
    DEST_PATH,
    HEALTHCHECK_URL,
    LOGS_DIR,
    NOW,
    PUB_KEY_PATH,
    S3_BUCKET,
    S3_PREFIX,
    SOURCE_PATH,
    SSH_PORT,
    SSH_SERVER,
    SSH_USER,
)
from healthcheck import ping
from logger import log_event, setup_logging
from s3_client import create_s3_client
from ssh_client import create_ssh_client

logger = logging.getLogger("main")


def main():

    run_id = uuid.uuid4().hex[:8]
    started = time.monotonic()
    error_counter = setup_logging(LOGS_DIR, run_id, NOW.date())

    log_event(
        logger, "run.started",
        engine=DB_ENGINE,
        targets=BACKUP_TARGETS,
        compress=COMPRESS_BACKUP,
        backup_days=BACKUP_DAYS,
        source_path=SOURCE_PATH,
        dest_path=DEST_PATH,
        s3_bucket=S3_BUCKET,
        s3_prefix=S3_PREFIX,
        host=socket.gethostname(),
        pid=os.getpid(),
    )
    ping(HEALTHCHECK_URL, "start")

    ssh_client = None
    s3_client = None
    exit_code = 0
    summary = {}
    last_error = None

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
            s3_client=s3_client,
            summary=summary
        )

    except Exception as exc:
        log_event(logger, "run.failed", logging.ERROR, exc_info=True)
        exit_code = 1
        last_error = str(exc)

    finally:
        if ssh_client:
            ssh_client.close()
            log_event(logger, "ssh.connection.closed")

        status = get_run_status(exit_code, summary)
        result = {
            "status": status,
            "exit_code": exit_code,
            "duration_s": round(time.monotonic() - started, 3),
            "backup_file": summary.get("backup_file"),
            "target_results": summary.get("target_results", {}),
            "failed_targets": summary.get("failed_targets", []),
            "files_backed_up": summary.get("files_backed_up", 0),
            "errors": error_counter.errors,
            "warnings": error_counter.warnings,
        }
        log_event(
            logger, "run.finished",
            logging.INFO if status == "success" else logging.ERROR,
            **result
        )

        # partial counts as failure, same as the exit code
        ping(
            HEALTHCHECK_URL,
            "" if status == "success" else "fail",
            body=json.dumps(
                {"run_id": run_id, **result, "error": last_error},
                default=str
            )
        )

    sys.exit(exit_code)


def get_run_status(exit_code: int, summary: dict) -> str:
    """
    success: every target ok
    partial: at least one target ok
    failed: dump/config failure or every target failed
    """
    if exit_code == 0:
        return "success"

    if "ok" in summary.get("target_results", {}).values():
        return "partial"

    return "failed"


if __name__ == "__main__":
    main()
