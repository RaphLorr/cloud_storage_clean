"""Bucket and file scanning with filtering."""

from datetime import datetime
from typing import Iterator, Pattern

from cloud_storage_clean.models import DeletionFilter, FileInfo
from cloud_storage_clean.providers.base import CloudStorageProvider
from cloud_storage_clean.utils.logging import get_logger
from cloud_storage_clean.utils.validators import (
    compile_regex,
    matches_glob,
    matches_regex,
    validate_glob_pattern,
)

logger = get_logger(__name__)


class BucketScanner:
    """Scans buckets and files with lazy evaluation."""

    def __init__(self, provider: CloudStorageProvider) -> None:
        """Initialize scanner.

        Args:
            provider: Cloud storage provider instance.
        """
        self.provider = provider

    def scan(self, deletion_filter: DeletionFilter) -> Iterator[FileInfo]:
        """Scan for files matching deletion criteria.

        Uses lazy evaluation - yields files as they're found without
        loading everything into memory.

        Args:
            deletion_filter: Criteria for filtering files.

        Yields:
            FileInfo objects matching all criteria.

        Raises:
            ValueError: If patterns are invalid.
            CloudStorageError: If scanning fails.
        """
        # Validate patterns first
        validate_glob_pattern(deletion_filter.file_pattern)
        bucket_regex = compile_regex(deletion_filter.bucket_pattern)

        logger.info(
            "scan_started",
            bucket_pattern=deletion_filter.bucket_pattern,
            file_pattern=deletion_filter.file_pattern,
            before_date=deletion_filter.before_date.isoformat(),
        )

        matched_buckets = 0
        total_files = 0

        # Iterate through buckets
        for bucket_info in self.provider.list_buckets():
            if not matches_regex(bucket_info.name, bucket_regex):
                logger.debug("bucket_skipped", bucket=bucket_info.name, reason="pattern_mismatch")
                continue

            matched_buckets += 1
            logger.info("bucket_matched", bucket=bucket_info.name)

            # Iterate through files in matching bucket
            bucket_files = 0
            for file_info in self.provider.list_files(bucket_info.name):
                # Apply file pattern filter
                if not matches_glob(file_info.key, deletion_filter.file_pattern):
                    continue

                # Apply time filter
                if file_info.last_modified >= deletion_filter.before_date:
                    continue

                bucket_files += 1
                total_files += 1
                yield file_info

            if bucket_files > 0:
                logger.info(
                    "bucket_scan_completed",
                    bucket=bucket_info.name,
                    files_matched=bucket_files,
                )

        logger.info(
            "scan_completed",
            matched_buckets=matched_buckets,
            total_files=total_files,
        )


def create_deletion_summary(files: list[FileInfo], provider: str) -> dict[str, int | dict]:
    """Create summary statistics from files list.

    Args:
        files: List of FileInfo objects.
        provider: Provider name.

    Returns:
        Dictionary with summary statistics.
    """
    from collections import defaultdict

    files_by_bucket: dict[str, int] = defaultdict(int)
    size_by_bucket: dict[str, int] = defaultdict(int)
    total_size = 0

    for file_info in files:
        files_by_bucket[file_info.bucket] += 1
        size_by_bucket[file_info.bucket] += file_info.size
        total_size += file_info.size

    return {
        "total_files": len(files),
        "total_size": total_size,
        "files_by_bucket": dict(files_by_bucket),
        "size_by_bucket": dict(size_by_bucket),
        "provider": provider,
    }
