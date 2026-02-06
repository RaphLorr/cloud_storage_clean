"""Unit tests for data models."""

from datetime import datetime

import pytest

from cloud_storage_clean.models import (
    BucketInfo,
    DeletionFilter,
    DeletionResult,
    DeletionSummary,
    FileInfo,
    FileTypeSummary,
)


def test_deletion_filter_immutable() -> None:
    """Test that DeletionFilter is immutable."""
    filter_obj = DeletionFilter(
        bucket_pattern="test-.*",
        file_pattern="*.log",
        before_date=datetime(2024, 1, 1),
        provider="tencent",
    )

    with pytest.raises(AttributeError):
        filter_obj.bucket_pattern = "new-pattern"  # type: ignore


def test_bucket_info_immutable() -> None:
    """Test that BucketInfo is immutable."""
    bucket = BucketInfo(
        name="test-bucket",
        creation_date=datetime(2023, 1, 1),
        provider="tencent",
    )

    with pytest.raises(AttributeError):
        bucket.name = "new-name"  # type: ignore


def test_file_info_immutable() -> None:
    """Test that FileInfo is immutable."""
    file_info = FileInfo(
        bucket="test-bucket",
        key="test.log",
        size=1024,
        last_modified=datetime(2023, 1, 1),
        provider="tencent",
    )

    with pytest.raises(AttributeError):
        file_info.size = 2048  # type: ignore


def test_deletion_result_default_timestamp() -> None:
    """Test that DeletionResult has default timestamp."""
    file_info = FileInfo(
        bucket="test-bucket",
        key="test.log",
        size=1024,
        last_modified=datetime(2023, 1, 1),
        provider="tencent",
    )

    result = DeletionResult(file=file_info, success=True)

    assert result.timestamp is not None
    assert isinstance(result.timestamp, datetime)


def test_deletion_summary_format_size() -> None:
    """Test size formatting in DeletionSummary."""
    summary = DeletionSummary(
        total_files=10,
        total_size=0,
        files_by_bucket={},
        size_by_bucket={},
        provider="tencent",
    )

    # Test various sizes
    assert summary.format_size(512) == "512.00 B"
    assert summary.format_size(1024) == "1.00 KB"
    assert summary.format_size(1024 * 1024) == "1.00 MB"
    assert summary.format_size(1024 * 1024 * 1024) == "1.00 GB"
    assert summary.format_size(1024 * 1024 * 1024 * 1024) == "1.00 TB"


def test_deletion_summary_format_size_precision() -> None:
    """Test size formatting precision."""
    summary = DeletionSummary(
        total_files=1,
        total_size=0,
        files_by_bucket={},
        size_by_bucket={},
        provider="tencent",
    )

    assert summary.format_size(1536) == "1.50 KB"
    assert summary.format_size(1024 * 1024 + 512 * 1024) == "1.50 MB"


def test_file_type_summary_construction() -> None:
    """Test FileTypeSummary construction."""
    summary = FileTypeSummary(
        bucket="test-bucket",
        extension=".log",
        file_count=42,
        total_size=1024 * 1024,
    )

    assert summary.bucket == "test-bucket"
    assert summary.extension == ".log"
    assert summary.file_count == 42
    assert summary.total_size == 1024 * 1024


def test_file_type_summary_immutable() -> None:
    """Test that FileTypeSummary is immutable."""
    summary = FileTypeSummary(
        bucket="test-bucket",
        extension=".log",
        file_count=42,
        total_size=1024,
    )

    with pytest.raises(AttributeError):
        summary.file_count = 100  # type: ignore
