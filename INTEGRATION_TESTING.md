# Integration Testing Guide

This guide walks you through running integration tests with real cloud credentials.

## Quick Start

### 1. Install Dependencies

```bash
# Activate virtual environment
source venv/bin/activate

# Install test dependencies
pip install pytest pytest-cov pytest-mock
```

### 2. Configure Credentials

Create `.env` file in project root:

```bash
# Tencent COS
TENCENT_SECRET_ID=AKIDxxxxxxxxxxxxx
TENCENT_SECRET_KEY=xxxxxxxxxxxxx
TENCENT_REGION=ap-guangzhou

# Aliyun OSS
ALIYUN_ACCESS_KEY_ID=LTAIxxxxxxxxxxxxx
ALIYUN_ACCESS_KEY_SECRET=xxxxxxxxxxxxx
ALIYUN_ENDPOINT=oss-cn-hangzhou.aliyuncs.com
```

### 3. Run Basic Tests

```bash
# Test Tencent authentication
make test-integration-tencent

# Test Aliyun authentication
make test-integration-aliyun
```

## Testing Levels

### Level 1: Authentication Only

Tests basic connectivity and authentication:

```bash
# Tencent
pytest tests/integration/test_tencent_provider.py::test_list_buckets_success -v -s

# Aliyun
pytest tests/integration/test_aliyun_provider.py::test_list_buckets_success -v -s
```

**Expected output:**
```
✓ Found 3 bucket(s)
  First bucket: my-production-bucket
PASSED
```

### Level 2: With Test Bucket

Tests file operations on a specific bucket:

```bash
# Replace YOUR-TEST-BUCKET with your actual test bucket name
export TEST_BUCKET=your-test-bucket-name

# Tencent
pytest tests/integration/test_tencent_provider.py -v -s \
  --test-bucket=$TEST_BUCKET

# Aliyun
pytest tests/integration/test_aliyun_provider.py -v -s \
  --test-bucket=$TEST_BUCKET
```

**Expected output:**
```
test_list_files_success
  ✓ Testing file listing in bucket: your-test-bucket
  Found 45 file(s)
  First file: logs/app.log (2048 bytes)
PASSED
```

### Level 3: Scanner Integration

Tests the full scanning workflow:

```bash
# Tencent scanner
pytest tests/integration/test_scanner_integration.py -v -s \
  --provider=tencent \
  --test-bucket=$TEST_BUCKET

# Aliyun scanner
pytest tests/integration/test_scanner_integration.py -v -s \
  --provider=aliyun \
  --test-bucket=$TEST_BUCKET
```

### Level 4: Destructive Tests

**⚠️ WARNING: These tests DELETE files!**

```bash
# 1. Create test files first
# Upload test-delete-1.txt and test-delete-2.txt to your test bucket

# 2. Run delete tests
pytest tests/integration/test_tencent_provider.py::test_batch_delete_success -v -s \
  --test-bucket=$TEST_BUCKET \
  --enable-delete
```

## Test Scenarios

### Scenario 1: First-Time Setup

You've just set up credentials and want to verify everything works:

```bash
# Step 1: Verify credentials
pytest tests/integration/test_tencent_provider.py::test_list_buckets_success -v -s

# Step 2: Pick a test bucket from the output
export TEST_BUCKET=my-test-bucket

# Step 3: Test file listing
pytest tests/integration/test_tencent_provider.py::test_list_files_success -v -s \
  --test-bucket=$TEST_BUCKET

# Step 4: Test scanner
pytest tests/integration/test_scanner_integration.py::test_scanner_with_real_provider -v -s \
  --provider=tencent
```

### Scenario 2: Testing Before Deployment

You want comprehensive testing before deploying to production:

```bash
# Run all non-destructive tests
pytest tests/integration/ -v -s \
  --test-bucket=$TEST_BUCKET \
  -k "not delete"

# Check rate limiting
pytest tests/integration/test_tencent_provider.py::test_rate_limiter_integration -v -s
```

### Scenario 3: Testing Pattern Matching

You want to verify pattern matching works correctly:

```bash
# Test bucket pattern matching
pytest tests/integration/test_scanner_integration.py::test_scanner_with_bucket_pattern -v -s \
  --provider=tencent \
  --test-bucket=$TEST_BUCKET

# Test file pattern matching (*.txt files)
pytest tests/integration/test_scanner_integration.py::test_scanner_with_file_pattern -v -s \
  --provider=tencent \
  --test-bucket=$TEST_BUCKET
```

### Scenario 4: Performance Testing

Test with large buckets:

```bash
# Test pagination with large file lists
pytest tests/integration/test_aliyun_provider.py::test_list_files_pagination -v -s \
  --test-bucket=$TEST_BUCKET

# Test lazy evaluation
pytest tests/integration/test_scanner_integration.py::test_scanner_lazy_evaluation -v -s \
  --provider=tencent
```

