"""Integration tests for Tencent COS provider.

These tests require real Tencent COS credentials.
Set up credentials in .env file before running.

Run with: pytest tests/integration/test_tencent_provider.py -v -s
"""

from datetime import datetime

import pytest
from pydantic import ValidationError

from cloud_storage_clean.config import load_tencent_config
from cloud_storage_clean.providers.base import (
    AuthenticationError,
    BucketNotFoundError,
)
from cloud_storage_clean.providers.tencent import TencentProvider


@pytest.fixture(scope="module")
def tencent_provider():
    """Create Tencent provider with real credentials."""
    try:
        config = load_tencent_config()
        return TencentProvider(config, rate_limit=10)
    except ValidationError as e:
        pytest.skip(f"Tencent credentials not configured: {e}")


def test_list_buckets_success(tencent_provider):
    """Test listing buckets with valid credentials."""
    buckets = list(tencent_provider.list_buckets())

    # Should return at least some buckets or empty list
    assert isinstance(buckets, list)

    if buckets:
        # Verify bucket structure
        bucket = buckets[0]
        assert hasattr(bucket, "name")
        assert hasattr(bucket, "creation_date")
        assert hasattr(bucket, "provider")
        assert bucket.provider == "tencent"
        assert isinstance(bucket.creation_date, datetime)
        print(f"\n✓ Found {len(buckets)} bucket(s)")
        print(f"  First bucket: {bucket.name}")


def test_list_buckets_with_invalid_credentials():
    """Test that invalid credentials raise AuthenticationError."""
    from cloud_storage_clean.config import TencentConfig
    from pydantic import SecretStr

    # Create config with invalid credentials
    config = TencentConfig(
        secret_id=SecretStr("invalid_id"),
        secret_key=SecretStr("invalid_key"),
    )
    provider = TencentProvider(config, rate_limit=10)

    with pytest.raises(AuthenticationError):
        list(provider.list_buckets())


def test_list_files_nonexistent_bucket(tencent_provider):
    """Test listing files from non-existent bucket."""
    with pytest.raises(BucketNotFoundError):
        list(tencent_provider.list_files("nonexistent-bucket-xyz-123"))


@pytest.mark.skipif(
    "not config.getoption('--test-bucket')",
    reason="Requires --test-bucket option with a real test bucket name",
)
def test_list_files_success(tencent_provider, request):
    """Test listing files from a real bucket.

    Run with: pytest tests/integration/test_tencent_provider.py::test_list_files_success \
              --test-bucket=your-test-bucket-name -v -s
    """
    test_bucket = request.config.getoption("--test-bucket")

    print(f"\n✓ Testing file listing in bucket: {test_bucket}")

    # List files (may be empty)
    files = list(tencent_provider.list_files(test_bucket))

    assert isinstance(files, list)
    print(f"  Found {len(files)} file(s)")

    if files:
        file = files[0]
        assert hasattr(file, "bucket")
        assert hasattr(file, "key")
        assert hasattr(file, "size")
        assert hasattr(file, "last_modified")
        assert hasattr(file, "provider")
        assert file.bucket == test_bucket
        assert file.provider == "tencent"
        assert isinstance(file.size, int)
        assert isinstance(file.last_modified, datetime)
        print(f"  First file: {file.key} ({file.size} bytes)")


@pytest.mark.skipif(
    "not config.getoption('--test-bucket')",
    reason="Requires --test-bucket option with a real test bucket name",
)
def test_list_files_with_prefix(tencent_provider, request):
    """Test listing files with prefix filter."""
    test_bucket = request.config.getoption("--test-bucket")

    # List all files
    all_files = list(tencent_provider.list_files(test_bucket))

    # List files with a prefix that shouldn't match anything
    filtered_files = list(
        tencent_provider.list_files(test_bucket, prefix="nonexistent-prefix/")
    )

    # Filtered should be <= all files
    assert len(filtered_files) <= len(all_files)
    print(f"\n✓ All files: {len(all_files)}, Filtered: {len(filtered_files)}")


@pytest.mark.skipif(
    "not config.getoption('--test-bucket') or not config.getoption('--enable-delete')",
    reason="Requires --test-bucket and --enable-delete flags for destructive tests",
)
def test_batch_delete_success(tencent_provider, request):
    """Test batch deletion of files.

    WARNING: This is a destructive test. Only run on test buckets!

    Run with: pytest tests/integration/test_tencent_provider.py::test_batch_delete_success \
              --test-bucket=your-test-bucket-name --enable-delete -v -s
    """
    test_bucket = request.config.getoption("--test-bucket")

    # This test requires manually created test files
    # Create test files in the bucket before running:
    # - test-delete-1.txt
    # - test-delete-2.txt

    test_keys = ["test-delete-1.txt", "test-delete-2.txt"]

    print(f"\n⚠️  WARNING: Attempting to delete files from {test_bucket}")
    print(f"  Files: {test_keys}")

    results = tencent_provider.batch_delete(test_bucket, test_keys)

    assert len(results) == len(test_keys)

    success_count = sum(1 for r in results if r.success)
    failed_count = len(results) - success_count

    print(f"  Deleted: {success_count}, Failed: {failed_count}")

    for result in results:
        if result.success:
            print(f"  ✓ {result.file.key}")
        else:
            print(f"  ✗ {result.file.key}: {result.error}")


def test_batch_delete_empty_list(tencent_provider):
    """Test that deleting empty list returns empty results."""
    results = tencent_provider.batch_delete("any-bucket", [])
    assert results == []


def test_batch_delete_too_many_keys(tencent_provider):
    """Test that batch delete rejects >1000 keys."""
    too_many_keys = [f"file-{i}.txt" for i in range(1001)]

    with pytest.raises(ValueError, match="max 1000 keys"):
        tencent_provider.batch_delete("any-bucket", too_many_keys)


def test_rate_limiter_integration(tencent_provider):
    """Test that rate limiter is working during actual API calls."""
    import time

    # Create provider with very low rate limit
    config = load_tencent_config()
    slow_provider = TencentProvider(config, rate_limit=2)  # 2 calls per second

    start = time.time()

    # Make 3 calls - should take at least 1 second due to rate limiting
    for _ in range(3):
        try:
            list(slow_provider.list_buckets())
        except Exception:
            pass  # Ignore errors, just testing rate limiting

    elapsed = time.time() - start

    # Should take at least 1 second (3 calls at 2/sec = 1.5 seconds minimum)
    assert elapsed >= 0.9, f"Rate limiter not working: {elapsed}s < 1s"
    print(f"\n✓ Rate limiter working: 3 calls took {elapsed:.2f}s (expected ~1.5s)")


# Custom command line options are defined in tests/conftest.py
