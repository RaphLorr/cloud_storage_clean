"""CLI interface using Typer and Rich."""

from datetime import datetime, timezone
from itertools import groupby
from operator import attrgetter
from typing import Optional
from zoneinfo import ZoneInfo

import typer
from pydantic import ValidationError
from rich.console import Console
from rich.table import Table

from cloud_storage_clean.config import (
    load_aliyun_config,
    load_app_config,
    load_tencent_config,
)
from cloud_storage_clean.deleter import SafeDeleter
from cloud_storage_clean.models import DeletionFilter, DeletionSummary
from cloud_storage_clean.providers.aliyun import AliyunProvider
from cloud_storage_clean.providers.base import CloudStorageError, CloudStorageProvider
from cloud_storage_clean.providers.tencent import TencentProvider
from cloud_storage_clean.scanner import BucketScanner
from cloud_storage_clean.utils.logging import configure_logging, get_logger

app = typer.Typer(help="Cloud Storage Cleanup Tool")
console = Console()


def create_provider(provider_name: str, rate_limit: int) -> CloudStorageProvider:
    """Create provider instance based on name.

    Args:
        provider_name: Provider name ('tencent' or 'aliyun').
        rate_limit: Maximum API calls per second.

    Returns:
        Configured provider instance.

    Raises:
        typer.Exit: If configuration is invalid.
    """
    try:
        if provider_name == "tencent":
            config = load_tencent_config()
            return TencentProvider(config, rate_limit)
        elif provider_name == "aliyun":
            config = load_aliyun_config()
            return AliyunProvider(config, rate_limit)
        else:
            console.print(f"[red]Error: Unknown provider '{provider_name}'[/red]")
            raise typer.Exit(1)
    except ValidationError as e:
        console.print(f"[red]Configuration error:[/red]\n{e}")
        raise typer.Exit(1)


@app.command()
def clean(
    provider: str,
    bucket_pattern: str,
    file_pattern: str,
    before: str,
    no_confirm: bool = typer.Option(False, "--no-confirm"),
    dry_run: bool = typer.Option(False, "--dry-run"),
    tz: Optional[str] = typer.Option(None, "--timezone", "--tz", help="Timezone for date (e.g., 'Asia/Shanghai', 'UTC', default: local timezone)"),
    log_file: Optional[str] = typer.Option(None, "--log-file"),
    verbose: bool = typer.Option(False, "--verbose"),
) -> None:
    """Delete files from cloud storage based on patterns and time criteria.

    Args:
        provider: Cloud provider (tencent or aliyun)
        bucket_pattern: Regex pattern for bucket names
        file_pattern: Glob pattern for file names
        before: Delete files modified before this date (YYYY-MM-DD)
        no_confirm: Skip confirmation prompt (dangerous)
        dry_run: Simulate deletion without actually deleting files
        tz: Timezone for the date (e.g., 'Asia/Shanghai' for Beijing time)
        log_file: Path to log file
        verbose: Enable verbose logging

    Example:
        cloud-storage-clean clean tencent "test-.*" "*.log" 2024-01-01 --dry-run
        cloud-storage-clean clean tencent "test-.*" "*.log" 2024-01-01 --timezone Asia/Shanghai
    """
    # Configure logging
    configure_logging(log_file, verbose)
    logger = get_logger(__name__)

    try:
        # Parse date with timezone
        try:
            naive_date = datetime.strptime(before, "%Y-%m-%d")

            # Determine timezone
            if tz:
                try:
                    tz_info = ZoneInfo(tz)
                except Exception:
                    console.print(f"[red]Error: Invalid timezone '{tz}'. Use IANA timezone names like 'Asia/Shanghai' or 'UTC'[/red]")
                    raise typer.Exit(1)
            else:
                # Use local timezone by default
                tz_info = datetime.now().astimezone().tzinfo
                logger.info("using_local_timezone", timezone=str(tz_info))

            before_date = naive_date.replace(tzinfo=tz_info)

        except ValueError:
            console.print("[red]Error: Invalid date format. Use YYYY-MM-DD[/red]")
            raise typer.Exit(1)

        # Load app config
        app_config = load_app_config()

        # Create provider
        logger.info("initializing_provider", provider=provider)
        provider_instance = create_provider(provider, app_config.rate_limit)

        # Create filter
        deletion_filter = DeletionFilter(
            bucket_pattern=bucket_pattern,
            file_pattern=file_pattern,
            before_date=before_date,
            provider=provider,
        )

        logger.info("starting_scan", filter=deletion_filter)
        console.print("[cyan]Scanning for files...[/cyan]")

        # Scan for files
        scanner = BucketScanner(provider_instance)
        files = list(scanner.scan(deletion_filter))

        if not files:
            console.print("[yellow]No files found matching criteria.[/yellow]")
            logger.info("no_files_found")
            return

        console.print(f"[green]Found {len(files)} files matching criteria.[/green]")

        # Delete files
        deleter = SafeDeleter(provider_instance, app_config.batch_size, dry_run=dry_run)
        results = list(deleter.delete(files, skip_confirmation=no_confirm))

        # Log final summary
        success_count = sum(1 for r in results if r.success)
        failed_count = len(results) - success_count

        logger.info(
            "operation_completed",
            total=len(results),
            success=success_count,
            failed=failed_count,
        )

    except CloudStorageError as e:
        console.print(f"[red]Cloud storage error: {str(e)}[/red]")
        logger.error("cloud_storage_error", error=str(e))
        raise typer.Exit(1)
    except ValueError as e:
        console.print(f"[red]Validation error: {str(e)}[/red]")
        logger.error("validation_error", error=str(e))
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Unexpected error: {str(e)}[/red]")
        logger.exception("unexpected_error")
        raise typer.Exit(1)


