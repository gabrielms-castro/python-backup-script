import os
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def _env(name, default=None):
    value = os.getenv(name)
    if value is None or not value.strip():
        return default
    return value.strip()


BASE_DIR = Path(__file__).resolve().parent.parent
NOW = datetime.now()
ENVIRONMENT = _env("ENVIRONMENT")
BACKUP_DAYS = int(_env("BACKUP_DAYS", "7"))
SOURCE_PATH = Path(_env("SOURCE_PATH")) if ENVIRONMENT != "dev" else Path("/srv/test_app/backup")
DEST_PATH = Path(_env("DEST_PATH")) if _env("DEST_PATH") else None
LOGS_DIR = Path(_env("LOGS_DIR", BASE_DIR / "logs")) if ENVIRONMENT != "dev" else BASE_DIR / "logs"
SSH_USER = _env("SSH_USER")
SSH_PASSWORD = _env("SSH_PASSWORD")
SSH_SERVER = _env("SSH_SERVER")
SSH_PORT = _env("SSH_PORT") or _env("PORT", "22")
PUB_KEY_PATH = _env("PUB_KEY_PATH")

# Backup settings
# postgres | firebird (see databases.DUMP_STRATEGIES)
DB_ENGINE = _env("DB_ENGINE", "postgres").lower()
COMPRESS_BACKUP = _env("COMPRESS_BACKUP", "true").lower() == "true"
BACKUP_TARGETS = [
    target.strip()
    for target in _env("BACKUP_TARGETS", "ssh").lower().split(",")
    if target.strip()
]  # ssh | s3 | ssh,s3, validated by storages.build_storages

# Monitoring (Healthchecks.io); empty = disabled
HEALTHCHECK_URL = _env("HEALTHCHECK_URL")

# AWS S3 Variables
S3_BUCKET = _env("S3_BUCKET")
S3_PREFIX = _env("S3_PREFIX", "")
S3_STORAGE_CLASS = _env("S3_STORAGE_CLASS", "STANDARD")
AWS_REGION = _env("AWS_REGION", "us-east-1")
AWS_ACCESS_KEY_ID = _env("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = _env("AWS_SECRET_ACCESS_KEY")

# PostgreSQL Variables
PG_HOST = _env("PG_HOST", "localhost")
PG_PORT = _env("PG_PORT", "5432")
PG_DB_NAME = _env("PG_DB_NAME")
PG_USER = _env("PG_USER")
PG_PASSWORD = _env("PG_PASSWORD")

# Firebird Variables
FB_HOST = _env("FB_HOST", "localhost")
FB_PORT = _env("FB_PORT", "3050")
FB_DATABASE = _env("FB_DATABASE")
FB_USER = _env("FB_USER", "SYSDBA")
FB_PASSWORD = _env("FB_PASSWORD")
FB_GBAK_PATH = _env("FB_GBAK_PATH", "gbak")
