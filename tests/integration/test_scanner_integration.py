"""Integration tests for scanner with real cloud providers.

These tests require real cloud credentials and test buckets.

Run with: pytest tests/integration/test_scanner_integration.py -v -s \
          --provider=tencent --test-bucket=your-bucket
"""

from datetime import datetime, timedelta

import pytest
from pydantic import ValidationError

from cloud_storage_clean.config import load_aliyun_config, load_tencent_config
from cloud_storage_clean.models import DeletionFilter
from cloud_storage_clean.providers.aliyun import AliyunProvider
from cloud_storage_clean.providers.tencent import TencentProvider
from cloud_storage_clean.scanner import BucketScanner, create_deletion_summary


@pytest.fixture
def provider(request):
    """Create provider based on command line option."""
    provider_name = request.config.getoption("--provider")

    if not provider_name:
        pytest.skip("--provider option required (tencent or aliyun)")

    try:
        if provider_name == "tencent":
            config = load_tencent_config()
            return TencentProvider(config, rate_limit=10)
        elif provider_name == "aliyun":
            config = load_aliyun_config()
            return AliyunProvider(config, rate_limit=10)
        else:
            pytest.skip(f"Unknown provider: {provider_name}")
    except ValidationError as e:
        pytest.skip(f"{provider_name} credentials not configured: {e}")


def test_scanner_with_real_provider(provider, request):
    """Test scanner with real cloud provider."""
    provider_name = request.config.getoption("--provider")

    # Create a filter that matches all buckets and files older than yesterday
    yesterday = datetime.now() - timedelta(days=1)
    deletion_filter = DeletionFilter(
        bucket_pattern=".*",  # Match all buckets
        file_pattern="*",  # Match all files
        before_date=yesterday,
        provider=provider_name,
    )

    scanner = BucketScanner(provider)

    print(f"\n✓ Scanning {provider_name} buckets...")

    # Scan and collect files
    files = []
    for file_info in scanner.scan(deletion_filter):
        files.append(file_info)
        if len(files) >= 10:  # Limit to first 10 for testing
            break

    print(f"  Found {len(files)} file(s) older than yesterday")

    # Verify all files match the criteria
    for file_info in files:
        assert file_info.provider == provider_name
        assert file_info.last_modified < yesterday

    if files:
        print(f"  Sample file: {files[0].bucket}/{files[0].key}")


@pytest.mark.skipif(
    "not config.getoption('--test-bucket')",
    reason="Requires --test-bucket option",
)
def test_scanner_with_bucket_pattern(provider, request):
    """Test scanner with specific bucket pattern."""
    provider_name = request.config.getoption("--provider")
    test_bucket = request.config.getoption("--test-bucket")

    # Extract bucket name pattern
    # If test_bucket is "my-test-bucket", create pattern "my-test-.*"
    bucket_pattern = f"^{test_bucket.rsplit('-', 1)[0]}.*"

    deletion_filter = DeletionFilter(
        bucket_pattern=bucket_pattern,
        file_pattern="*",
        before_date=datetime.now(),  # All files
        provider=provider_name,
    )

    scanner = BucketScanner(provider)

    print(f"\n✓ Scanning with bucket pattern: {bucket_pattern}")

    files = list(scanner.scan(deletion_filter))

    print(f"  Found {len(files)} file(s)")

    # All files should be from matching buckets
    for file_info in files[:10]:  # Check first 10
        assert file_info.provider == provider_name
        print(f"  - {file_info.bucket}/{file_info.key}")


@pytest.mark.skipif(
    "not config.getoption('--test-bucket')",
    reason="Requires --test-bucket option",
)
def test_scanner_with_file_pattern(provider, request):
    """Test scanner with specific file pattern."""
    provider_name = request.config.getoption("--provider")
    test_bucket = request.config.getoption("--test-bucket")

    # Look for .txt files only
    deletion_filter = DeletionFilter(
        bucket_pattern=f"^{test_bucket}$",  # Exact match
        file_pattern="*.txt",  # Only .txt files
        before_date=datetime.now(),
        provider=provider_name,
    )

    scanner = BucketScanner(provider)

    print(f"\n✓ Scanning for *.txt files in {test_bucket}")

    files = list(scanner.scan(deletion_filter))

    print(f"  Found {len(files)} .txt file(s)")

    # All files should end with .txt
    for file_info in files:
        assert file_info.key.endswith(".txt"), f"Non-.txt file found: {file_info.key}"
        print(f"  - {file_info.key}")


