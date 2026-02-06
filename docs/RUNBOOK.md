# Operations Runbook

## Deployment Procedures

### Production Deployment

This is a CLI tool, not a service, so "deployment" means installing on user machines.

#### Method 1: pip install (Recommended for End Users)

```bash
# Install from PyPI (when published)
pip install cloud-storage-clean

# Verify installation
cloud-storage-clean --help
```

#### Method 2: Development Install (For Contributors)

```bash
# Clone repository
git clone <repository-url>
cd cloud_storage_clean

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install in development mode
pip install -e .

# Verify installation
cloud-storage-clean --help
```

#### Method 3: Poetry Install (For Developers)

```bash
# Install with Poetry
poetry install

# Activate virtual environment
poetry shell

# Verify installation
cloud-storage-clean --help
```

### Configuration Deployment

**Environment Variables Setup:**

1. **Create `.env` file:**
   ```bash
   cp .env.example .env
   ```

2. **Configure credentials** (see Environment Variables section below)

3. **Verify configuration:**
   ```bash
   # Test connection
   cloud-storage-clean list-buckets tencent
   ```

**Security Best Practices:**

- ✅ Never commit `.env` files
- ✅ Use restrictive IAM permissions
- ✅ Rotate credentials regularly
- ✅ Use read-only credentials for testing
- ✅ Enable verbose logging for auditing

### Release Process

**Creating a New Release:**

1. **Update version in `pyproject.toml`:**
   ```toml
   [tool.poetry]
   version = "0.2.0"
   ```

2. **Run tests:**
   ```bash
   make test
   make test-integration  # With credentials
   ```

3. **Update CHANGELOG.md** (if exists)

4. **Build package:**
   ```bash
   poetry build
   ```

5. **Publish to PyPI:**
   ```bash
   poetry publish
   ```

6. **Create Git tag:**
   ```bash
   git tag v0.2.0
   git push origin v0.2.0
   ```

## Monitoring and Alerts

### Log Monitoring

**Enable Structured Logging:**

```bash
# Configure in .env
LOG_FILE=logs/cleanup.log
VERBOSE=true
```

**Log Format (JSON):**

```json
{
  "event": "file_deleted",
  "bucket": "test-bucket",
  "key": "app.log",
  "dry_run": false,
  "timestamp": "2024-02-06T10:30:00",
  "level": "info"
}
```

**Key Events to Monitor:**

| Event | Level | Description | Action Required |
|-------|-------|-------------|-----------------|
| `authentication_error` | ERROR | Cloud provider auth failed | Check credentials |
| `rate_limit_exceeded` | ERROR | API rate limit hit | Reduce RATE_LIMIT |
| `batch_delete_error` | ERROR | Batch deletion failed | Check logs for details |
| `deletion_completed` | INFO | Deletion finished | Review success/failed counts |
| `file_deleted` | INFO | Individual file deleted | Normal operation |
| `dry_run_simulated_batch` | INFO | Dry run batch simulated | Normal dry-run operation |

**Monitoring Commands:**

```bash
# Watch logs in real-time
tail -f logs/cleanup.log | jq

# Count errors
grep -c '"level":"error"' logs/cleanup.log

# Filter specific events
cat logs/cleanup.log | jq 'select(.event == "file_deleted")'

# View recent errors
cat logs/cleanup.log | jq 'select(.level == "error")' | tail -10

# Count deletions
cat logs/cleanup.log | jq 'select(.event == "file_deleted")' | wc -l
```

### Performance Monitoring

**Track Operation Metrics:**

```bash
# Monitor deletion speed
cat logs/cleanup.log | jq 'select(.event == "deletion_completed")' | \
  jq '{files: .total_files, success: .success, failed: .failed}'

# Track batch performance
cat logs/cleanup.log | jq 'select(.event == "dry_run_simulated_batch" or .event == "batch_delete_success")' | \
  jq '{bucket: .bucket, count: .file_count}'
```

**Performance Indicators:**

- **Scan Time**: Time to list all files (API rate limited)
- **Deletion Rate**: Files deleted per second
- **Success Rate**: Percentage of successful deletions
- **API Rate**: Calls per second (should stay under RATE_LIMIT)

### Health Checks

**Verify System Health:**

```bash
# Test connectivity
cloud-storage-clean list-buckets tencent --verbose

# Test with dry-run (no actual deletion)
cloud-storage-clean clean tencent "test-.*" "*.log" 2024-01-01 --dry-run

# Verify credentials
# Should succeed if credentials are valid
cloud-storage-clean list-buckets tencent
```

## Common Issues and Fixes

### Authentication Issues

**Issue**: `AuthenticationError: Invalid credentials`

