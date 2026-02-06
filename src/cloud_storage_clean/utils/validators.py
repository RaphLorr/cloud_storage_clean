"""Input validation utilities."""

import re
from fnmatch import fnmatch
from typing import Pattern


def compile_regex(pattern: str) -> Pattern[str]:
    """Compile and validate a regex pattern.

    Args:
        pattern: Regex pattern string.

    Returns:
        Compiled regex pattern.

    Raises:
        ValueError: If pattern is invalid.
    """
    try:
        return re.compile(pattern)
    except re.error as e:
        raise ValueError(f"Invalid regex pattern '{pattern}': {str(e)}")


def validate_glob_pattern(pattern: str) -> None:
    """Validate a glob pattern.

    Args:
        pattern: Glob pattern string.

    Raises:
        ValueError: If pattern is invalid or empty.
    """
    if not pattern:
        raise ValueError("Glob pattern cannot be empty")

    if pattern.startswith("/"):
        raise ValueError("Glob pattern should not start with '/'")


def matches_glob(text: str, pattern: str) -> bool:
    """Check if text matches glob pattern.

    Args:
        text: Text to match.
        pattern: Glob pattern (supports *, ?, [abc]).

    Returns:
        True if text matches pattern.
    """
    return fnmatch(text, pattern)


def matches_regex(text: str, pattern: Pattern[str]) -> bool:
    """Check if text matches regex pattern.

    Args:
        text: Text to match.
        pattern: Compiled regex pattern.

    Returns:
        True if text matches pattern.
    """
    return pattern.search(text) is not None
