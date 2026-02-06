"""Pytest configuration and fixtures."""

from datetime import datetime

import pytest

from cloud_storage_clean.models import FileInfo


def pytest_addoption(parser):
    """Add custom command line options for integration tests."""
    parser.addoption(
        "--provider",
        action="store",
        default=None,
        help="Cloud provider for integration tests (tencent or aliyun)",
    )
    parser.addoption(
        "--test-bucket",
        action="store",
        default=None,
        help="Test bucket name for integration tests",
    )
    parser.addoption(
        "--enable-delete",
        action="store_true",
        default=False,
        help="Enable destructive delete tests (use with caution!)",
    )


@pytest.fixture
def sample_files() -> list[FileInfo]:
    """Create list of sample files for testing."""
    return [
        FileInfo(
            bucket="test-bucket-1",
            key="file1.log",
            size=1024,
            last_modified=datetime(2023, 1, 1),
            provider="tencent",
        ),
        FileInfo(
            bucket="test-bucket-1",
            key="file2.log",
            size=2048,
            last_modified=datetime(2023, 2, 1),
            provider="tencent",
        ),
        FileInfo(
            bucket="test-bucket-2",
            key="file3.txt",
            size=512,
            last_modified=datetime(2023, 3, 1),
            provider="tencent",
        ),
    ]
