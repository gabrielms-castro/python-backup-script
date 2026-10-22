from abc import ABC, abstractmethod


class StorageAdapter(ABC):
    """
    Common interface of the backup targets (SSH server, S3 bucket, ...).
    """

    # Target name used on BACKUP_TARGETS, on the logs and on the summary
    name: str

    def connect(self) -> None:
        """
        Opens the connection/client. May raise; the target is then failed.
        """

    @abstractmethod
    def upload(self, src_files: list[dict]) -> set:
        """
        Sends the files missing on the target and returns the filenames
        confirmed there. Raises if the target cannot be used at all.
        """

    def apply_retention(self) -> None:
        """
        Deletes old backups on the target, when the script owns retention.
        """

    def close(self) -> None:
        """
        Releases the connection; must not raise.
        """
