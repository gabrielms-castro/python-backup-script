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
from config import settings
from databases import build_dump_strategy
from healthcheck import ping
from logger import log_event, setup_logging
from storages import build_storages

logger = logging.getLogger("main")


def main():

    run_id = uuid.uuid4().hex[:8]
    started = time.monotonic()
    error_counter = setup_logging(
        settings.logs_dir, run_id, settings.now.date()
    )

    log_event(
        logger, "run.started",
        engine=settings.db_engine,
        targets=settings.backup_targets,
        compress=settings.compress_backup,
        backup_days=settings.ssh.backup_days,
        source_path=settings.source_path,
        dest_path=settings.ssh.dest_path,
        s3_bucket=settings.s3.bucket,
        s3_prefix=settings.s3.prefix,
        host=socket.gethostname(),
        pid=os.getpid(),
    )
    ping(settings.healthcheck_url, "start")

    storages = []
    exit_code = 0
    summary = {}
    last_error = None

    try:
        # Config errors (engine, targets, credentials) fail before the dump
        dump_strategy = build_dump_strategy(settings.db_engine)
        storages = build_storages(settings.backup_targets)

        run_backup(
            src_path=settings.source_path,
            dump_strategy=dump_strategy,
            storages=storages,
            compress=settings.compress_backup,
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
            settings.healthcheck_url,
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