@app.command()
def list_buckets(
    provider: str,
    pattern: Optional[str] = typer.Option(None, "--pattern"),
    verbose: bool = typer.Option(False, "--verbose"),
) -> None:
    """List all accessible buckets.

    Args:
        provider: Cloud provider (tencent or aliyun)
        pattern: Optional regex pattern to filter buckets
        verbose: Enable verbose logging

    Example:
        cloud-storage-clean list-buckets tencent --pattern "test-.*"
    """
    # Configure logging
    configure_logging(None, verbose)
    logger = get_logger(__name__)

    try:
        # Load app config
        app_config = load_app_config()

        # Create provider
        logger.info("initializing_provider", provider=provider)
        provider_instance = create_provider(provider, app_config.rate_limit)

        console.print(f"[cyan]Listing buckets for provider: {provider}[/cyan]\n")

        # Compile pattern if provided
        compiled_pattern = None
        if pattern:
            from cloud_storage_clean.utils.validators import compile_regex

            try:
                compiled_pattern = compile_regex(pattern)
            except ValueError as e:
                console.print(f"[red]Invalid pattern: {e}[/red]")
                raise typer.Exit(1)

        # List buckets
        bucket_count = 0
        for bucket_info in provider_instance.list_buckets():
            if compiled_pattern:
                from cloud_storage_clean.utils.validators import matches_regex

                if not matches_regex(bucket_info.name, compiled_pattern):
                    continue

            bucket_count += 1
            console.print(
                f"[green]•[/green] {bucket_info.name} "
                f"(created: {bucket_info.creation_date.strftime('%Y-%m-%d')})"
            )
            if bucket_info.region:
                console.print(f"  [dim]Region: {bucket_info.region}[/dim]")

        console.print(f"\n[cyan]Total buckets: {bucket_count}[/cyan]")
        logger.info("list_buckets_completed", count=bucket_count)

    except CloudStorageError as e:
        console.print(f"[red]Cloud storage error: {str(e)}[/red]")
        logger.error("cloud_storage_error", error=str(e))
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Unexpected error: {str(e)}[/red]")
        logger.exception("unexpected_error")
        raise typer.Exit(1)


