"""Unit tests for scanner."""

from datetime import datetime, timezone
from unittest.mock import Mock

import pytest

from cloud_storage_clean.models import BucketInfo, DeletionFilter, FileInfo, FileTypeSummary
from cloud_storage_clean.scanner import BucketScanner, create_deletion_summary


@pytest.fixture
def mock_provider() -> Mock:
    """Create mock provider."""
    return Mock()


def test_scanner_initialization(mock_provider: Mock) -> None:
    """Test scanner initialization."""
    scanner = BucketScanner(mock_provider)
    assert scanner.provider == mock_provider


def test_scanner_filters_buckets_by_pattern(mock_provider: Mock) -> None:
    """Test that scanner filters buckets by regex pattern."""
    # Mock bucket list
    mock_provider.list_buckets.return_value = iter(
        [
            BucketInfo("test-bucket-1", datetime(2023, 1, 1), "tencent"),
            BucketInfo("prod-bucket-1", datetime(2023, 1, 1), "tencent"),
            BucketInfo("test-bucket-2", datetime(2023, 1, 1), "tencent"),
        ]
    )

    # Mock file list (empty for simplicity)
    mock_provider.list_files.return_value = iter([])

    scanner = BucketScanner(mock_provider)
    deletion_filter = DeletionFilter(
        bucket_pattern=r"^test-.*",
        file_pattern="*.log",
        before_date=datetime(2024, 1, 1),
        provider="tencent",
    )

    list(scanner.scan(deletion_filter))

    # Should only call list_files for test buckets
    assert mock_provider.list_files.call_count == 2


def test_scanner_filters_files_by_glob(mock_provider: Mock) -> None:
    """Test that scanner filters files by glob pattern."""
    mock_provider.list_buckets.return_value = iter(
        [BucketInfo("test-bucket", datetime(2023, 1, 1), "tencent")]
    )

    mock_provider.list_files.return_value = iter(
        [
            FileInfo("test-bucket", "file1.log", 1024, datetime(2023, 1, 1), "tencent"),
            FileInfo("test-bucket", "file2.txt", 1024, datetime(2023, 1, 1), "tencent"),
            FileInfo("test-bucket", "file3.log", 1024, datetime(2023, 1, 1), "tencent"),
        ]
    )

    scanner = BucketScanner(mock_provider)
    deletion_filter = DeletionFilter(
        bucket_pattern=".*",
        file_pattern="*.log",
        before_date=datetime(2024, 1, 1),
        provider="tencent",
    )

    results = list(scanner.scan(deletion_filter))

    # Should only return .log files
    assert len(results) == 2
    assert all(r.key.endswith(".log") for r in results)


def test_scanner_filters_files_by_date(mock_provider: Mock) -> None:
    """Test that scanner filters files by modification date."""
    mock_provider.list_buckets.return_value = iter(
        [BucketInfo("test-bucket", datetime(2023, 1, 1), "tencent")]
    )

    mock_provider.list_files.return_value = iter(
        [
            FileInfo("test-bucket", "old.log", 1024, datetime(2023, 1, 1), "tencent"),
            FileInfo("test-bucket", "new.log", 1024, datetime(2024, 6, 1), "tencent"),
            FileInfo("test-bucket", "mid.log", 1024, datetime(2023, 12, 31), "tencent"),
        ]
    )

    scanner = BucketScanner(mock_provider)
    deletion_filter = DeletionFilter(
        bucket_pattern=".*",
        file_pattern="*.log",
        before_date=datetime(2024, 1, 1),
        provider="tencent",
    )

    results = list(scanner.scan(deletion_filter))

    # Should only return files before 2024-01-01
    assert len(results) == 2
    assert all(r.last_modified < datetime(2024, 1, 1) for r in results)


def test_scanner_invalid_regex_pattern(mock_provider: Mock) -> None:
    """Test scanner with invalid regex pattern."""
    scanner = BucketScanner(mock_provider)
    deletion_filter = DeletionFilter(
        bucket_pattern=r"test-[",  # Invalid regex
        file_pattern="*.log",
        before_date=datetime(2024, 1, 1),
        provider="tencent",
    )

    with pytest.raises(ValueError, match="Invalid regex pattern"):
        list(scanner.scan(deletion_filter))


def test_scanner_invalid_glob_pattern(mock_provider: Mock) -> None:
    """Test scanner with invalid glob pattern."""
    scanner = BucketScanner(mock_provider)
    deletion_filter = DeletionFilter(
        bucket_pattern=".*",
        file_pattern="",  # Empty glob
        before_date=datetime(2024, 1, 1),
        provider="tencent",
    )

    with pytest.raises(ValueError, match="cannot be empty"):
        list(scanner.scan(deletion_filter))


