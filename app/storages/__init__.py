from config import settings
from storages.base import StorageAdapter
from storages.s3 import S3Storage
from storages.ssh import SSHStorage


def _build_ssh() -> StorageAdapter:
    ssh = settings.ssh
    # Missing SSH settings only fail this target (on connect), not the run
    return SSHStorage(
        server=ssh.server,
        port=ssh.port,
        user=ssh.user,
        key_filepath=ssh.key_filepath,
        dest_path=ssh.dest_path,
        backup_days=ssh.backup_days,
    )


def _build_s3() -> StorageAdapter:
    s3 = settings.s3
    if not (s3.bucket and s3.access_key_id and s3.secret_access_key):
        raise Exception(
            "S3_BUCKET, AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY "
            "are required when BACKUP_TARGETS contains s3."
        )

    return S3Storage(
        bucket=s3.bucket,
        prefix=s3.prefix,
        storage_class=s3.storage_class,
        access_key=s3.access_key_id,
        secret_key=s3.secret_access_key,
        region=s3.region,
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
