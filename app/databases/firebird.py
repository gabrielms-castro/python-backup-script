import os

from databases.base import DumpStrategy
from generate_backup import run_dump_command


class FirebirdDump(DumpStrategy):
    tool = "gbak"
    extension = ".fbk"

    def __init__(self, gbak_path, host, port, database, user, password):
        self.gbak_path = gbak_path
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password

    def dump(self, output_file: str) -> bool:
        cmd = [
            self.gbak_path,
            "-b",
            "-v",
            "-g",
            f"{self.host}/{self.port}:{self.database}",
            output_file
        ]

        # Credentials via env so the password does not show up in `ps`
        env = {
            **os.environ,
            "ISC_USER": self.user or "",
            "ISC_PASSWORD": self.password or "",
        }

        return run_dump_command(self.tool, cmd, env, output_file)
