import os
import tempfile

from databases.base import DumpStrategy
from generate_backup import run_dump_command


class MySQLDump(DumpStrategy):
    """
    mysqldump (MySQL) and mariadb-dump (MariaDB) share the same options;
    engine specific ones go in extra_args.
    """

    extension = ".sql"

    def __init__(
        self, binary, host, port, database, user, password, extra_args=()
    ):
        self.binary = binary
        self.tool = os.path.basename(binary)
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.extra_args = list(extra_args)

    def dump(self, output_file: str) -> bool:
        # Password in an option file so it does not show up in `ps`
        # (MYSQL_PWD is deprecated on MySQL 8)
        options_file = _write_options_file(self.password)

        try:
            cmd = [
                # must be the first argument
                f"--defaults-extra-file={options_file}",
                f"--host={self.host}",
                f"--port={self.port}",
                f"--user={self.user}",
                "--single-transaction",
                "--quick",
                "--routines",
                "--triggers",
                "--events",
                # avoids requiring the PROCESS privilege (MySQL >= 8.0.21)
                "--no-tablespaces",
                "--verbose",
                *self.extra_args,
                f"--result-file={output_file}",
                self.database,
            ]

            return run_dump_command(
                self.tool, [self.binary, *cmd], dict(os.environ), output_file
            )

        finally:
            os.remove(options_file)


def _write_options_file(password) -> str:
    # mkstemp creates the file with mode 0600
    fd, path = tempfile.mkstemp(prefix="backup_mysql_", suffix=".cnf")
    escaped = (password or "").replace("\\", "\\\\").replace('"', '\\"')

    with os.fdopen(fd, "w") as f:
        f.write(f'[client]\npassword="{escaped}"\n')

    return path