**Diagnosis:**
```bash
# Check .env file exists
ls -la .env

# Verify credentials are set (without showing values)
grep "TENCENT_SECRET_ID" .env
grep "TENCENT_SECRET_KEY" .env
```

**Fix:**
1. Verify credentials in Tencent Cloud Console: https://console.cloud.tencent.com/cam/capi
2. Update `.env` with correct credentials
3. Ensure no extra spaces or quotes around values
4. Test connection: `cloud-storage-clean list-buckets tencent`

---

### Rate Limiting Issues

**Issue**: `RateLimitError: Too many requests`

**Diagnosis:**
```bash
# Check current rate limit
grep "RATE_LIMIT" .env
```

**Fix:**
```bash
# Reduce rate limit in .env
RATE_LIMIT=50  # Reduced from default 100

# Or use smaller batches
BATCH_SIZE=50  # Reduced from default 100
```

**Prevention:**
- Start with conservative rate limits (50 calls/sec)
- Monitor API usage in cloud provider console
- Contact provider to increase limits if needed

### Bucket Access Issues

**Issue**: `BucketNotFoundError: Bucket does not exist`

**Diagnosis:**
```bash
# List all accessible buckets
cloud-storage-clean list-buckets tencent

# Check bucket pattern
echo "test-.*" | grep -E "^test-.*$"
```

**Fix:**
1. Verify bucket name spelling
2. Check bucket exists in correct region
3. Verify credentials have bucket access permissions
4. Use `list-buckets` to see available buckets

---

**Issue**: `AccessDeniedError: Insufficient permissions`

**Fix:**
1. Verify IAM policy grants necessary permissions:
   - `cos:GetBucket` (list buckets)
   - `cos:GetObject` (list files)
   - `cos:DeleteObject` (delete files)
2. Update IAM policy in cloud provider console
3. Test with dry-run mode first: `--dry-run`

### Pattern Matching Issues

**Issue**: `ValueError: Invalid regex pattern`

**Diagnosis:**
```bash
# Test regex pattern
python3 -c "import re; re.compile('test-.*')"
```

**Fix:**
```bash
# Escape special characters
cloud-storage-clean clean tencent "test-\\..*" "*.log" 2024-01-01

# Use raw strings for complex patterns
cloud-storage-clean clean tencent "^test-[0-9]+$" "*.log" 2024-01-01
```

---

**Issue**: `ValueError: Invalid glob pattern`

**Fix:**
```bash
# Ensure glob patterns don't start with /
# WRONG: "/logs/*.log"
# RIGHT: "logs/*.log"

cloud-storage-clean clean tencent "test-.*" "logs/*.log" 2024-01-01
```

### Memory Issues

**Issue**: `MemoryError: Out of memory` (very rare, only with >1M files)

**Diagnosis:**
```bash
# Check number of matching files
cloud-storage-clean clean tencent ".*" "*.log" 2024-01-01 --dry-run
```

**Fix:**
```bash
# Process buckets individually
cloud-storage-clean clean tencent "^specific-bucket$" "*.log" 2024-01-01

# Use more specific patterns
cloud-storage-clean clean tencent "test-2024-.*" "logs/2024-*/*.log" 2024-01-01
```

### Deletion Failures

**Issue**: Some files fail to delete

**Diagnosis:**
```bash
# Check logs for specific errors
cat logs/cleanup.log | jq 'select(.event == "file_delete_failed")'

# Count failures
cat logs/cleanup.log | jq 'select(.event == "deletion_completed")' | \
  jq '{success: .success, failed: .failed}'
```

**Common Causes:**
1. **Object locked**: File has object lock enabled
2. **Versioned bucket**: Delete specific version ID
3. **Permissions**: Insufficient delete permissions
4. **In-progress upload**: Multipart upload not completed

**Fix:**
```bash
# Retry failed deletions
# Extract failed file keys from logs
cat logs/cleanup.log | jq 'select(.event == "file_delete_failed") | .key'

# Manual deletion via cloud console if needed
```

### Dry-Run Mode Issues

**Issue**: `--dry-run` still shows "deleted" in output

**Expected Behavior:**
- Dry-run mode performs real API calls for scanning
- Shows "would be deleted" instead of "deleted"
- No actual `batch_delete()` API calls made
- Console shows: "🔍 DRY RUN MODE - No files will be deleted"

**Verification:**
```bash
# Run dry-run and check logs
cloud-storage-clean clean tencent "test-.*" "*.log" 2024-01-01 \
  --dry-run --log-file dry-run.log

# Verify no actual deletions
cat dry-run.log | jq 'select(.event == "file_would_be_deleted")'
cat dry-run.log | jq 'select(.event == "dry_run_simulated_batch")'

# Files should still exist after dry-run
cloud-storage-clean list-buckets tencent
```

