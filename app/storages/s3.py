import logging

from logger import log_event
from s3_client import (
    create_s3_client,
    has_s3_object,
    make_s3_key,
    upload_file_s3,
)
from storages.base import StorageAdapter
from utils import get_file_name

logger = logging.getLogger(__name__)


class S3Storage(StorageAdapter):
    """
    AWS S3 bucket. Retention is handled by the bucket lifecycle rule.
    """

    name = "s3"

    def __init__(
        self, bucket, prefix, storage_class, access_key, secret_key, region
    ):
        self.bucket = bucket
        self.prefix = prefix
        self.storage_class = storage_class
        self.access_key = access_key
        self.secret_key = secret_key
        self.region = region
        self.client = None

    def connect(self) -> None:
        self.client = create_s3_client(
            access_key=self.access_key,
            secret_key=self.secret_key,
            region=self.region
        )

    def upload(self, src_files: list[dict]) -> set:
        if not self.client:
            raise Exception("S3 client not available")

        uploaded = set()

        for src_file in src_files:
            src_filepath = src_file["filepath"]
            src_filename = get_file_name(src_filepath)
            key = make_s3_key(self.prefix, src_filename)

            if has_s3_object(self.client, self.bucket, key):
                log_event(
                    logger, "s3.upload.skipped",
                    file=src_filename, bucket=self.bucket, key=key,
                    reason="already uploaded"
                )
                uploaded.add(src_filename)
                continue

            if upload_file_s3(
                self.client, src_filepath, self.bucket, key,
                self.storage_class
            ):
                uploaded.add(src_filename)

        return uploaded
