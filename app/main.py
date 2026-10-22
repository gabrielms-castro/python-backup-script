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
    BACKUP_DAYS,
    BACKUP_TARGETS,
    COMPRESS_BACKUP,
    DB_ENGINE,
    DEST_PATH,
    HEALTHCHECK_URL,
    LOGS_DIR,
    NOW,
    S3_BUCKET,
    S3_PREFIX,
    SOURCE_PATH,
)
from databases import build_dump_strategy
from healthcheck import ping
from logger import log_event, setup_logging
from storages import build_storages

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

    storages = []
    exit_code = 0
    summary = {}
    last_error = None

    try:
        # Config errors (engine, targets, credentials) fail before the dump
        dump_strategy = build_dump_strategy(DB_ENGINE)
        storages = build_storages(BACKUP_TARGETS)

        run_backup(
            src_path=SOURCE_PATH,
            dump_strategy=dump_strategy,
            storages=storages,
            compress=COMPRESS_BACKUP,
            summary=summary
        )

    except Exception as exc:
        log_event(logger, "run.failed", logging.ERROR, exc_info=True)
        exit_code = 1
        last_error = str(exc)

    finally:
        for storage in storages:
            storage.close()

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
