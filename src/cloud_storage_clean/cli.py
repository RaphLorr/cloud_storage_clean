"""CLI interface using Typer and Rich."""

from datetime import datetime, timezone
from typing import Optional
from zoneinfo import ZoneInfo

import typer
from pydantic import ValidationError
from rich.console import Console

from cloud_storage_clean.config import (
    load_aliyun_config,
    load_app_config,
    load_tencent_config,
)
from cloud_storage_clean.deleter import SafeDeleter
from cloud_storage_clean.models import DeletionFilter
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


if __name__ == "__main__":
    app()
