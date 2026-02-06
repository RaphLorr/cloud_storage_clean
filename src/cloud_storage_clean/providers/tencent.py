"""Tencent COS provider implementation."""

from datetime import datetime
from typing import Iterator

from qcloud_cos import CosConfig, CosS3Client
from qcloud_cos.cos_exception import CosClientError, CosServiceError

from cloud_storage_clean.config import TencentConfig
from cloud_storage_clean.models import BucketInfo, DeletionResult, FileInfo
from cloud_storage_clean.providers.base import (
    AuthenticationError,
    BucketNotFoundError,
    CloudStorageError,
    CloudStorageProvider,
    RateLimitError,
)
from cloud_storage_clean.utils.logging import get_logger
from cloud_storage_clean.utils.rate_limiter import RateLimiter

logger = get_logger(__name__)


class TencentProvider(CloudStorageProvider):
    """Tencent COS storage provider."""

    def __init__(self, config: TencentConfig, rate_limit: int = 100) -> None:
        """Initialize Tencent COS provider.

        Args:
            config: Tencent configuration with credentials.
            rate_limit: Maximum API calls per second.
        """
        self.config = config
        self.rate_limiter = RateLimiter(rate=float(rate_limit))

        cos_config = CosConfig(
            Region=config.region,
            SecretId=config.secret_id.get_secret_value(),
            SecretKey=config.secret_key.get_secret_value(),
            Scheme=config.scheme,
        )
        self.client = CosS3Client(cos_config)
        self._bucket_regions: dict[str, str] = {}
        self._region_clients: dict[str, CosS3Client] = {config.region: self.client}
        logger.info("tencent_provider_initialized", region=config.region)

    def list_buckets(self) -> Iterator[BucketInfo]:
        """List all accessible buckets."""
        try:
            self.rate_limiter.acquire()
            response = self.client.list_buckets()

            for bucket in response.get("Buckets", {}).get("Bucket", []):
                location = bucket.get("Location")
                if location:
                    self._bucket_regions[bucket["Name"]] = location
                yield BucketInfo(
                    name=bucket["Name"],
                    creation_date=datetime.fromisoformat(
                        bucket["CreationDate"].replace("Z", "+00:00")
                    ),
                    provider="tencent",
                    region=location,
                )

        except CosServiceError as e:
            if e.get_error_code() == "AccessDenied":
                raise AuthenticationError(f"Authentication failed: {e.get_error_msg()}")
            raise CloudStorageError(f"Failed to list buckets: {e.get_error_msg()}")
        except CosClientError as e:
            raise CloudStorageError(f"Client error listing buckets: {str(e)}")

    def _get_client(self, bucket: str) -> CosS3Client:
        """Get a CosS3Client for the bucket's region.

        Uses cached region from list_buckets if available,
        falls back to the default client.
        """
        region = self._bucket_regions.get(bucket, self.config.region)
        if region not in self._region_clients:
            cos_config = CosConfig(
                Region=region,
                SecretId=self.config.secret_id.get_secret_value(),
                SecretKey=self.config.secret_key.get_secret_value(),
                Scheme=self.config.scheme,
            )
            self._region_clients[region] = CosS3Client(cos_config)
        return self._region_clients[region]

    def list_files(self, bucket: str, prefix: str = "") -> Iterator[FileInfo]:
        """List files in a bucket with pagination."""
        marker = ""
        has_more = True
        client = self._get_client(bucket)

        try:
            while has_more:
                self.rate_limiter.acquire()
                response = client.list_objects(
                    Bucket=bucket, Prefix=prefix, Marker=marker, MaxKeys=1000
                )

                contents = response.get("Contents", [])
                for obj in contents:
                    yield FileInfo(
                        bucket=bucket,
                        key=obj["Key"],
                        size=int(obj["Size"]),
                        last_modified=datetime.fromisoformat(
                            obj["LastModified"].replace("Z", "+00:00")
                        ),
                        provider="tencent",
                        storage_class=obj.get("StorageClass"),
                    )

                has_more = response.get("IsTruncated") == "true"
                if has_more:
                    marker = response.get("NextMarker", "")

        except CosServiceError as e:
            if e.get_error_code() == "NoSuchBucket":
                raise BucketNotFoundError(f"Bucket not found: {bucket}")
            if e.get_status_code() == 429:
                raise RateLimitError("Rate limit exceeded")
            raise CloudStorageError(f"Failed to list files in {bucket}: {e.get_error_msg()}")
        except CosClientError as e:
            raise CloudStorageError(f"Client error listing files: {str(e)}")

    def batch_delete(self, bucket: str, keys: list[str]) -> list[DeletionResult]:
        """Delete multiple files in a bucket.

        Tencent COS supports batch delete of up to 1000 objects per request.
        """
        if not keys:
            return []

        if len(keys) > 1000:
            raise ValueError("Tencent COS batch delete supports max 1000 keys")

        results: list[DeletionResult] = []

        try:
            self.rate_limiter.acquire()
            client = self._get_client(bucket)

            objects = {"Object": [{"Key": key} for key in keys]}
            response = client.delete_objects(Bucket=bucket, Delete=objects)

            # Track successful deletions
            deleted = {obj["Key"] for obj in response.get("Deleted", [])}

            # Process errors
            for error in response.get("Error", []):
                key = error["Key"]
                results.append(
                    DeletionResult(
                        file=FileInfo(
                            bucket=bucket,
                            key=key,
                            size=0,
                            last_modified=datetime.now(),
                            provider="tencent",
                        ),
                        success=False,
                        error=f"{error['Code']}: {error['Message']}",
                    )
                )

            # Add successful results
            for key in keys:
                if key in deleted:
                    results.append(
                        DeletionResult(
                            file=FileInfo(
                                bucket=bucket,
                                key=key,
                                size=0,
                                last_modified=datetime.now(),
                                provider="tencent",
                            ),
                            success=True,
                        )
                    )

            logger.info(
                "batch_delete_completed",
                bucket=bucket,
                total=len(keys),
                success=len(deleted),
                failed=len(results) - len(deleted),
            )

        except CosServiceError as e:
            if e.get_error_code() == "NoSuchBucket":
                raise BucketNotFoundError(f"Bucket not found: {bucket}")
            raise CloudStorageError(f"Batch delete failed: {e.get_error_msg()}")
        except CosClientError as e:
            raise CloudStorageError(f"Client error during batch delete: {str(e)}")

        return results
