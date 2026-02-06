# Cloud Storage Cleanup Tool - Quick Start

## Installation

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install the package
pip install -e .
```

## Configuration

Create a `.env` file in the project root:

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

## Basic Usage

### 1. List Buckets

Explore available buckets before deleting:

```bash
# List all Tencent COS buckets
cloud-storage-clean list-buckets tencent

# Filter buckets with regex pattern
cloud-storage-clean list-buckets tencent --pattern "test-.*"

# List Aliyun OSS buckets
cloud-storage-clean list-buckets aliyun
```

### 2. Delete Files (Safe Workflow)

**RECOMMENDED**: Always use `--dry-run` first to preview what will be deleted:

```bash
# Step 1: Preview with dry-run (no actual deletion)
cloud-storage-clean clean tencent "test-.*" "*.log" 2024-01-01 --dry-run

# Step 2: Review the output, then run for real
cloud-storage-clean clean tencent "test-.*" "*.log" 2024-01-01
```

**Additional Options:**

```bash
# With logging
cloud-storage-clean clean tencent "test-.*" "*.log" 2024-01-01 --log-file cleanup.log

# Dry-run with logging (test entire workflow)
cloud-storage-clean clean tencent "test-.*" "*.log" 2024-01-01 --dry-run --log-file test.log

# Skip confirmation (dangerous!)
cloud-storage-clean clean tencent "test-.*" "*.log" 2024-01-01 --no-confirm

# Verbose mode
cloud-storage-clean clean tencent "test-.*" "*.log" 2024-01-01 --verbose
```

## Command Reference

### `clean` command

```bash
cloud-storage-clean clean PROVIDER BUCKET_PATTERN FILE_PATTERN BEFORE [OPTIONS]
```

**Arguments:**
- `PROVIDER`: Cloud provider (`tencent` or `aliyun`)
- `BUCKET_PATTERN`: Regex pattern for bucket names (e.g., `"test-.*"`)
- `FILE_PATTERN`: Glob pattern for file names (e.g., `"*.log"`, `"temp/*"`)
- `BEFORE`: Delete files modified before this date (format: `YYYY-MM-DD`)

**Options:**
- `--dry-run`: **Simulate deletion without actually deleting files (RECOMMENDED FIRST)**
- `--timezone TZ`, `--tz TZ`: Timezone for date (e.g., `Asia/Shanghai`, default: local timezone)
- `--no-confirm`: Skip confirmation prompt (use with caution)
- `--log-file PATH`: Path to structured JSON log file
- `--verbose`: Enable debug-level logging

### `list-buckets` command

```bash
cloud-storage-clean list-buckets PROVIDER [OPTIONS]
```

**Arguments:**
- `PROVIDER`: Cloud provider (`tencent` or `aliyun`)

**Options:**
- `--pattern TEXT`: Regex pattern to filter bucket names
- `--verbose`: Enable debug-level logging

## Examples

### Clean up old test logs

```bash
cloud-storage-clean clean tencent "test-env-.*" "*.log" 2024-01-01 --log-file test-cleanup.log
```

### Remove temporary files from staging

```bash
cloud-storage-clean clean aliyun "staging-.*" "temp/*" 2024-06-01
```

### Delete old backups with pattern

```bash
cloud-storage-clean clean tencent "backup-.*" "backup-*.tar.gz" 2023-01-01
```

### Explore buckets first

```bash
# List all test buckets
cloud-storage-clean list-buckets tencent --pattern "test-.*"

# Then delete files from them
cloud-storage-clean clean tencent "test-.*" "*.tmp" 2024-01-01
```

## Safety Features

1. **Interactive Confirmation**: Shows detailed summary before deletion
   - Total file count and size
   - Breakdown by bucket
   - Provider information

2. **Audit Trail**: All operations logged with timestamps
   - Structured JSON format for log files
   - Human-readable console output

3. **Pattern Validation**: Validates regex and glob patterns before execution

4. **Rate Limiting**: Prevents API throttling (default: 100 calls/sec)

5. **Error Isolation**: Failed deletions logged but don't stop the process

## Testing

```bash
# Run all tests with coverage
pytest tests/unit/ -v --cov=src/cloud_storage_clean --cov-report=html

# View coverage report
open htmlcov/index.html
```

## Troubleshooting

### Missing credentials

```
ValidationError: TENCENT_SECRET_ID is required
```

**Solution**: Create `.env` file with credentials (see Configuration section)

### Invalid pattern

```
ValueError: Invalid regex pattern 'test-[': unterminated character set
```

**Solution**: Check regex syntax. Use online regex testers to validate patterns.

### Rate limit exceeded

```
RateLimitError: Rate limit exceeded
```

**Solution**: Reduce `RATE_LIMIT` in `.env` file:
```bash
RATE_LIMIT=50  # Default is 100
```

## Development

```bash
# Install development dependencies
pip install -e ".[dev]"

# Format code
black src/ tests/

# Lint
ruff check src/ tests/

# Type check
mypy src/
```
