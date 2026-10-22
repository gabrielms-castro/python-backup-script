import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent


def _env(name, default=None, cast=None):
    """
    Empty or blank values fall back to the default; cast only applies to
    values that were actually set.
    """
    value = os.getenv(name)
    if value is None or not value.strip():
        return default

    value = value.strip()
    return cast(value) if cast else value


@dataclass(frozen=True)
class PostgresSettings:
    host: str
    port: str
    database: Optional[str]
    user: Optional[str]
    password: Optional[str] = field(repr=False)

    @classmethod
    def from_env(cls) -> "PostgresSettings":
        return cls(
            host=_env("PG_HOST", "localhost"),
            port=_env("PG_PORT", "5432"),
            database=_env("PG_DB_NAME"),
            user=_env("PG_USER"),
            password=_env("PG_PASSWORD"),
        )


@dataclass(frozen=True)
class FirebirdSettings:
    host: str
    port: str
    database: Optional[str]
    user: str
    password: Optional[str] = field(repr=False)
    # full path (/opt/firebird/bin/gbak) or 'gbak' if in PATH
    gbak_path: str = "gbak"

    @classmethod
    def from_env(cls) -> "FirebirdSettings":
        return cls(
            host=_env("FB_HOST", "localhost"),
            port=_env("FB_PORT", "3050"),
            database=_env("FB_DATABASE"),
            user=_env("FB_USER", "SYSDBA"),
            password=_env("FB_PASSWORD"),
            gbak_path=_env("FB_GBAK_PATH", "gbak"),
        )


@dataclass(frozen=True)
class MySQLSettings:
    """
    Used by DB_ENGINE=mysql | mariadb.
    """

    host: str
    port: str
    database: Optional[str]
    user: Optional[str]
    password: Optional[str] = field(repr=False)
    # None = mysqldump (mysql) or mariadb-dump (mariadb), from PATH
    dump_path: Optional[str] = None

    @classmethod
    def from_env(cls) -> "MySQLSettings":
        return cls(
            host=_env("MYSQL_HOST", "localhost"),
            port=_env("MYSQL_PORT", "3306"),
            database=_env("MYSQL_DATABASE"),
            user=_env("MYSQL_USER"),
            password=_env("MYSQL_PASSWORD"),
            dump_path=_env("MYSQL_DUMP_PATH"),
        )


@dataclass(frozen=True)
class SSHSettings:
    """
    Backup server (BACKUP_TARGETS contains ssh). Retention is done there.
    """

    server: Optional[str]
    port: str
    user: Optional[str]
    password: Optional[str] = field(repr=False)
    key_filepath: Optional[str] = None
    dest_path: Optional[Path] = None
    backup_days: int = 7

    @classmethod
    def from_env(cls) -> "SSHSettings":
        return cls(
            server=_env("SSH_SERVER"),
            port=_env("SSH_PORT") or _env("PORT", "22"),
            user=_env("SSH_USER"),
            password=_env("SSH_PASSWORD"),
            key_filepath=_env("PUB_KEY_PATH"),
            dest_path=_env("DEST_PATH", cast=Path),
            backup_days=_env("BACKUP_DAYS", 7, int),
        )


@dataclass(frozen=True)
class S3Settings:
    """
    AWS S3 (BACKUP_TARGETS contains s3). Retention is the bucket lifecycle.
    """

    bucket: Optional[str]
    prefix: str
    storage_class: str
    region: str
    access_key_id: Optional[str] = field(repr=False)
    secret_access_key: Optional[str] = field(repr=False)

    @classmethod
    def from_env(cls) -> "S3Settings":
        return cls(
            bucket=_env("S3_BUCKET"),
            prefix=_env("S3_PREFIX", ""),
            storage_class=_env("S3_STORAGE_CLASS", "STANDARD"),
            region=_env("AWS_REGION", "us-east-1"),
            access_key_id=_env("AWS_ACCESS_KEY_ID"),
            secret_access_key=_env("AWS_SECRET_ACCESS_KEY"),
        )


@dataclass(frozen=True)
class Settings:
    environment: Optional[str]
    now: datetime
    source_path: Path
    logs_dir: Path
    # postgres | firebird | mysql | mariadb (see databases.DUMP_STRATEGIES)
    db_engine: str
    compress_backup: bool
    # ssh | s3 | ssh,s3, validated by storages.build_storages
    backup_targets: tuple[str, ...]
    # Healthchecks.io ping URL; None = disabled
    healthcheck_url: Optional[str]
    pg: PostgresSettings
    firebird: FirebirdSettings
    mysql: MySQLSettings
    ssh: SSHSettings
    s3: S3Settings

    @classmethod
    def from_env(cls) -> "Settings":
        environment = _env("ENVIRONMENT")

        if environment == "dev":
            source_path = Path("/srv/test_app/backup")
            logs_dir = BASE_DIR / "logs"
        else:
            source_path = _env("SOURCE_PATH", cast=Path)
            if source_path is None:
                raise ValueError("SOURCE_PATH is required.")
            logs_dir = _env("LOGS_DIR", BASE_DIR / "logs", Path)

        targets = _env("BACKUP_TARGETS", "ssh").lower().split(",")

        return cls(
            environment=environment,
            now=datetime.now(),
            source_path=source_path,
            logs_dir=logs_dir,
            db_engine=_env("DB_ENGINE", "postgres").lower(),
            compress_backup=_env("COMPRESS_BACKUP", "true").lower() == "true",
            backup_targets=tuple(
                target.strip() for target in targets if target.strip()
            ),
            healthcheck_url=_env("HEALTHCHECK_URL"),
            pg=PostgresSettings.from_env(),
            firebird=FirebirdSettings.from_env(),
            mysql=MySQLSettings.from_env(),
            ssh=SSHSettings.from_env(),
            s3=S3Settings.from_env(),
        )


settings = Settings.from_env()
