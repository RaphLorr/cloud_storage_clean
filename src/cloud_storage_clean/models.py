"""Immutable data models for cloud storage operations."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class DeletionFilter:
    """Criteria for filtering files to delete."""

    bucket_pattern: str
    file_pattern: str
    before_date: datetime
    provider: str


@dataclass(frozen=True)
class BucketInfo:
    """Information about a storage bucket."""

    name: str
    creation_date: datetime
    provider: str
    region: Optional[str] = None


@dataclass(frozen=True)
class FileInfo:
    """Information about a file in cloud storage."""

    bucket: str
    key: str
    size: int
    last_modified: datetime
    provider: str
    storage_class: Optional[str] = None


@dataclass(frozen=True)
class DeletionResult:
    """Result of a file deletion operation."""

    file: FileInfo
    success: bool
    error: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass(frozen=True)
class DeletionSummary:
    """Summary of planned deletion operation."""

    total_files: int
    total_size: int
    files_by_bucket: dict[str, int]
    size_by_bucket: dict[str, int]
    provider: str

    def format_size(self, size_bytes: int) -> str:
        """Format size in bytes to human-readable format."""
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} PB"
