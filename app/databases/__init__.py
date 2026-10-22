from config import (
    FB_DATABASE,
    FB_GBAK_PATH,
    FB_HOST,
    FB_PASSWORD,
    FB_PORT,
    FB_USER,
    PG_DB_NAME,
    PG_HOST,
    PG_PASSWORD,
    PG_PORT,
    PG_USER,
)
from databases.base import DumpStrategy
from databases.firebird import FirebirdDump
from databases.postgres import PostgresDump


def _build_postgres() -> DumpStrategy:
    return PostgresDump(
        host=PG_HOST,
        port=PG_PORT,
        database=PG_DB_NAME,
        user=PG_USER,
        password=PG_PASSWORD,
    )


def _build_firebird() -> DumpStrategy:
    return FirebirdDump(
        gbak_path=FB_GBAK_PATH,
        host=FB_HOST,
        port=FB_PORT,
        database=FB_DATABASE,
        user=FB_USER,
        password=FB_PASSWORD,
    )


# DB_ENGINE -> strategy factory. A new engine only needs an entry here.
DUMP_STRATEGIES = {
    "postgres": _build_postgres,
    "firebird": _build_firebird,
}


def build_dump_strategy(engine: str) -> DumpStrategy:
    if engine not in DUMP_STRATEGIES:
        raise ValueError(f"Unsupported DB_ENGINE: '{engine}'")

    return DUMP_STRATEGIES[engine]()
