# Cloud Storage Cleanup Tool

A Python CLI tool to safely delete files from Tencent COS and Aliyun OSS based on bucket patterns (regex), file patterns (glob), and time criteria.

## Features

- **Multi-Provider Support**: Works with Tencent COS and Aliyun OSS
- **Pattern Matching**: Regex for buckets, glob patterns for files
- **Time-Based Filtering**: Delete files modified before a specific date
- **Safe Operations**: Interactive confirmation with detailed summary
- **Batch Deletion**: Efficient batch operations (up to 1000 files per batch)
- **Rate Limiting**: Respects API limits to avoid throttling
- **Comprehensive Logging**: Structured JSON logging for audit trails
- **Memory Efficient**: Lazy evaluation with iterators

## Installation

### Prerequisites

- Python 3.11 or higher
- Poetry (recommended) or pip

### Using Poetry

```bash
# Clone the repository
git clone <repository-url>
cd cloud_storage_clean

# Install dependencies
poetry install

# Activate virtual environment
poetry shell
```

### Using pip

```bash
pip install -e .
```

## Configuration

### Environment Variables

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```bash
# Tencent COS
TENCENT_SECRET_ID=your_secret_id
TENCENT_SECRET_KEY=your_secret_key
TENCENT_REGION=ap-guangzhou

# Aliyun OSS
ALIYUN_ACCESS_KEY_ID=your_access_key_id
ALIYUN_ACCESS_KEY_SECRET=your_access_key_secret
ALIYUN_ENDPOINT=oss-cn-hangzhou.aliyuncs.com
```

### Security Notes

- **Never commit `.env` files** to version control
- Use environment variables for production deployments
- Credentials are masked in logs using Pydantic SecretStr

## Usage

### List Buckets

Explore available buckets before deleting:

```bash
# List all buckets
cloud-storage-clean list-buckets tencent

# Filter buckets with regex
cloud-storage-clean list-buckets tencent --pattern "test-.*"

# List Aliyun buckets
cloud-storage-clean list-buckets aliyun
```

### Delete Files

Delete files matching specific criteria:

```bash
# Basic deletion with confirmation
cloud-storage-clean clean tencent "test-.*" "*.log" 2024-01-01

# Preview with dry-run (recommended first step)
cloud-storage-clean clean tencent "test-.*" "*.log" 2024-01-01 --dry-run

# With logging
cloud-storage-clean clean tencent "test-.*" "*.log" 2024-01-01 --log-file cleanup.log

# Skip confirmation (dangerous!)
cloud-storage-clean clean tencent "test-.*" "*.log" 2024-01-01 --no-confirm
```

### Command Options

#### `clean` command

```bash
cloud-storage-clean clean PROVIDER BUCKET_PATTERN FILE_PATTERN BEFORE [OPTIONS]
```

**Arguments:**
- `PROVIDER` - Cloud provider: `tencent` or `aliyun`
- `BUCKET_PATTERN` - Regex pattern for bucket names (e.g., `"test-.*"`)
- `FILE_PATTERN` - Glob pattern for file names (e.g., `"*.log"`, `"temp/*"`)
- `BEFORE` - Delete files modified before this date (format: `YYYY-MM-DD`)

**Options:**

| Option | Description |
|--------|-------------|
| `--dry-run` | Simulate deletion without actually deleting files (preview mode) |
| `--timezone TZ`, `--tz TZ` | Timezone for date interpretation (e.g., `Asia/Shanghai`, `UTC`). Default: local timezone |
| `--no-confirm` | Skip confirmation prompt (dangerous) |
| `--log-file PATH` | Path to log file for structured JSON logging |
| `--verbose` | Enable debug-level logging |

#### `list-buckets` command

```bash
cloud-storage-clean list-buckets PROVIDER [OPTIONS]
```

**Arguments:**
- `PROVIDER` - Cloud provider: `tencent` or `aliyun`

**Options:**

| Option | Description |
|--------|-------------|
| `--pattern REGEX` | Regex pattern to filter bucket names |
| `--verbose` | Enable debug-level logging |

## Timezone Handling

When you specify a date like `2025-01-01`, the tool needs to know which timezone you mean:

**Default behavior (no `--timezone` flag):**
- Uses your computer's local timezone
- For Chinese users with CST timezone: `2025-01-01` = Beijing time 2025-01-01 00:00:00
- For US users with EST timezone: `2025-01-01` = New York time 2025-01-01 00:00:00

**Recommended for Chinese users:**
```bash
# Explicitly specify Beijing time (most reliable)
cloud-storage-clean clean tencent "bucket" "*.log" 2025-01-01 --timezone Asia/Shanghai
```