def test_create_deletion_summary() -> None:
    """Test creating deletion summary."""
    files = [
        FileInfo("bucket-1", "file1.log", 1024, datetime(2023, 1, 1), "tencent"),
        FileInfo("bucket-1", "file2.log", 2048, datetime(2023, 1, 1), "tencent"),
        FileInfo("bucket-2", "file3.log", 512, datetime(2023, 1, 1), "tencent"),
    ]

    summary = create_deletion_summary(files, "tencent")

    assert summary["total_files"] == 3
    assert summary["total_size"] == 3584
    assert summary["files_by_bucket"]["bucket-1"] == 2
    assert summary["files_by_bucket"]["bucket-2"] == 1
    assert summary["size_by_bucket"]["bucket-1"] == 3072
    assert summary["size_by_bucket"]["bucket-2"] == 512
    assert summary["provider"] == "tencent"


def test_create_deletion_summary_empty() -> None:
    """Test creating summary with empty file list."""
    summary = create_deletion_summary([], "tencent")

    assert summary["total_files"] == 0
    assert summary["total_size"] == 0
    assert summary["files_by_bucket"] == {}
    assert summary["size_by_bucket"] == {}


def test_scan_file_types_filters_buckets(mock_provider: Mock) -> None:
    """Test that scan_file_types filters buckets by regex pattern."""
    mock_provider.list_buckets.return_value = iter(
        [
            BucketInfo("test-bucket-1", datetime(2023, 1, 1), "tencent"),
            BucketInfo("prod-bucket-1", datetime(2023, 1, 1), "tencent"),
            BucketInfo("test-bucket-2", datetime(2023, 1, 1), "tencent"),
        ]
    )
    mock_provider.list_files.return_value = iter([])

    scanner = BucketScanner(mock_provider)
    list(scanner.scan_file_types(r"^test-.*", datetime(2024, 1, 1)))

    assert mock_provider.list_files.call_count == 2


def test_scan_file_types_groups_by_extension(mock_provider: Mock) -> None:
    """Test that scan_file_types groups files by extension correctly."""
    mock_provider.list_buckets.return_value = iter(
        [BucketInfo("test-bucket", datetime(2023, 1, 1), "tencent")]
    )
    mock_provider.list_files.return_value = iter(
        [
            FileInfo("test-bucket", "a.log", 100, datetime(2023, 1, 1), "tencent"),
            FileInfo("test-bucket", "b.log", 200, datetime(2023, 2, 1), "tencent"),
            FileInfo("test-bucket", "c.json", 50, datetime(2023, 3, 1), "tencent"),
        ]
    )

    scanner = BucketScanner(mock_provider)
    results = list(scanner.scan_file_types(".*", datetime(2024, 1, 1)))

    assert len(results) == 2
    log_summary = next(r for r in results if r.extension == ".log")
    json_summary = next(r for r in results if r.extension == ".json")

    assert log_summary.file_count == 2
    assert log_summary.total_size == 300
    assert json_summary.file_count == 1
    assert json_summary.total_size == 50


def test_scan_file_types_handles_no_extension(mock_provider: Mock) -> None:
    """Test that files without extensions are grouped as '(no ext)'."""
    mock_provider.list_buckets.return_value = iter(
        [BucketInfo("test-bucket", datetime(2023, 1, 1), "tencent")]
    )
    mock_provider.list_files.return_value = iter(
        [
            FileInfo("test-bucket", "Makefile", 500, datetime(2023, 1, 1), "tencent"),
            FileInfo("test-bucket", "README", 200, datetime(2023, 1, 1), "tencent"),
            FileInfo("test-bucket", "data.csv", 100, datetime(2023, 1, 1), "tencent"),
        ]
    )

    scanner = BucketScanner(mock_provider)
    results = list(scanner.scan_file_types(".*", datetime(2024, 1, 1)))

    no_ext = next(r for r in results if r.extension == "(no ext)")
    assert no_ext.file_count == 2
    assert no_ext.total_size == 700


def test_scan_file_types_compound_extension(mock_provider: Mock) -> None:
    """Test that compound extensions like .tar.gz use last suffix (.gz)."""
    mock_provider.list_buckets.return_value = iter(
        [BucketInfo("test-bucket", datetime(2023, 1, 1), "tencent")]
    )
    mock_provider.list_files.return_value = iter(
        [
            FileInfo("test-bucket", "archive.tar.gz", 1000, datetime(2023, 1, 1), "tencent"),
            FileInfo("test-bucket", "backup.gz", 500, datetime(2023, 1, 1), "tencent"),
        ]
    )

    scanner = BucketScanner(mock_provider)
    results = list(scanner.scan_file_types(".*", datetime(2024, 1, 1)))

    assert len(results) == 1
    assert results[0].extension == ".gz"
    assert results[0].file_count == 2
    assert results[0].total_size == 1500