@app.command(name="list-files")
def list_files(
    provider: str,
    bucket_pattern: str,
    file_pattern: str,
    before: str,
    tz: Optional[str] = typer.Option(None, "--timezone", "--tz", help="Timezone for date (e.g., 'Asia/Shanghai', 'UTC', default: local timezone)"),
    verbose: bool = typer.Option(False, "--verbose"),
) -> None:
    """List files matching patterns and time criteria.

    Example:
        cloud-storage-clean list-files tencent "test-.*" "*.mp4" 2025-01-01
        cloud-storage-clean list-files aliyun "prod-.*" "*.log" 2024-06-01 --timezone Asia/Shanghai
    """
    configure_logging(None, verbose)
    logger = get_logger(__name__)

    try:
        # Parse date with timezone
        try:
            naive_date = datetime.strptime(before, "%Y-%m-%d")

            if tz:
                try:
                    tz_info = ZoneInfo(tz)
                except Exception:
                    console.print(f"[red]Error: Invalid timezone '{tz}'. Use IANA timezone names like 'Asia/Shanghai' or 'UTC'[/red]")
                    raise typer.Exit(1)
            else:
                tz_info = datetime.now().astimezone().tzinfo
                logger.info("using_local_timezone", timezone=str(tz_info))

            before_date = naive_date.replace(tzinfo=tz_info)

        except ValueError:
            console.print("[red]Error: Invalid date format. Use YYYY-MM-DD[/red]")
            raise typer.Exit(1)

        app_config = load_app_config()
        provider_instance = create_provider(provider, app_config.rate_limit)

        console.print("[cyan]Scanning for files...[/cyan]\n")

        scanner = BucketScanner(provider_instance)
        deletion_filter = DeletionFilter(
            bucket_pattern=bucket_pattern,
            file_pattern=file_pattern,
            before_date=before_date,
            provider=provider,
        )
        files = list(scanner.scan(deletion_filter))

        if not files:
            console.print("[yellow]No files found matching criteria.[/yellow]")
            return

        # Render a table per bucket
        total_size = 0

        for bucket_name, bucket_group in groupby(files, key=attrgetter("bucket")):
            table = Table(title=f"Bucket: {bucket_name}")
            table.add_column("Key", style="cyan")
            table.add_column("Size", justify="right", style="green")
            table.add_column("Last Modified", style="magenta")

            for f in bucket_group:
                table.add_row(
                    f.key,
                    DeletionSummary.format_size(f.size),
                    f.last_modified.strftime("%Y-%m-%d %H:%M:%S"),
                )
                total_size += f.size

            console.print(table)
            console.print()

        console.print(
            f"[bold]Total: {len(files)} files, "
            f"{DeletionSummary.format_size(total_size)}[/bold]"
        )

        logger.info(
            "list_files_completed",
            total_files=len(files),
            total_size=total_size,
        )

    except CloudStorageError as e:
        console.print(f"[red]Cloud storage error: {str(e)}[/red]")
        logger.error("cloud_storage_error", error=str(e))
        raise typer.Exit(1)
    except ValueError as e:
        console.print(f"[red]Validation error: {str(e)}[/red]")
        logger.error("validation_error", error=str(e))
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Unexpected error: {str(e)}[/red]")
        logger.exception("unexpected_error")
        raise typer.Exit(1)


