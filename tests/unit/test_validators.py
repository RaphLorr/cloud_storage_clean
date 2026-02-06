"""Unit tests for validation utilities."""

import re

import pytest

from cloud_storage_clean.utils.validators import (
    compile_regex,
    matches_glob,
    matches_regex,
    validate_glob_pattern,
)


def test_compile_regex_valid() -> None:
    """Test compiling valid regex patterns."""
    pattern = compile_regex(r"test-\d+")
    assert isinstance(pattern, re.Pattern)


def test_compile_regex_invalid() -> None:
    """Test compiling invalid regex patterns."""
    with pytest.raises(ValueError, match="Invalid regex pattern"):
        compile_regex(r"test-[")


def test_validate_glob_pattern_valid() -> None:
    """Test validating valid glob patterns."""
    validate_glob_pattern("*.log")
    validate_glob_pattern("test-*.txt")
    validate_glob_pattern("logs/**/*.log")


def test_validate_glob_pattern_empty() -> None:
    """Test validating empty glob pattern."""
    with pytest.raises(ValueError, match="cannot be empty"):
        validate_glob_pattern("")


def test_validate_glob_pattern_starts_with_slash() -> None:
    """Test validating glob pattern starting with slash."""
    with pytest.raises(ValueError, match="should not start with"):
        validate_glob_pattern("/*.log")


def test_matches_glob_basic() -> None:
    """Test basic glob matching."""
    assert matches_glob("test.log", "*.log")
    assert matches_glob("file.txt", "*.txt")
    assert not matches_glob("file.log", "*.txt")


def test_matches_glob_complex() -> None:
    """Test complex glob patterns."""
    assert matches_glob("test-123.log", "test-*.log")
    assert matches_glob("file.txt", "file.???")
    assert matches_glob("test-a.log", "test-[abc].log")
    assert not matches_glob("test-d.log", "test-[abc].log")


def test_matches_regex_basic() -> None:
    """Test basic regex matching."""
    pattern = compile_regex(r"test-\d+")
    assert matches_regex("test-123", pattern)
    assert matches_regex("prefix-test-456-suffix", pattern)
    assert not matches_regex("test-abc", pattern)


def test_matches_regex_anchored() -> None:
    """Test anchored regex patterns."""
    pattern = compile_regex(r"^test-\d+$")
    assert matches_regex("test-123", pattern)
    assert not matches_regex("prefix-test-123", pattern)
    assert not matches_regex("test-123-suffix", pattern)