**Common timezones:**
- `Asia/Shanghai` - Beijing/Shanghai (UTC+8)
- `Asia/Hong_Kong` - Hong Kong (UTC+8)
- `UTC` - Coordinated Universal Time
- `America/New_York` - New York (UTC-5/-4)
- `Europe/London` - London (UTC+0/+1)

**Important:** If you don't specify `--timezone` and your colleague runs the same command on a computer in a different timezone, they will get different results!

## Examples

### Example 1: Safe workflow with dry-run

```bash
# Step 1: Preview what would be deleted
cloud-storage-clean clean tencent "test-env-.*" "*.log" 2024-01-01 --dry-run

# Step 2: Review the output, then run for real
cloud-storage-clean clean tencent "test-env-.*" "*.log" 2024-01-01 --log-file cleanup.log
```

### Example 2: Clean up test environment logs

```bash
cloud-storage-clean clean tencent "test-env-.*" "*.log" 2024-01-01 --log-file cleanup.log
```

### Example 3: Remove temporary files from staging

```bash
cloud-storage-clean clean aliyun "staging-.*" "temp/*" 2024-06-01 --dry-run
```

### Example 4: Delete old backups

```bash
cloud-storage-clean clean tencent "backup-.*" "backup-*.tar.gz" 2023-01-01
```

### Example 5: Using timezone (for Chinese users)

```bash
# Explicitly specify Beijing time
cloud-storage-clean clean tencent "test-.*" "*.log" 2025-01-01 --timezone Asia/Shanghai --dry-run

# Or use short form
cloud-storage-clean clean tencent "test-.*" "*.log" 2025-01-01 --tz Asia/Shanghai --dry-run

# Without --timezone: uses your computer's local timezone (CST for Chinese users)
cloud-storage-clean clean tencent "test-.*" "*.log" 2025-01-01 --dry-run
```

### Example 6: Automated cleanup (with logging)

```bash
# Daily cleanup script with logging
cloud-storage-clean clean tencent "logs-.*" "*.log" $(date -d '30 days ago' +%Y-%m-%d) \
  --timezone Asia/Shanghai \
  --log-file logs/cleanup-$(date +%Y%m%d).log \
  --no-confirm
```

## Safety Features

1. **Interactive Confirmation**: Displays detailed summary before deletion
   - Total file count and size
   - Breakdown by bucket
   - Provider information

2. **Audit Trail**: All operations logged with timestamps
   - Structured JSON format for machine parsing
   - Human-readable console output

3. **Pattern Validation**: Validates regex and glob patterns before execution

4. **Rate Limiting**: Token bucket algorithm prevents API throttling

5. **Error Isolation**: Failed deletions don't stop the entire process

## Architecture

### Core Components

- **Providers**: Abstract interface with Tencent and Aliyun implementations
- **Scanner**: Lazy evaluation of buckets and files with pattern matching
- **Deleter**: Safe deletion orchestration with batch operations
- **CLI**: Typer-based interface with Rich formatting

### Design Principles

- **Immutability**: All data models use frozen dataclasses
- **Lazy Evaluation**: Iterators prevent memory exhaustion
- **Error Handling**: Comprehensive exception hierarchy
- **Type Safety**: Full type hints with mypy checking

## Development

### Running Tests

```bash
# Run all tests with coverage
pytest --cov=src/cloud_storage_clean --cov-report=html

# Run specific test types
pytest tests/unit/
pytest tests/integration/
pytest tests/e2e/
```

### Code Quality

```bash
# Format code
black src/ tests/

# Lint
ruff check src/ tests/

# Type check
mypy src/
```

## Troubleshooting

### Authentication Errors

**Problem**: `AuthenticationError: Authentication failed`

**Solution**:
- Verify credentials in `.env` file
- Check that credentials have necessary permissions
- Ensure region/endpoint is correct

### Rate Limit Errors

**Problem**: `RateLimitError: Rate limit exceeded`

**Solution**:
- Reduce `RATE_LIMIT` in `.env` (default: 100)
- Add delays between operations
- Contact provider to increase limits

### Bucket Not Found

**Problem**: `BucketNotFoundError: Bucket not found`

**Solution**:
- Verify bucket name is correct
- Check that bucket exists in the specified region
- Ensure credentials have access to the bucket

## Security Considerations

- **Credentials**: Never hardcode credentials in code
- **Logging**: Credentials are automatically masked in logs
- **Permissions**: Use least-privilege IAM policies
- **Audit**: Review log files regularly
- **Deletion**: Operations are irreversible - always review summaries

## License

MIT License

## Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## Support

For issues and questions:
- Open an issue on GitHub
- Check existing issues for solutions
- Review logs for detailed error messages
