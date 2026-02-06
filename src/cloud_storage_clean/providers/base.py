"""Abstract base class for cloud storage providers."""

from abc import ABC, abstractmethod
from typing import Iterator

from cloud_storage_clean.models import BucketInfo, DeletionResult, FileInfo


class CloudStorageProvider(ABC):
    """Abstract interface for cloud storage operations."""

    @abstractmethod
    def list_buckets(self) -> Iterator[BucketInfo]:
        """List all accessible buckets.

        Yields:
            BucketInfo objects for each bucket.

        Raises:
            CloudStorageError: If listing fails.
        """
        pass

    @abstractmethod
    def list_files(self, bucket: str, prefix: str = "") -> Iterator[FileInfo]:
        """List files in a bucket.

        Args:
            bucket: Bucket name.
            prefix: Optional prefix to filter files.

        Yields:
            FileInfo objects for each file.

        Raises:
            CloudStorageError: If listing fails.
        """
        pass

    @abstractmethod
    def batch_delete(self, bucket: str, keys: list[str]) -> list[DeletionResult]:
        """Delete multiple files in a bucket.

        Args:
            bucket: Bucket name.
            keys: List of file keys to delete.

        Returns:
            List of DeletionResult objects.

        Raises:
            CloudStorageError: If deletion fails critically.
        """
        pass


class CloudStorageError(Exception):
    """Base exception for cloud storage operations."""

    pass


class AuthenticationError(CloudStorageError):
    """Authentication failed."""

    pass


class BucketNotFoundError(CloudStorageError):
    """Bucket does not exist."""

    pass


class RateLimitError(CloudStorageError):
    """Rate limit exceeded."""

    pass