## Rollback Procedures

### Accidental Deletion Recovery

**⚠️ CRITICAL**: Cloud storage deletions are **irreversible** by default.

**Prevention (Before Deletion):**

1. **Always use dry-run first:**
   ```bash
   cloud-storage-clean clean tencent "prod-.*" "*.log" 2024-01-01 --dry-run
   ```

2. **Enable versioning on buckets** (Tencent COS / Aliyun OSS)

3. **Review deletion summary carefully** before confirming

4. **Use restrictive patterns** to limit scope

**Recovery Options (After Deletion):**

1. **Versioned Buckets:**
   - Deleted files can be recovered from previous versions
   - Use cloud provider console to restore

2. **Backup Recovery:**
   - Restore from backups if available
   - Check backup retention policies

3. **Cross-Region Replication:**
   - If enabled, files may exist in replica bucket

**Emergency Contacts:**
- Tencent Cloud Support: https://cloud.tencent.com/document/product/436
- Aliyun OSS Support: https://help.aliyun.com/product/31815.html

### Configuration Rollback

**Issue**: New configuration causes errors

**Rollback Steps:**

1. **Restore previous `.env`:**
   ```bash
   # If you have backup
   cp .env.backup .env

   # Or restore from .env.example
   cp .env.example .env
   # Re-enter credentials
   ```

2. **Verify configuration:**
   ```bash
   cloud-storage-clean list-buckets tencent --verbose
   ```

### Version Rollback

**Rollback to Previous Package Version:**

```bash
# Uninstall current version
pip uninstall cloud-storage-clean

# Install specific version
pip install cloud-storage-clean==0.1.0

# Verify version
cloud-storage-clean --version  # If version flag exists
```

## Operational Best Practices

### 1. Pre-Flight Checks

Before any deletion operation:

```bash
# Step 1: List matching buckets
cloud-storage-clean list-buckets tencent --pattern "test-.*"

# Step 2: Dry-run to preview deletions
cloud-storage-clean clean tencent "test-.*" "*.log" 2024-01-01 \
  --dry-run --log-file dry-run.log

# Step 3: Review dry-run logs
cat dry-run.log | jq 'select(.event == "deletion_completed")'

# Step 4: Execute real deletion (if satisfied)
cloud-storage-clean clean tencent "test-.*" "*.log" 2024-01-01 \
  --log-file real-deletion.log
```

### 2. Staged Rollout

For large-scale deletions:

```bash
# Stage 1: Test on single bucket
cloud-storage-clean clean tencent "^test-bucket-1$" "*.log" 2024-01-01

# Stage 2: Expand to subset
cloud-storage-clean clean tencent "^test-bucket-[1-3]$" "*.log" 2024-01-01

# Stage 3: Full rollout
cloud-storage-clean clean tencent "test-.*" "*.log" 2024-01-01
```

### 3. Logging Strategy

**Recommended logging setup:**

```bash
# In .env
LOG_FILE=logs/cleanup-$(date +%Y%m%d).log  # Note: shell expansion won't work in .env
VERBOSE=true

# Use CLI flag for dated logs
cloud-storage-clean clean tencent "test-.*" "*.log" 2024-01-01 \
  --log-file "logs/cleanup-$(date +%Y%m%d-%H%M%S).log"
```

### 4. Audit Trail

**Maintain audit logs:**

```bash
# Archive logs after operations
mkdir -p logs/archive
cp logs/cleanup.log "logs/archive/cleanup-$(date +%Y%m%d).log"

# Compress old logs
gzip logs/archive/*.log

# Review logs periodically
cat logs/cleanup.log | jq 'select(.event == "deletion_completed")' | \
  jq '{date: .timestamp, files: .total_files, success: .success}'
```

### 5. Security Hardening

**Credential Management:**

```bash
# Use environment variables (not .env file) in production
export TENCENT_SECRET_ID="xxx"
export TENCENT_SECRET_KEY="xxx"

# Clear after use
unset TENCENT_SECRET_ID
unset TENCENT_SECRET_KEY
```

**Least Privilege Permissions:**

```json
{
  "version": "2.0",
  "statement": [
    {
      "effect": "allow",
      "action": [
        "name/cos:GetBucket",
        "name/cos:GetObject",
        "name/cos:DeleteObject"
      ],
      "resource": [
        "qcs::cos:ap-guangzhou:uid/1234567890:test-*/",
        "qcs::cos:ap-guangzhou:uid/1234567890:test-*/*"
      ]
    }
  ]
}
```

## Disaster Recovery

### Backup Recommendations

