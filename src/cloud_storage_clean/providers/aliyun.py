"""Aliyun OSS provider implementation."""

from datetime import datetime, timezone
from typing import Iterator

import oss2
from oss2.exceptions import (
    NoSuchBucket,
    OssError,
    RequestError,
    ServerError,
)

from cloud_storage_clean.config import AliyunConfig
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


class AliyunProvider(CloudStorageProvider):
    """Aliyun OSS storage provider."""

    def __init__(self, config: AliyunConfig, rate_limit: int = 100) -> None:
        """Initialize Aliyun OSS provider.

        Args:
            config: Aliyun configuration with credentials.
            rate_limit: Maximum API calls per second.
        """
        self.config = config
        self.rate_limiter = RateLimiter(rate=float(rate_limit))

        auth = oss2.Auth(
            config.access_key_id.get_secret_value(),
            config.access_key_secret.get_secret_value(),
        )
        self.service = oss2.Service(auth, config.endpoint)
        self.auth = auth
        self._bucket_endpoints: dict[str, str] = {}
        logger.info("aliyun_provider_initialized", endpoint=config.endpoint)

    def list_buckets(self) -> Iterator[BucketInfo]:
        """List all accessible buckets."""
        try:
            self.rate_limiter.acquire()
            result = self.service.list_buckets()

            for bucket in result.buckets:
                if bucket.location:
                    endpoint = f"https://{bucket.location}.aliyuncs.com"
                    self._bucket_endpoints[bucket.name] = endpoint
                yield BucketInfo(
                    name=bucket.name,
                    creation_date=datetime.fromtimestamp(bucket.creation_date),
                    provider="aliyun",
                    region=bucket.location,
                )

        except oss2.exceptions.AccessDenied as e:
            raise AuthenticationError(f"Authentication failed: {str(e)}")
        except (ServerError, RequestError) as e:
            raise CloudStorageError(f"Failed to list buckets: {str(e)}")
        except OssError as e:
            raise CloudStorageError(f"OSS error listing buckets: {str(e)}")

    def _get_bucket_endpoint(self, bucket: str) -> str:
        """Get the correct endpoint for a bucket.

        Uses cached location from list_buckets if available,
        falls back to the configured default endpoint.
        """
        return self._bucket_endpoints.get(bucket, self.config.endpoint)

    def list_files(self, bucket: str, prefix: str = "") -> Iterator[FileInfo]:
        """List files in a bucket with pagination."""
        try:
            endpoint = self._get_bucket_endpoint(bucket)
            bucket_obj = oss2.Bucket(self.auth, endpoint, bucket)
            marker = ""
            has_more = True

            while has_more:
                self.rate_limiter.acquire()
                result = bucket_obj.list_objects(prefix=prefix, marker=marker, max_keys=1000)

                for obj in result.object_list:
                    yield FileInfo(
                        bucket=bucket,
                        key=obj.key,
                        size=obj.size,
                        last_modified=datetime.fromtimestamp(obj.last_modified, tz=timezone.utc),
                        provider="aliyun",
                        storage_class=obj.storage_class,
                    )

                has_more = result.is_truncated
                if has_more:
                    marker = result.next_marker

        except NoSuchBucket:
            raise BucketNotFoundError(f"Bucket not found: {bucket}")
        except oss2.exceptions.AccessDenied as e:
            raise AuthenticationError(f"Access denied to bucket {bucket}: {str(e)}")
        except ServerError as e:
            if e.status == 429:
                raise RateLimitError("Rate limit exceeded")
            raise CloudStorageError(f"Failed to list files in {bucket}: {str(e)}")
        except (RequestError, OssError) as e:
            raise CloudStorageError(f"Error listing files: {str(e)}")

    def batch_delete(self, bucket: str, keys: list[str]) -> list[DeletionResult]:
        """Delete multiple files in a bucket.

        Aliyun OSS supports batch delete of up to 1000 objects per request.
        """
        if not keys:
            return []

        if len(keys) > 1000:
            raise ValueError("Aliyun OSS batch delete supports max 1000 keys")

        results: list[DeletionResult] = []
        endpoint = self._get_bucket_endpoint(bucket)
        bucket_obj = oss2.Bucket(self.auth, endpoint, bucket)

        try:
            self.rate_limiter.acquire()
            result = bucket_obj.batch_delete_objects(keys)

            # Aliyun returns list of successfully deleted keys
            deleted_set = set(result.deleted_keys)

            for key in keys:
                if key in deleted_set:
                    results.append(
                        DeletionResult(
                            file=FileInfo(
                                bucket=bucket,
                                key=key,
                                size=0,
                                last_modified=datetime.now(),
                                provider="aliyun",
                            ),
                            success=True,
                        )
                    )
                else:
                    results.append(
                        DeletionResult(
                            file=FileInfo(
                                bucket=bucket,
                                key=key,
                                size=0,
                                last_modified=datetime.now(),
                                provider="aliyun",
                            ),
                            success=False,
                            error="Key not in deleted list",
                        )
                    )

            logger.info(
                "batch_delete_completed",
                bucket=bucket,
                total=len(keys),
                success=len(deleted_set),
                failed=len(keys) - len(deleted_set),
            )

        except NoSuchBucket:
            raise BucketNotFoundError(f"Bucket not found: {bucket}")
        except oss2.exceptions.AccessDenied as e:
            raise AuthenticationError(f"Access denied: {str(e)}")
        except (ServerError, RequestError, OssError) as e:
            raise CloudStorageError(f"Batch delete failed: {str(e)}")

        return results
