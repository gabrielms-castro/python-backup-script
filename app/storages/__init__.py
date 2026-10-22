from config import (
    AWS_ACCESS_KEY_ID,
    AWS_REGION,
    AWS_SECRET_ACCESS_KEY,
    BACKUP_DAYS,
    DEST_PATH,
    PUB_KEY_PATH,
    S3_BUCKET,
    S3_PREFIX,
    S3_STORAGE_CLASS,
    SSH_PORT,
    SSH_SERVER,
    SSH_USER,
)
from storages.base import StorageAdapter
from storages.s3 import S3Storage
from storages.ssh import SSHStorage


def _build_ssh() -> StorageAdapter:
    # Missing SSH settings only fail this target (on connect), not the run
    return SSHStorage(
        server=SSH_SERVER,
        port=SSH_PORT,
        user=SSH_USER,
        key_filepath=PUB_KEY_PATH,
        dest_path=DEST_PATH,
        backup_days=BACKUP_DAYS,
    )


def _build_s3() -> StorageAdapter:
    if not (S3_BUCKET and AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY):
        raise Exception(
            "S3_BUCKET, AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY "
            "are required when BACKUP_TARGETS contains s3."
        )

    return S3Storage(
        bucket=S3_BUCKET,
        prefix=S3_PREFIX,
        storage_class=S3_STORAGE_CLASS,
        access_key=AWS_ACCESS_KEY_ID,
        secret_key=AWS_SECRET_ACCESS_KEY,
        region=AWS_REGION,
    )


# BACKUP_TARGETS name -> adapter factory. A new storage (e.g. Google Cloud
# Storage) only needs an adapter module and an entry here.
STORAGES = {
    "ssh": _build_ssh,
    "s3": _build_s3,
}


def build_storages(targets: list) -> list[StorageAdapter]:
    invalid = [target for target in targets if target not in STORAGES]
    if invalid or not targets:
        raise ValueError(f"Invalid BACKUP_TARGETS: {','.join(targets)}")

    return [STORAGES[target]() for target in targets]