## Common Issues

### Issue: Tests Skipped

**Symptom:**
```
SKIPPED [1] Tencent credentials not configured
```

**Solution:**
1. Check `.env` file exists in project root
2. Verify all required environment variables are set
3. Try loading manually:
   ```bash
   python -c "from cloud_storage_clean.config import load_tencent_config; print(load_tencent_config())"
   ```

### Issue: Bucket Not Found

**Symptom:**
```
BucketNotFoundError: Bucket not found: your-test-bucket
```

**Solutions:**
1. **Wrong bucket name**: Verify spelling and check cloud console
2. **Wrong region**: For Tencent, ensure bucket is in TENCENT_REGION
3. **Wrong endpoint**: For Aliyun, verify endpoint matches bucket location
4. **No permissions**: Check IAM permissions include `GetBucket`

### Issue: Access Denied

**Symptom:**
```
AuthenticationError: Access denied
```

**Solutions:**
1. **Invalid credentials**: Check ACCESS_KEY and SECRET_KEY are correct
2. **Insufficient permissions**: Verify IAM policy includes:
   - Tencent: `cos:GetService`, `cos:GetBucket`, `cos:DeleteObject`
   - Aliyun: `oss:ListBuckets`, `oss:ListObjects`, `oss:DeleteObject`
3. **IP restrictions**: Check if API access has IP whitelist restrictions
4. **Temporary credentials expired**: If using STS, refresh tokens

### Issue: Rate Limit Exceeded

**Symptom:**
```
RateLimitError: Rate limit exceeded
```

**Solutions:**
1. Wait 1-2 minutes before retrying
2. Tests already use conservative rate limit (10 calls/sec)
3. Check your account quota hasn't been exceeded
4. Consider splitting tests into smaller batches

## Test Data Setup

### Creating Test Files

For comprehensive testing, create diverse test files:

```bash
# In your test bucket, create:

# 1. Files for pattern matching tests
test-file-1.txt
test-file-2.txt
logs/app.log
logs/error.log
temp/cache.tmp

# 2. Files with different ages
# (Manually adjust last-modified dates or wait)

# 3. Files for deletion tests
test-delete-1.txt  # Small file
test-delete-2.txt  # Small file
```

### Using Cloud Console

**Tencent COS:**
1. Go to https://console.cloud.tencent.com/cos
2. Select your test bucket
3. Upload test files
4. Note bucket name for `--test-bucket` parameter

**Aliyun OSS:**
1. Go to https://oss.console.aliyun.com/
2. Select your test bucket
3. Upload test files
4. Note bucket name and endpoint

## Continuous Integration

Example GitHub Actions workflow:

```yaml
# .github/workflows/integration-tests.yml
name: Integration Tests

on:
  schedule:
    - cron: '0 2 * * 1'  # Weekly

jobs:
  integration:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          python -m venv venv
          source venv/bin/activate
          pip install -e .
          pip install pytest pytest-cov pytest-mock

      - name: Run integration tests
        env:
          TENCENT_SECRET_ID: ${{ secrets.TENCENT_SECRET_ID }}
          TENCENT_SECRET_KEY: ${{ secrets.TENCENT_SECRET_KEY }}
          ALIYUN_ACCESS_KEY_ID: ${{ secrets.ALIYUN_ACCESS_KEY_ID }}
          ALIYUN_ACCESS_KEY_SECRET: ${{ secrets.ALIYUN_ACCESS_KEY_SECRET }}
        run: |
          source venv/bin/activate
          pytest tests/integration/ -v --tb=short -k "not delete"
```

## Security Best Practices

1. **Never commit credentials**
   - `.env` is in `.gitignore`
   - Use GitHub Secrets for CI/CD
   - Rotate credentials if exposed

2. **Use least-privilege credentials**
   - Create separate IAM user for testing
   - Grant only required permissions
   - Restrict to test buckets only

3. **Monitor API usage**
   - Check billing after test runs
   - Set up usage alerts
   - Review API access logs

4. **Protect test buckets**
   - Use clear naming (e.g., `test-*` prefix)
   - Enable versioning as backup
   - Set lifecycle rules to clean old data

## Getting Help

If you encounter issues:

1. **Check logs**: Use `-v -s` for verbose output
2. **Verify credentials**: Test in cloud console first
3. **Review IAM**: Ensure all required permissions
4. **Check region/endpoint**: Must match bucket location
5. **Open issue**: Include sanitized logs (remove credentials!)

## Next Steps

After successful integration testing:

1. ✅ Run E2E tests (full CLI workflow)
2. ✅ Security review
3. ✅ Performance benchmarks
4. ✅ Production deployment planning
