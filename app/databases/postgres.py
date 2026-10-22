import os

from databases.base import DumpStrategy
from generate_backup import run_dump_command


class PostgresDump(DumpStrategy):
    tool = "pg_dump"
    extension = ".sql"

    def __init__(self, host, port, database, user, password):
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password

    def dump(self, output_file: str) -> bool:
        cmd = [
            "pg_dump",
            f"--host={self.host}",
            f"--port={self.port}",
            f"--username={self.user}",
            f"--dbname={self.database}",
            f"--file={output_file}",
            "--format=plain",
            "--verbose"
        ]

        env = {**os.environ, "PGPASSWORD": self.password or ""}

        return run_dump_command(self.tool, cmd, env, output_file)
