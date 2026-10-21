import logging
import os
import time

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from logger import log_event
from utils import get_file_size

logger = logging.getLogger(__name__)


def create_s3_client(access_key, secret_key, region):
    client = boto3.client(
        "s3",
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name=region,
    )

    log_event(logger, "s3.client.created", region=region)

    return client


def make_s3_key(prefix: str, filename: str) -> str:
    prefix = (prefix or "").strip("/")

    if not prefix:
        return filename

    return f"{prefix}/{filename}"


def has_s3_object(s3_client, bucket: str, key: str) -> bool:
    """
    Without s3:ListBucket, a missing object returns 403 instead of 404
    """
    try:
        s3_client.head_object(Bucket=bucket, Key=key)
        return True

    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code")
        if error_code in ("404", "403", "NoSuchKey", "NotFound", "Forbidden"):
            return False
        raise


def upload_file_s3(s3_client, filepath, bucket, key, storage_class) -> bool:
    filename = os.path.basename(filepath)
    started = time.monotonic()

    try:
        s3_client.upload_file(
            filepath,
            bucket,
            key,
            ExtraArgs={
                "StorageClass": storage_class,
                "ServerSideEncryption": "AES256",
            },
        )
        log_event(
            logger, "s3.upload.ok",
            file=filename,
            bucket=bucket,
            key=key,
            storage_class=storage_class,
            size_bytes=get_file_size(filepath),
            duration_s=round(time.monotonic() - started, 3)
        )
        return True

    except (BotoCoreError, ClientError):
        log_event(
            logger, "s3.upload.failed", logging.ERROR, exc_info=True,
            file=filename, bucket=bucket, key=key
        )
        return False
