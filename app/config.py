import os
from datetime import datetime
from pathlib import Path

NOW = datetime.now()
BASE_DIR = Path(__file__).resolve().parent.parent
BACKUP_PATH = Path(os.environ.get("BACKUP_PATH")) if os.environ.get("ENVIRONMENT") == "prod" else Path(os.environ.get("BACKUP_PATH_DEV"))