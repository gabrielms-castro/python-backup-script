import os
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

NOW = datetime.now()
BASE_DIR = Path(__file__).resolve().parent.parent
SOURCE_PATH = Path(os.environ.get("SOURCE_PATH"))
DEST_PATH = Path(os.environ.get("DEST_PATH"))
LOGS_DIR = BASE_DIR / "logs"