@app.command()
def stat(
    provider: str,
    bucket_pattern: str,
    before: str,
    tz: Optional[str] = typer.Option(None, "--timezone", "--tz", help="Timezone for date (e.g., 'Asia/Shanghai', 'UTC', default: local timezone)"),
    verbose: bool = typer.Option(False, "--verbose"),
) -> None:
    """Show file type statistics for files modified before a given date.

    Displays a per-bucket breakdown of file types (by extension) with
    file counts and total sizes.

    Example:
        cloud-storage-clean stat tencent "test-.*" 2024-01-01
        cloud-storage-clean stat aliyun "prod-.*" 2025-06-01 --timezone Asia/Shanghai
    """
    configure_logging(None, verbose)
    logger = get_logger(__name__)

    try:
        # Parse date with timezone
        try:
            naive_date = datetime.strptime(before, "%Y-%m-%d")

            if tz:
                try:
                    tz_info = ZoneInfo(tz)
                except Exception:
                    console.print(f"[red]Error: Invalid timezone '{tz}'. Use IANA timezone names like 'Asia/Shanghai' or 'UTC'[/red]")
                    raise typer.Exit(1)
            else:
                tz_info = datetime.now().astimezone().tzinfo
                logger.info("using_local_timezone", timezone=str(tz_info))

            before_date = naive_date.replace(tzinfo=tz_info)

        except ValueError:
            console.print("[red]Error: Invalid date format. Use YYYY-MM-DD[/red]")
            raise typer.Exit(1)

        app_config = load_app_config()
        provider_instance = create_provider(provider, app_config.rate_limit)

        console.print("[cyan]Scanning for file type statistics...[/cyan]\n")

        scanner = BucketScanner(provider_instance)
        summaries = list(scanner.scan_file_types(bucket_pattern, before_date))

        if not summaries:
            console.print("[yellow]No files found matching criteria.[/yellow]")
            return

        # Render a table per bucket (summaries are already grouped by bucket)
        from collections import defaultdict

        grand_total_files = 0
        grand_total_size = 0
        bucket_count = 0
        totals_by_ext_count: dict[str, int] = defaultdict(int)
        totals_by_ext_size: dict[str, int] = defaultdict(int)

        for bucket_name, bucket_group in groupby(summaries, key=attrgetter("bucket")):
            bucket_count += 1

            table = Table(title=f"Bucket: {bucket_name}")
            table.add_column("Extension", style="cyan")
            table.add_column("File Count", justify="right", style="magenta")
            table.add_column("Total Size", justify="right", style="green")

            for s in bucket_group:
                table.add_row(
                    s.extension,
                    str(s.file_count),
                    DeletionSummary.format_size(s.total_size),
                )
                grand_total_files += s.file_count
                grand_total_size += s.total_size
                totals_by_ext_count[s.extension] += s.file_count
                totals_by_ext_size[s.extension] += s.total_size

            console.print(table)
            console.print()

        # Total summary grouped by file type across all buckets
        total_table = Table(title="Total (all buckets)")
        total_table.add_column("Extension", style="cyan")
        total_table.add_column("File Count", justify="right", style="magenta")
        total_table.add_column("Total Size", justify="right", style="green")

        for ext in sorted(totals_by_ext_count.keys()):
            total_table.add_row(
                ext,
                str(totals_by_ext_count[ext]),
                DeletionSummary.format_size(totals_by_ext_size[ext]),
            )

        console.print(total_table)
        console.print(
            f"\n[bold]Total: {grand_total_files} files, "
            f"{DeletionSummary.format_size(grand_total_size)} "
            f"across {bucket_count} bucket{'s' if bucket_count != 1 else ''}[/bold]"
        )

        logger.info(
            "stat_completed",
            total_files=grand_total_files,
            total_size=grand_total_size,
            buckets=bucket_count,
        )

    except CloudStorageError as e:
        console.print(f"[red]Cloud storage error: {str(e)}[/red]")
        logger.error("cloud_storage_error", error=str(e))
        raise typer.Exit(1)
    except ValueError as e:
        console.print(f"[red]Validation error: {str(e)}[/red]")
        logger.error("validation_error", error=str(e))
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Unexpected error: {str(e)}[/red]")
        logger.exception("unexpected_error")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
