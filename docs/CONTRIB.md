# Contributing Guide

## Development Setup

### Prerequisites

- Python 3.11 or higher
- Poetry (recommended) or pip
- Git

### Initial Setup

```bash
# Clone the repository
git clone <repository-url>
cd cloud_storage_clean

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install package in development mode
make install

# Or manually:
pip install -e .
pip install pytest pytest-cov pytest-mock black ruff mypy
```

### Environment Configuration

1. **Copy environment template:**
   ```bash
   cp .env.example .env
   ```

2. **Configure credentials** (see Environment Variables section below)

3. **Create logs directory:**
   ```bash
   mkdir -p logs
   ```

## Available Development Scripts

All development tasks are managed through the `Makefile`. Run `make help` to see all available commands.

### Make Commands Reference

| Command | Description | Requirements |
|---------|-------------|--------------|
| `make help` | Show help message with all commands | None |
| `make install` | Install package in development mode | None |
| `make test` | Run unit tests with HTML coverage report | None |
| `make test-unit` | Run unit tests with terminal coverage | None |
| `make test-integration` | Run all integration tests | Credentials in `.env` |
| `make test-integration-tencent` | Run Tencent provider integration tests | Tencent credentials |
| `make test-integration-aliyun` | Run Aliyun provider integration tests | Aliyun credentials |
| `make test-integration-scanner-tencent` | Run scanner tests with Tencent | Tencent credentials |
| `make test-integration-scanner-aliyun` | Run scanner tests with Aliyun | Aliyun credentials |
| `make test-coverage` | Generate HTML coverage report | None |
| `make test-all` | Run both unit and integration tests | Credentials in `.env` |
| `make lint` | Run linters (ruff) | None |
| `make format` | Format code with black | None |
| `make type-check` | Run mypy type checking | None |
| `make clean` | Clean up generated files | None |

### Example Commands

```bash
# Show all available commands
make help

# Run example integration test commands
make example-tencent-bucket
make example-aliyun-bucket
make example-delete-test
```

## Environment Variables

All environment variables are defined in `.env.example` as the single source of truth.

### Tencent COS Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `TENCENT_SECRET_ID` | Yes* | - | Tencent Cloud API Secret ID (obtain from [API Key Management](https://console.cloud.tencent.com/cam/capi)) |
| `TENCENT_SECRET_KEY` | Yes* | - | Tencent Cloud API Secret Key |
| `TENCENT_REGION` | No | `ap-guangzhou` | Tencent COS region (e.g., `ap-guangzhou`, `ap-shanghai`, `ap-beijing`) |
| `TENCENT_SCHEME` | No | `https` | Protocol scheme (`https` or `http`) |

*Required only if using Tencent COS provider

### Aliyun OSS Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ALIYUN_ACCESS_KEY_ID` | Yes* | - | Aliyun AccessKey ID (obtain from [RAM Console](https://ram.console.aliyun.com/)) |
| `ALIYUN_ACCESS_KEY_SECRET` | Yes* | - | Aliyun AccessKey Secret |
| `ALIYUN_ENDPOINT` | No | `oss-cn-hangzhou.aliyuncs.com` | Aliyun OSS endpoint (e.g., `oss-cn-hangzhou.aliyuncs.com`, `oss-cn-shanghai.aliyuncs.com`) |

*Required only if using Aliyun OSS provider

### Application Configuration

| Variable | Required | Default | Description | Format |
|----------|----------|---------|-------------|--------|
| `LOG_FILE` | No | (empty) | Path to log file for structured JSON logging | Relative or absolute path (e.g., `logs/cleanup.log`) |
| `VERBOSE` | No | `false` | Enable verbose debug-level logging | `true` or `false` |
| `RATE_LIMIT` | No | `100` | Maximum API calls per second (token bucket algorithm) | Integer (1-1000) |
| `BATCH_SIZE` | No | `100` | Maximum files per batch deletion operation | Integer (1-1000) |

### Environment Setup Examples

**Tencent COS Only:**
```bash
TENCENT_SECRET_ID=AKIDxxxxxxxxxxxxxxxxxxxxxx
TENCENT_SECRET_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TENCENT_REGION=ap-guangzhou
LOG_FILE=logs/cleanup.log
VERBOSE=true
```

**Aliyun OSS Only:**
```bash
ALIYUN_ACCESS_KEY_ID=LTAI5xxxxxxxxxxxxx
ALIYUN_ACCESS_KEY_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
ALIYUN_ENDPOINT=oss-cn-hangzhou.aliyuncs.com
LOG_FILE=logs/cleanup.log
```