def test_scan_file_types_applies_before_date(mock_provider: Mock) -> None:
    """Test that scan_file_types applies before_date filter."""
    mock_provider.list_buckets.return_value = iter(
        [BucketInfo("test-bucket", datetime(2023, 1, 1), "tencent")]
    )
    mock_provider.list_files.return_value = iter(
        [
            FileInfo("test-bucket", "old.log", 100, datetime(2023, 1, 1), "tencent"),
            FileInfo("test-bucket", "new.log", 200, datetime(2025, 1, 1), "tencent"),
        ]
    )

    scanner = BucketScanner(mock_provider)
    results = list(scanner.scan_file_types(".*", datetime(2024, 1, 1)))

    assert len(results) == 1
    assert results[0].file_count == 1
    assert results[0].total_size == 100


def test_scan_file_types_no_matching_buckets(mock_provider: Mock) -> None:
    """Test scan_file_types returns empty for no matching buckets."""
    mock_provider.list_buckets.return_value = iter(
        [BucketInfo("prod-bucket", datetime(2023, 1, 1), "tencent")]
    )

    scanner = BucketScanner(mock_provider)
    results = list(scanner.scan_file_types(r"^test-.*", datetime(2024, 1, 1)))

    assert results == []
    assert mock_provider.list_files.call_count == 0


def test_scan_file_types_no_files_before_date(mock_provider: Mock) -> None:
    """Test scan_file_types returns empty when no files are before date."""
    mock_provider.list_buckets.return_value = iter(
        [BucketInfo("test-bucket", datetime(2023, 1, 1), "tencent")]
    )
    mock_provider.list_files.return_value = iter(
        [
            FileInfo("test-bucket", "new.log", 100, datetime(2025, 6, 1), "tencent"),
        ]
    )

    scanner = BucketScanner(mock_provider)
    results = list(scanner.scan_file_types(".*", datetime(2024, 1, 1)))

    assert results == []


def test_scan_file_types_timezone_aware(mock_provider: Mock) -> None:
    """Test scan_file_types with timezone-aware datetimes."""
    mock_provider.list_buckets.return_value = iter(
        [BucketInfo("test-bucket", datetime(2023, 1, 1), "tencent")]
    )
    mock_provider.list_files.return_value = iter(
        [
            FileInfo(
                "test-bucket", "old.log", 100,
                datetime(2024, 6, 1, tzinfo=timezone.utc), "tencent",
            ),
            FileInfo(
                "test-bucket", "new.log", 200,
                datetime(2025, 6, 1, tzinfo=timezone.utc), "tencent",
            ),
        ]
    )

    scanner = BucketScanner(mock_provider)
    results = list(
        scanner.scan_file_types(".*", datetime(2025, 1, 1, tzinfo=timezone.utc))
    )

    assert len(results) == 1
    assert results[0].file_count == 1
    assert results[0].total_size == 100


def test_scanner_handles_timezone_aware_datetimes(mock_provider: Mock) -> None:
    """Test that scanner correctly handles timezone-aware datetimes from providers.

    This test ensures we can compare timezone-aware file modification times
    (from cloud providers) with timezone-aware filter dates (from CLI).
    Regression test for: can't compare offset-naive and offset-aware datetimes
    """
    mock_provider.list_buckets.return_value = iter(
        [BucketInfo("test-bucket", datetime(2023, 1, 1), "tencent")]
    )

    # Simulate timezone-aware datetimes from cloud provider (UTC)
    mock_provider.list_files.return_value = iter(
        [
            FileInfo(
                "test-bucket",
                "old.log",
                1024,
                datetime(2024, 6, 1, tzinfo=timezone.utc),  # Old file
                "tencent",
            ),
            FileInfo(
                "test-bucket",
                "new.log",
                1024,
                datetime(2025, 6, 1, tzinfo=timezone.utc),  # New file
                "tencent",
            ),
        ]
    )

    scanner = BucketScanner(mock_provider)
    # Filter date should also be timezone-aware (as fixed in CLI)
    deletion_filter = DeletionFilter(
        bucket_pattern=".*",
        file_pattern="*.log",
        before_date=datetime(2025, 1, 1, tzinfo=timezone.utc),
        provider="tencent",
    )

    results = list(scanner.scan(deletion_filter))

    # Should only return old.log (before 2025-01-01)
    assert len(results) == 1
    assert results[0].key == "old.log"
