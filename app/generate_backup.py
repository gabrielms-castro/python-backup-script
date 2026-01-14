import logging
import subprocess
from datetime import datetime


def pg_dump_database(
    host: str,
    port: int,
    database: str,
    user: str,
    password: str,
    output_file: str
) -> bool:

    try:
        # Monta o comando
        cmd = [
            "pg_dump",
            f"--host={host}",
            f"--port={port}",
            f"--username={user}",
            f"--dbname={database}",
            f"--file={output_file}",
            "--format=custom",
            "--verbose"
        ]

        # Define a senha via variável de ambiente (mais seguro que passar na linha de comando)
        env = {"PGPASSWORD": password}

        # Executa
        result = subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            text=True,
            check=True
        )

        logging.info(f"[OK] Database dump created: {output_file}")
        return True

    except subprocess.CalledProcessError as e:
        logging.error(f"[FAIL] pg_dump failed: {e.stderr}")
        return False
    except Exception as e:
        logging.error(f"[ERROR] Exception during pg_dump: {e}")
        return False


# Uso:
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
output_file = f"/srv/test_app/backup/db_backup_{timestamp}.dump"