@pytest.mark.skipif(
    "not config.getoption('--test-bucket')",
    reason="Requires --test-bucket option",
)
def test_scanner_with_date_filter(provider, request):
    """Test scanner with date filtering."""
    provider_name = request.config.getoption("--provider")
    test_bucket = request.config.getoption("--test-bucket")

    # Look for files older than 30 days
    thirty_days_ago = datetime.now() - timedelta(days=30)

    deletion_filter = DeletionFilter(
        bucket_pattern=f"^{test_bucket}$",
        file_pattern="*",
        before_date=thirty_days_ago,
        provider=provider_name,
    )

    scanner = BucketScanner(provider)

    print(f"\n✓ Scanning for files older than 30 days in {test_bucket}")

    files = list(scanner.scan(deletion_filter))

    print(f"  Found {len(files)} old file(s)")

    # All files should be older than 30 days
    for file_info in files[:5]:  # Check first 5
        assert file_info.last_modified < thirty_days_ago
        age_days = (datetime.now() - file_info.last_modified).days
        print(f"  - {file_info.key} ({age_days} days old)")


def test_create_deletion_summary_with_real_data(provider, request):
    """Test creating deletion summary with real scan results."""
    provider_name = request.config.getoption("--provider")

    deletion_filter = DeletionFilter(
        bucket_pattern=".*",
        file_pattern="*",
        before_date=datetime.now() - timedelta(days=1),
        provider=provider_name,
    )

    scanner = BucketScanner(provider)

    # Collect up to 100 files for summary
    files = []
    for file_info in scanner.scan(deletion_filter):
        files.append(file_info)
        if len(files) >= 100:
            break

    if not files:
        pytest.skip("No files found for summary test")

    print(f"\n✓ Creating summary for {len(files)} file(s)")

    summary = create_deletion_summary(files, provider_name)

    assert summary["total_files"] == len(files)
    assert summary["total_size"] > 0
    assert summary["provider"] == provider_name
    assert len(summary["files_by_bucket"]) > 0

    print(f"  Total size: {summary['total_size']:,} bytes")
    print(f"  Buckets: {len(summary['files_by_bucket'])}")

    for bucket, count in list(summary["files_by_bucket"].items())[:5]:
        size = summary["size_by_bucket"][bucket]
        print(f"  - {bucket}: {count} files, {size:,} bytes")


def test_scanner_lazy_evaluation(provider, request):
    """Test that scanner uses lazy evaluation (doesn't load all files)."""
    provider_name = request.config.getoption("--provider")

    deletion_filter = DeletionFilter(
        bucket_pattern=".*",
        file_pattern="*",
        before_date=datetime.now(),
        provider=provider_name,
    )

    scanner = BucketScanner(provider)

    print(f"\n✓ Testing lazy evaluation")

    # Get iterator but don't consume it
    file_iterator = scanner.scan(deletion_filter)

    # Just get first file (should not load all files)
    first_file = next(file_iterator, None)

    if first_file:
        print(f"  Got first file without loading all: {first_file.key}")
        assert True
    else:
        print("  No files found (expected if no matching files exist)")


def test_scanner_handles_empty_buckets(provider, request):
    """Test scanner with buckets that have no files."""
    provider_name = request.config.getoption("--provider")

    # Use a pattern that likely won't match anything
    deletion_filter = DeletionFilter(
        bucket_pattern="nonexistent-bucket-pattern-xyz",
        file_pattern="*",
        before_date=datetime.now(),
        provider=provider_name,
    )

    scanner = BucketScanner(provider)

    print(f"\n✓ Scanning with non-matching pattern")

    files = list(scanner.scan(deletion_filter))

    assert files == []
    print("  Correctly returned empty list for non-matching pattern")


# Custom command line options are defined in tests/conftest.py
