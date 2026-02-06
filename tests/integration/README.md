# Integration Tests

Integration tests verify the tool works with **real cloud services** using actual API calls. These tests require valid credentials and may incur small costs from API usage.

## Prerequisites

### 1. Set Up Credentials

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

### 2. Create Test Buckets

**IMPORTANT**: Use dedicated test buckets, not production buckets!

For testing deletion operations, create test files in your bucket:
- `test-delete-1.txt`
- `test-delete-2.txt`

## Running Tests

### Basic Tests (No Bucket Required)

These tests only verify authentication and basic API access:

```bash
# Test Tencent provider
pytest tests/integration/test_tencent_provider.py -v -s

# Test Aliyun provider
pytest tests/integration/test_aliyun_provider.py -v -s
```

**Expected output:**
```
✓ Found 5 bucket(s)
  First bucket: my-test-bucket
```

### Tests with Test Bucket

These tests require a test bucket name:

```bash
# Tencent with test bucket
pytest tests/integration/test_tencent_provider.py -v -s \
  --test-bucket=your-test-bucket-name

# Aliyun with test bucket
pytest tests/integration/test_aliyun_provider.py -v -s \
  --test-bucket=your-test-bucket-name
```

### Scanner Integration Tests

Test the full scanning workflow:

```bash
# Test Tencent scanner
pytest tests/integration/test_scanner_integration.py -v -s \
  --provider=tencent

# Test with specific bucket
pytest tests/integration/test_scanner_integration.py -v -s \
  --provider=tencent \
  --test-bucket=your-test-bucket

# Test Aliyun scanner
pytest tests/integration/test_scanner_integration.py -v -s \
  --provider=aliyun
```

### Destructive Tests (Deletion)

**⚠️ WARNING**: These tests DELETE files from your bucket!

Only run these on test buckets with test data:

```bash
# Enable deletion tests
pytest tests/integration/test_tencent_provider.py::test_batch_delete_success -v -s \
  --test-bucket=your-test-bucket \
  --enable-delete

# For Aliyun
pytest tests/integration/test_aliyun_provider.py::test_batch_delete_success -v -s \
  --test-bucket=your-test-bucket \
  --enable-delete
```

**Before running:**
1. Create test files in your bucket (`test-delete-1.txt`, `test-delete-2.txt`)
2. Verify you're using a test bucket, not production
3. Backup any important data

## Test Categories

### 1. Provider Tests (`test_*_provider.py`)

Test individual cloud provider implementations:

| Test | Description | Requires |
|------|-------------|----------|
| `test_list_buckets_success` | List all buckets | Credentials |
| `test_list_buckets_with_invalid_credentials` | Test auth errors | Nothing |
| `test_list_files_success` | List files in bucket | Test bucket |
| `test_list_files_with_prefix` | Test prefix filtering | Test bucket |
| `test_batch_delete_success` | Delete files | Test bucket + `--enable-delete` |
| `test_rate_limiter_integration` | Verify rate limiting | Credentials |

### 2. Scanner Tests (`test_scanner_integration.py`)

Test the scanning and filtering logic:

| Test | Description | Requires |
|------|-------------|----------|
| `test_scanner_with_real_provider` | Basic scanning | Provider |
| `test_scanner_with_bucket_pattern` | Regex filtering | Test bucket |
| `test_scanner_with_file_pattern` | Glob filtering | Test bucket |
| `test_scanner_with_date_filter` | Time filtering | Test bucket |
| `test_scanner_lazy_evaluation` | Memory efficiency | Provider |

## Troubleshooting

### SkipTest: Credentials not configured

**Problem:**
```
SKIPPED [1] Tencent credentials not configured: TENCENT_SECRET_ID is required
```

**Solution:**
1. Create `.env` file in project root
2. Add required credentials (see Prerequisites)
3. Verify `.env` is not in `.gitignore`

### BucketNotFoundError

**Problem:**
```
BucketNotFoundError: Bucket not found: your-test-bucket
```

**Solution:**
1. Verify bucket name is correct
2. Check bucket exists in the specified region
3. Ensure credentials have access to the bucket

### AuthenticationError

**Problem:**
```
AuthenticationError: Authentication failed: InvalidAccessKeyId
```

**Solution:**
1. Verify credentials in `.env` are correct
2. Check credentials have necessary IAM permissions
3. For Tencent: Verify region is correct
4. For Aliyun: Verify endpoint matches bucket region

### Rate Limit Errors

**Problem:**
```
RateLimitError: Rate limit exceeded
```

**Solution:**
1. Tests use rate limit of 10 calls/sec (safe for testing)
2. Wait a few minutes and try again
3. If persistent, check your API quota with provider

## Test Coverage

Integration tests verify:

- ✅ Authentication with real credentials
- ✅ Listing buckets across providers
- ✅ Listing files with pagination
- ✅ Pattern matching (regex/glob)
- ✅ Date filtering
- ✅ Batch deletion
- ✅ Rate limiting
- ✅ Error handling
- ✅ Lazy evaluation (memory efficiency)

## Best Practices

### 1. Use Test Buckets

Never run integration tests on production buckets:

```bash
# GOOD: Dedicated test bucket
--test-bucket=my-integration-test-bucket

# BAD: Production bucket
--test-bucket=production-customer-data
```

### 2. Clean Up After Tests

After running destructive tests:
1. Verify test files were deleted
2. Check no unexpected files remain
3. Review deletion logs

### 3. Monitor Costs

Integration tests make real API calls:
- Bucket listing: ~$0.005 per 1000 requests
- File listing: ~$0.005 per 1000 requests
- Deletion: Usually free

Typical test run costs < $0.01

### 4. Run Regularly

Run integration tests:
- Before major releases
- After provider SDK updates
- When adding new provider features
- Weekly in CI/CD (if available)

## Continuous Integration

To run integration tests in CI/CD:

```yaml
# .github/workflows/integration-tests.yml
name: Integration Tests

on:
  schedule:
    - cron: '0 2 * * 1'  # Weekly on Monday

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -e .
          pip install pytest pytest-cov

      - name: Run integration tests
        env:
          TENCENT_SECRET_ID: ${{ secrets.TENCENT_SECRET_ID }}
          TENCENT_SECRET_KEY: ${{ secrets.TENCENT_SECRET_KEY }}
          ALIYUN_ACCESS_KEY_ID: ${{ secrets.ALIYUN_ACCESS_KEY_ID }}
          ALIYUN_ACCESS_KEY_SECRET: ${{ secrets.ALIYUN_ACCESS_KEY_SECRET }}
        run: |
          pytest tests/integration/ -v --tb=short
```

## Security Notes

⚠️ **Never commit credentials to git!**

- `.env` is in `.gitignore`
- Use environment variables in CI/CD
- Rotate credentials if exposed
- Use least-privilege IAM policies

## IAM Permissions Required

### Tencent COS

Minimum permissions:
```json
{
  "version": "2.0",
  "statement": [
    {
      "effect": "allow",
      "action": [
        "cos:GetService",
        "cos:GetBucket",
        "cos:DeleteObject"
      ],
      "resource": "*"
    }
  ]
}
```

### Aliyun OSS

Minimum permissions:
- `oss:ListBuckets`
- `oss:ListObjects`
- `oss:DeleteObject`

## Getting Help

If integration tests fail:

1. **Check logs**: Use `-v -s` for verbose output
2. **Verify credentials**: Test auth separately
3. **Check bucket access**: Use cloud console to verify
4. **Review IAM permissions**: Ensure sufficient access
5. **Contact support**: Open GitHub issue with sanitized logs