**Both Providers:**
```bash
# Tencent COS
TENCENT_SECRET_ID=AKIDxxxxxxxxxxxxxxxxxxxxxx
TENCENT_SECRET_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TENCENT_REGION=ap-guangzhou

# Aliyun OSS
ALIYUN_ACCESS_KEY_ID=LTAI5xxxxxxxxxxxxx
ALIYUN_ACCESS_KEY_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
ALIYUN_ENDPOINT=oss-cn-hangzhou.aliyuncs.com

# Application
LOG_FILE=logs/cleanup.log
VERBOSE=false
RATE_LIMIT=100
BATCH_SIZE=100
```

## Testing Procedures

### Unit Tests

Unit tests require **no cloud credentials** and can be run immediately:

```bash
# Run all unit tests with coverage
make test

# Or manually
pytest tests/unit/ -v --cov=src/cloud_storage_clean --cov-report=term-missing

# Generate HTML coverage report
make test-coverage
open htmlcov/index.html  # View coverage report
```

**Coverage Requirements:**
- Minimum 80% code coverage
- All new features must include unit tests
- Tests should be isolated (no external dependencies)

### Integration Tests

Integration tests require **valid cloud credentials** in `.env` file:

```bash
# Run all integration tests
make test-integration

# Run provider-specific tests
make test-integration-tencent
make test-integration-aliyun

# Run scanner integration tests
make test-integration-scanner-tencent
make test-integration-scanner-aliyun
```

**Integration Test Requirements:**
- Real cloud credentials in `.env`
- Test buckets should be created before running tests
- Use `--test-bucket` flag to specify bucket name
- Destructive tests require `--enable-delete` flag

**Example Integration Test Commands:**

```bash
# Test with specific bucket
pytest tests/integration/test_tencent_provider.py -v -s --test-bucket=my-test-bucket

# Run destructive delete tests (WARNING: deletes files!)
pytest tests/integration/test_tencent_provider.py::test_batch_delete_success \
  -v -s --test-bucket=my-test-bucket --enable-delete
```

### Test Organization

```
tests/
├── unit/                      # Unit tests (no credentials needed)
│   ├── test_deleter.py       # SafeDeleter tests
│   ├── test_models.py        # Data model tests
│   ├── test_rate_limiter.py  # Rate limiting tests
│   ├── test_scanner.py       # Scanner tests
│   └── test_validators.py    # Validation tests
├── integration/               # Integration tests (credentials required)
│   ├── test_aliyun_provider.py
│   ├── test_tencent_provider.py
│   └── test_scanner_integration.py
└── conftest.py               # Shared test fixtures
```

## Development Workflow

### 1. Create Feature Branch

```bash
git checkout -b feature/your-feature-name
```

### 2. Write Tests First (TDD)

```bash
# Create test file
touch tests/unit/test_your_feature.py

# Write failing test
pytest tests/unit/test_your_feature.py  # Should fail
```

### 3. Implement Feature

```bash
# Implement feature in src/cloud_storage_clean/
# Run tests until they pass
pytest tests/unit/test_your_feature.py  # Should pass
```

### 4. Code Quality Checks

```bash
# Format code
make format

# Run linter
make lint

# Type check
make type-check

# Run all unit tests
make test
```

### 5. Integration Testing

```bash
# Test with real credentials (if applicable)
make test-integration-tencent
```

### 6. Commit Changes

```bash
git add .
git commit -m "feat: add your feature description"
```

### 7. Push and Create PR

```bash
git push origin feature/your-feature-name
# Create pull request on GitHub
```

## Code Style Guidelines

### Python Style

- **Line Length**: 100 characters (enforced by black and ruff)
- **Python Version**: 3.11+ (target version)
- **Type Hints**: Required for all functions and methods
- **Docstrings**: Required for all public APIs

### Code Formatting

We use **Black** for code formatting:

```bash
# Format all code
make format

# Check formatting without changes
black --check src/ tests/
```

### Linting

We use **Ruff** for linting:

```bash
# Run linter
make lint

# Auto-fix issues
ruff check --fix src/ tests/
```

### Type Checking

We use **mypy** for static type checking:

```bash
# Run type checker
make type-check

# Configuration in pyproject.toml:
# - python_version = "3.11"
# - warn_return_any = true
# - warn_unused_configs = true
# - disallow_untyped_defs = true
```