**Before Large Deletions:**

1. **Create bucket inventory** (if not using dry-run):
   ```bash
   cloud-storage-clean list-buckets tencent > buckets-backup.txt
   ```

2. **Export file list** (using dry-run):
   ```bash
   cloud-storage-clean clean tencent "prod-.*" "*.log" 2024-01-01 \
     --dry-run --log-file files-to-delete.log
   ```

3. **Enable versioning** on critical buckets (via cloud console)

### Recovery Procedures

**If Accidental Deletion Occurs:**

1. **Stop immediately:**
   - Cancel operation (Ctrl+C)
   - Review what was deleted from logs

2. **Assess damage:**
   ```bash
   cat logs/cleanup.log | jq 'select(.event == "file_deleted")' | wc -l
   ```

3. **Attempt recovery:**
   - Check versioned buckets
   - Restore from backups
   - Contact cloud provider support

4. **Document incident:**
   - Files deleted
   - Recovery attempts
   - Lessons learned

## Escalation Procedures

### Level 1: User Issues

**Handler**: User / DevOps Team

**Issues**:
- Authentication errors
- Configuration problems
- Usage questions

**Resources**:
- README.md
- QUICKSTART.md
- This runbook

### Level 2: Technical Issues

**Handler**: Development Team

**Issues**:
- Bugs in deletion logic
- Performance problems
- Integration test failures

**Resources**:
- GitHub Issues
- Test logs
- Stack traces

### Level 3: Cloud Provider Issues

**Handler**: Cloud Provider Support

**Issues**:
- API outages
- Rate limit problems (cannot be resolved locally)
- Bucket access issues (policy-level)

**Contacts**:
- Tencent Cloud Support
- Aliyun OSS Support

## Maintenance Tasks

### Daily

- ✅ Review deletion logs for errors
- ✅ Monitor API rate limit usage
- ✅ Check failed deletions

### Weekly

- ✅ Archive old logs
- ✅ Review credential rotation schedule
- ✅ Check for package updates

### Monthly

- ✅ Rotate API credentials
- ✅ Review IAM permissions
- ✅ Update dependencies (`poetry update`)
- ✅ Run full test suite

### Quarterly

- ✅ Security audit
- ✅ Review and update documentation
- ✅ Test disaster recovery procedures
- ✅ Review and optimize rate limits

## Performance Tuning

### Rate Limit Optimization

**Finding Optimal Rate:**

```bash
# Start conservative
RATE_LIMIT=50

# Monitor errors
cloud-storage-clean clean tencent "test-.*" "*.log" 2024-01-01 --verbose

# Increase gradually
RATE_LIMIT=75   # If no errors
RATE_LIMIT=100  # If still stable
RATE_LIMIT=150  # Maximum recommended
```

### Batch Size Optimization

**Trade-offs:**
- Larger batches = Fewer API calls, but higher risk per batch
- Smaller batches = More API calls, but better error isolation

**Recommended:**
```bash
BATCH_SIZE=100  # Default, good balance
BATCH_SIZE=50   # More conservative
BATCH_SIZE=200  # More aggressive (only if stable)
```

### Large-Scale Operations

**For >100k files:**

```bash
# Process buckets individually (not via pattern)
for bucket in test-bucket-1 test-bucket-2 test-bucket-3; do
  cloud-storage-clean clean tencent "^${bucket}$" "*.log" 2024-01-01 \
    --log-file "logs/cleanup-${bucket}.log"
done
```

## Metrics and KPIs

### Key Metrics to Track

| Metric | Formula | Target | Alert Threshold |
|--------|---------|--------|-----------------|
| Success Rate | (success / total) × 100 | >99% | <95% |
| Deletion Speed | files / second | 50-100 | <10 |
| API Error Rate | (errors / total_calls) × 100 | <1% | >5% |
| Average Latency | time / total_files | <100ms | >500ms |

### Reporting

**Generate Monthly Report:**

```bash
# Extract metrics from logs
cat logs/cleanup-*.log | jq 'select(.event == "deletion_completed")' | \
  jq '{
    date: .timestamp,
    total: .total_files,
    success: .success,
    failed: .failed,
    success_rate: (.success / .total_files * 100)
  }'
```

## Emergency Procedures

### Emergency Stop

**If deletion is running and needs to stop immediately:**

```bash
# Press Ctrl+C
# Operation will stop after current batch completes
```

**Verify partial completion:**

```bash
cat logs/cleanup.log | jq 'select(.event == "deletion_completed")'
```

### Emergency Recovery

**If critical files were deleted:**

1. Check versioned buckets immediately
2. Contact cloud provider support
3. Attempt restore from backups
4. Document incident for post-mortem
