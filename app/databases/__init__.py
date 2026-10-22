from config import settings
from databases.base import DumpStrategy
from databases.firebird import FirebirdDump
from databases.mysql import MySQLDump
from databases.postgres import PostgresDump


def _build_postgres() -> DumpStrategy:
    pg = settings.pg
    return PostgresDump(
        host=pg.host,
        port=pg.port,
        database=pg.database,
        user=pg.user,
        password=pg.password,
    )


def _build_firebird() -> DumpStrategy:
    fb = settings.firebird
    return FirebirdDump(
        gbak_path=fb.gbak_path,
        host=fb.host,
        port=fb.port,
        database=fb.database,
        user=fb.user,
        password=fb.password,
    )


def _build_mysql() -> DumpStrategy:
    mysql = settings.mysql
    return MySQLDump(
        binary=mysql.dump_path or "mysqldump",
        host=mysql.host,
        port=mysql.port,
        database=mysql.database,
        user=mysql.user,
        password=mysql.password,
        # mariadb-dump does not have this option
        extra_args=("--set-gtid-purged=OFF",),
    )


def _build_mariadb() -> DumpStrategy:
    mysql = settings.mysql
    return MySQLDump(
        binary=mysql.dump_path or "mariadb-dump",
        host=mysql.host,
        port=mysql.port,
        database=mysql.database,
        user=mysql.user,
        password=mysql.password,
    )


# DB_ENGINE -> strategy factory. A new engine only needs an entry here.
DUMP_STRATEGIES = {
    "postgres": _build_postgres,
    "firebird": _build_firebird,
    "mysql": _build_mysql,
    "mariadb": _build_mariadb,
}


def build_dump_strategy(engine: str) -> DumpStrategy:
    if engine not in DUMP_STRATEGIES:
        raise ValueError(f"Unsupported DB_ENGINE: '{engine}'")

    return DUMP_STRATEGIES[engine]()