## Project Structure

```
cloud_storage_clean/
├── src/
│   └── cloud_storage_clean/
│       ├── __init__.py
│       ├── cli.py              # CLI entry point (Typer)
│       ├── config.py           # Configuration management (Pydantic)
│       ├── deleter.py          # Safe deletion orchestration
│       ├── models.py           # Data models (frozen dataclasses)
│       ├── scanner.py          # Bucket/file scanning
│       ├── providers/
│       │   ├── base.py        # Abstract provider interface
│       │   ├── tencent.py     # Tencent COS implementation
│       │   └── aliyun.py      # Aliyun OSS implementation
│       └── utils/
│           ├── logging.py     # Structured logging (structlog)
│           ├── rate_limiter.py # Token bucket rate limiting
│           └── validators.py   # Pattern validation
├── tests/
│   ├── unit/
│   ├── integration/
│   └── conftest.py            # Shared pytest fixtures
├── docs/
│   ├── CONTRIB.md             # This file
│   └── RUNBOOK.md             # Operations runbook
├── .env.example               # Environment variable template
├── pyproject.toml             # Poetry configuration
├── Makefile                   # Development tasks
└── README.md                  # User documentation
```

## Design Principles

### 1. Immutability

All data models use frozen dataclasses:

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class FileInfo:
    bucket: str
    key: str
    size: int
```

### 2. Lazy Evaluation

Use iterators to prevent memory exhaustion:

```python
def scan(self) -> Iterator[FileInfo]:
    for bucket in self.list_buckets():
        for file in self.list_files(bucket):
            yield file
```

### 3. Type Safety

Full type hints with mypy checking:

```python
def delete(self, files: list[FileInfo]) -> Iterator[DeletionResult]:
    ...
```

### 4. Error Handling

Comprehensive exception hierarchy:

```python
class CloudStorageError(Exception):
    """Base exception for cloud storage operations."""

class AuthenticationError(CloudStorageError):
    """Authentication failed."""
```

## Debugging

### Enable Verbose Logging

```bash
# Set in .env
VERBOSE=true

# Or use CLI flag
cloud-storage-clean clean tencent ".*" "*.log" 2024-01-01 --verbose
```

### View Structured Logs

```bash
# View JSON logs
cat logs/cleanup.log | jq

# Filter errors only
cat logs/cleanup.log | jq 'select(.level == "error")'

# Filter specific events
cat logs/cleanup.log | jq 'select(.event == "file_deleted")'
```

### Run Tests with Print Statements

```bash
# Show print output in tests
pytest tests/unit/ -v -s

# Run specific test with debugging
pytest tests/unit/test_deleter.py::test_delete_dry_run_mode -v -s
```

## Common Issues

### Import Errors

**Problem**: `ModuleNotFoundError: No module named 'cloud_storage_clean'`

**Solution**:
```bash
# Reinstall in development mode
pip install -e .
```

### Credential Errors

**Problem**: `ValidationError: TENCENT_SECRET_ID is required`

**Solution**:
```bash
# Check .env file exists
ls -la .env

# Verify credentials are set
grep "TENCENT_SECRET_ID" .env
```

### Test Failures

**Problem**: Tests fail with "No module named 'pytest'"

**Solution**:
```bash
# Install dev dependencies
make install
```

## Contributing Checklist

Before submitting a pull request:

- [ ] Code follows style guidelines (black, ruff)
- [ ] All tests pass (`make test`)
- [ ] Type checking passes (`make type-check`)
- [ ] New features include unit tests
- [ ] Coverage remains above 80%
- [ ] Documentation updated (if needed)
- [ ] Commit messages follow conventional commits format
- [ ] `.env` not committed (in `.gitignore`)

## Getting Help

- **Documentation**: Check `README.md` and `QUICKSTART.md`
- **Issues**: Search existing GitHub issues
- **Logs**: Review structured logs for detailed errors
- **Tests**: Run tests with `-v -s` flags for debugging

## Resources

- **Tencent COS SDK**: https://github.com/tencentyun/cos-python-sdk-v5
- **Aliyun OSS SDK**: https://github.com/aliyun/aliyun-oss-python-sdk
- **Typer Documentation**: https://typer.tiangolo.com/
- **Pydantic Documentation**: https://docs.pydantic.dev/
- **pytest Documentation**: https://docs.pytest.org/
