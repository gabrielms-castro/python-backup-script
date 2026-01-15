import os
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
NOW = datetime.now()

BACKUP_DAYS = int(os.getenv("BACKUP_DAYS"))

SOURCE_PATH = Path(os.environ.get("SOURCE_PATH")) if os.getenv("ENVIRONMENT") != "dev" else Path("/srv/test_app/backup")
DEST_PATH = Path(os.environ.get("DEST_PATH"))
LOGS_DIR = BASE_DIR / "logs"

SSH_USER = os.getenv("SSH_USER").strip()
SSH_PASSWORD = os.getenv("SSH_PASSWORD").strip()
SSH_SERVER = os.getenv("SSH_SERVER").strip()
PUB_KEY_PATH = os.getenv("PUB_KEY_PATH").strip()
PORT = os.getenv("PORT").strip()


# PostgreSQL Variables
PG_HOST = os.getenv("PG_HOST")
PG_PORT = os.getenv("PG_PORT")
DB_NAME = os.getenv("DB_NAME")
PG_USER = os.getenv("PG_USER")
PG_PASSWORD = os.getenv("PG_PASSWORD")
