"""Unit tests for deleter."""

from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from cloud_storage_clean.deleter import SafeDeleter
from cloud_storage_clean.models import DeletionResult, FileInfo


@pytest.fixture
def mock_provider() -> Mock:
    """Create mock provider."""
    return Mock()


def test_deleter_initialization(mock_provider: Mock) -> None:
    """Test deleter initialization."""
    deleter = SafeDeleter(mock_provider, batch_size=50)
    assert deleter.provider == mock_provider
    assert deleter.batch_size == 50


def test_deleter_batch_size_limit(mock_provider: Mock) -> None:
    """Test that batch size is limited to 1000."""
    deleter = SafeDeleter(mock_provider, batch_size=2000)
    assert deleter.batch_size == 1000


def test_create_summary(mock_provider: Mock, sample_files: list[FileInfo]) -> None:
    """Test creating deletion summary."""
    deleter = SafeDeleter(mock_provider)
    summary = deleter.create_summary(sample_files)

    assert summary.total_files == 3
    assert summary.total_size == 3584
    assert summary.files_by_bucket["test-bucket-1"] == 2
    assert summary.files_by_bucket["test-bucket-2"] == 1
    assert summary.provider == "tencent"


def test_delete_empty_list(mock_provider: Mock) -> None:
    """Test deletion with empty file list."""
    deleter = SafeDeleter(mock_provider)
    results = list(deleter.delete([]))

    assert len(results) == 0
    mock_provider.batch_delete.assert_not_called()


@patch("cloud_storage_clean.deleter.console")
def test_delete_with_confirmation(
    mock_console: Mock, mock_provider: Mock, sample_files: list[FileInfo]
) -> None:
    """Test deletion with user confirmation."""
    mock_console.input.return_value = "yes"
    mock_provider.batch_delete.return_value = [
        DeletionResult(file=sample_files[0], success=True),
        DeletionResult(file=sample_files[1], success=True),
    ]

    deleter = SafeDeleter(mock_provider)

    # Only pass files from one bucket for simplicity
    files = sample_files[:2]
    results = list(deleter.delete(files, skip_confirmation=False))

    # Should prompt for confirmation
    mock_console.input.assert_called_once()

    # Should call batch_delete
    mock_provider.batch_delete.assert_called_once()
    assert len(results) == 2


@patch("cloud_storage_clean.deleter.console")
def test_delete_cancelled(
    mock_console: Mock, mock_provider: Mock, sample_files: list[FileInfo]
) -> None:
    """Test deletion cancelled by user."""
    mock_console.input.return_value = "no"

    deleter = SafeDeleter(mock_provider)
    results = list(deleter.delete(sample_files, skip_confirmation=False))

    assert len(results) == 0
    mock_provider.batch_delete.assert_not_called()


def test_delete_skip_confirmation(mock_provider: Mock, sample_files: list[FileInfo]) -> None:
    """Test deletion with skipped confirmation."""
    mock_provider.batch_delete.return_value = [
        DeletionResult(file=sample_files[0], success=True),
        DeletionResult(file=sample_files[1], success=True),
    ]

    deleter = SafeDeleter(mock_provider)
    files = sample_files[:2]

    results = list(deleter.delete(files, skip_confirmation=True))

    # Should not prompt, directly delete
    mock_provider.batch_delete.assert_called_once()
    assert len(results) == 2


def test_delete_groups_by_bucket(mock_provider: Mock) -> None:
    """Test that deletion groups files by bucket."""
    files = [
        FileInfo("bucket-1", "file1.log", 1024, datetime(2023, 1, 1), "tencent"),
        FileInfo("bucket-2", "file2.log", 1024, datetime(2023, 1, 1), "tencent"),
        FileInfo("bucket-1", "file3.log", 1024, datetime(2023, 1, 1), "tencent"),
    ]

    mock_provider.batch_delete.return_value = [
        DeletionResult(file=files[0], success=True),
        DeletionResult(file=files[2], success=True),
    ]

    deleter = SafeDeleter(mock_provider)
    list(deleter.delete(files, skip_confirmation=True))

    # Should call batch_delete twice (once per bucket)
    assert mock_provider.batch_delete.call_count == 2


def test_delete_batches_large_lists(mock_provider: Mock) -> None:
    """Test that deletion batches large file lists."""
    # Create 250 files for one bucket
    files = [
        FileInfo("bucket-1", f"file{i}.log", 1024, datetime(2023, 1, 1), "tencent")
        for i in range(250)
    ]

    mock_provider.batch_delete.return_value = [
        DeletionResult(file=f, success=True) for f in files[:100]
    ]

    deleter = SafeDeleter(mock_provider, batch_size=100)
    list(deleter.delete(files, skip_confirmation=True))

    # Should call batch_delete 3 times (100 + 100 + 50)
    assert mock_provider.batch_delete.call_count == 3


def test_delete_handles_errors(mock_provider: Mock) -> None:
    """Test that deletion handles errors gracefully."""
    files = [
        FileInfo("bucket-1", "file1.log", 1024, datetime(2023, 1, 1), "tencent"),
        FileInfo("bucket-1", "file2.log", 1024, datetime(2023, 1, 1), "tencent"),
    ]

    # Simulate batch_delete raising exception
    mock_provider.batch_delete.side_effect = Exception("API error")

    deleter = SafeDeleter(mock_provider)
    results = list(deleter.delete(files, skip_confirmation=True))

    # Should return failure results for all files
    assert len(results) == 2
    assert all(not r.success for r in results)
    assert all("API error" in r.error for r in results if r.error)


def test_delete_dry_run_mode(mock_provider: Mock, sample_files: list[FileInfo]) -> None:
    """Test deletion in dry-run mode - no actual deletions."""
    # Create deleter with dry_run=True
    deleter = SafeDeleter(mock_provider, dry_run=True)

    files = sample_files[:2]
    results = list(deleter.delete(files, skip_confirmation=True))

    # Should NOT call provider.batch_delete
    mock_provider.batch_delete.assert_not_called()

    # Should still return results
    assert len(results) == 2

    # All results should be successful
    assert all(r.success for r in results)

    # Results should be for the correct files
    assert results[0].file.key == files[0].key
    assert results[1].file.key == files[1].key


@patch("cloud_storage_clean.deleter.console")
def test_delete_dry_run_shows_indicator(
    mock_console: Mock, mock_provider: Mock, sample_files: list[FileInfo]
) -> None:
    """Test that dry-run mode displays clear indicator."""
    deleter = SafeDeleter(mock_provider, dry_run=True)

    list(deleter.delete(sample_files[:2], skip_confirmation=True))

    # Check console was called with dry-run indicator
    console_calls = [str(call) for call in mock_console.print.call_args_list]
    dry_run_indicator_shown = any("DRY RUN" in call for call in console_calls)

    assert dry_run_indicator_shown, "Dry-run indicator not shown in console output"
