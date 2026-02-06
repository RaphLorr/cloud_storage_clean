"""Structured logging configuration using structlog."""

import sys
from typing import Any

import structlog
from structlog.types import FilteringBoundLogger


def configure_logging(log_file: str | None = None, verbose: bool = False) -> None:
    """Configure structlog for the application.

    Args:
        log_file: Optional path to log file. If None, logs to stderr only.
        verbose: If True, enable debug level logging.
    """
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.TimeStamper(fmt="iso"),
    ]

    if log_file:
        # JSON format for file logging
        processors.append(structlog.processors.JSONRenderer())
    else:
        # Human-readable format for console
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.DEBUG if verbose else logging.INFO
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(
            file=open(log_file, "a") if log_file else sys.stderr
        ),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> FilteringBoundLogger:
    """Get a logger instance.

    Args:
        name: Logger name, typically __name__ of the calling module.

    Returns:
        Configured structlog logger.
    """
    return structlog.get_logger(name)


# Import logging module for level constants
import logging
