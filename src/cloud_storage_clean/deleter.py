"""Safe deletion orchestration with confirmation."""

from collections import defaultdict
from typing import Iterator

from rich.console import Console
from rich.table import Table

from cloud_storage_clean.models import DeletionResult, DeletionSummary, FileInfo
from cloud_storage_clean.providers.base import CloudStorageProvider
from cloud_storage_clean.utils.logging import get_logger

logger = get_logger(__name__)
console = Console()


class SafeDeleter:
    """Orchestrates safe deletion with user confirmation."""

    def __init__(
        self,
        provider: CloudStorageProvider,
        batch_size: int = 100,
        dry_run: bool = False,
    ) -> None:
        """Initialize deleter.

        Args:
            provider: Cloud storage provider instance.
            batch_size: Maximum files per batch deletion.
            dry_run: If True, simulate deletion without actual API calls.
        """
        self.provider = provider
        self.batch_size = min(batch_size, 1000)  # Never exceed provider limits
        self.dry_run = dry_run

    def create_summary(self, files: list[FileInfo]) -> DeletionSummary:
        """Create summary statistics from files.

        Args:
            files: List of files to be deleted.

        Returns:
            DeletionSummary with statistics.
        """
        files_by_bucket: dict[str, int] = defaultdict(int)
        size_by_bucket: dict[str, int] = defaultdict(int)
        total_size = 0

        for file_info in files:
            files_by_bucket[file_info.bucket] += 1
            size_by_bucket[file_info.bucket] += file_info.size
            total_size += file_info.size

        return DeletionSummary(
            total_files=len(files),
            total_size=total_size,
            files_by_bucket=dict(files_by_bucket),
            size_by_bucket=dict(size_by_bucket),
            provider=files[0].provider if files else "unknown",
        )

    def display_summary(self, summary: DeletionSummary) -> None:
        """Display deletion summary as a formatted table.

        Args:
            summary: Deletion summary to display.
        """
        console.print("\n[bold yellow]⚠ Deletion Summary[/bold yellow]\n")

        # Overall statistics
        console.print(f"[cyan]Total files:[/cyan] {summary.total_files}")
        console.print(
            f"[cyan]Total size:[/cyan] {summary.format_size(summary.total_size)}"
        )
        console.print(f"[cyan]Provider:[/cyan] {summary.provider}\n")

        # Per-bucket breakdown
        table = Table(title="Files by Bucket")
        table.add_column("Bucket", style="cyan")
        table.add_column("File Count", justify="right", style="magenta")
        table.add_column("Total Size", justify="right", style="green")

        for bucket in sorted(summary.files_by_bucket.keys()):
            file_count = summary.files_by_bucket[bucket]
            size = summary.size_by_bucket[bucket]
            table.add_row(bucket, str(file_count), summary.format_size(size))

        console.print(table)
        console.print()

    def confirm_deletion(self) -> bool:
        """Prompt user for deletion confirmation.

        Returns:
            True if user confirms, False otherwise.
        """
        console.print("[bold red]⚠ This action cannot be undone![/bold red]")
        response = console.input("[yellow]Proceed with deletion? (yes/no):[/yellow] ")
        return response.lower() in ("yes", "y")

    def delete(
        self, files: list[FileInfo], skip_confirmation: bool = False
    ) -> Iterator[DeletionResult]:
        """Delete files with confirmation and progress tracking.

        Args:
            files: List of files to delete.
            skip_confirmation: If True, skip user confirmation prompt.

        Yields:
            DeletionResult for each file.

        Raises:
            CloudStorageError: If deletion fails critically.
        """
        if not files:
            logger.info("no_files_to_delete")
            return

        # Create and display summary
        summary = self.create_summary(files)
        self.display_summary(summary)

        # Display dry-run indicator
        if self.dry_run:
            console.print(
                "\n[yellow]🔍 DRY RUN MODE - No files will be deleted[/yellow]"
            )

        # Get confirmation unless skipped
        if not skip_confirmation:
            if not self.confirm_deletion():
                logger.info("deletion_cancelled_by_user")
                console.print("[yellow]Deletion cancelled.[/yellow]")
                return

        logger.info("deletion_started", total_files=len(files))
        console.print("\n[green]Starting deletion...[/green]\n")

        # Group files by bucket
        files_by_bucket: dict[str, list[FileInfo]] = defaultdict(list)
        for file_info in files:
            files_by_bucket[file_info.bucket].append(file_info)

        # Delete bucket by bucket
        total_success = 0
        total_failed = 0

        for bucket, bucket_files in files_by_bucket.items():
            logger.info("deleting_bucket", bucket=bucket, file_count=len(bucket_files))

            # Process in batches
            for i in range(0, len(bucket_files), self.batch_size):
                batch = bucket_files[i : i + self.batch_size]
                keys = [f.key for f in batch]

                try:
                    if self.dry_run:
                        # Simulate successful deletion
                        results = [
                            DeletionResult(file=file_info, success=True)
                            for file_info in batch
                        ]
                        logger.info(
                            "dry_run_simulated_batch",
                            bucket=bucket,
                            file_count=len(batch),
                        )
                    else:
                        # Real deletion
                        results = self.provider.batch_delete(bucket, keys)

                    for result in results:
                        if result.success:
                            total_success += 1
                            logger.info(
                                "file_deleted"
                                if not self.dry_run
                                else "file_would_be_deleted",
                                bucket=result.file.bucket,
                                key=result.file.key,
                                dry_run=self.dry_run,
                            )
                        else:
                            total_failed += 1
                            logger.error(
                                "file_delete_failed",
                                bucket=result.file.bucket,
                                key=result.file.key,
                                error=result.error,
                            )

                        yield result

                except Exception as e:
                    logger.error("batch_delete_error", bucket=bucket, error=str(e))
                    # Create failure results for batch
                    for file_info in batch:
                        total_failed += 1
                        yield DeletionResult(
                            file=file_info, success=False, error=str(e)
                        )

        logger.info(
            "deletion_completed",
            total_files=len(files),
            success=total_success,
            failed=total_failed,
            dry_run=self.dry_run,
        )

        if self.dry_run:
            console.print(
                f"\n[green]✓ Dry run completed: {total_success} files would be deleted[/green]"
            )
        else:
            console.print(f"\n[green]✓ Successfully deleted: {total_success}[/green]")

        if total_failed > 0:
            console.print(f"[red]✗ Failed: {total_failed}[/red]")
