# Environment Variables Reference

> **Source of Truth**: `.env.example`
>
> This document is automatically generated from `.env.example`. All environment variable definitions should be updated in `.env.example` first, then this documentation regenerated.

## Quick Setup

```bash
# Copy template
cp .env.example .env

# Edit with your credentials
nano .env  # or vim, code, etc.
```

## Configuration Overview

The application is configured entirely through environment variables defined in a `.env` file.

### Configuration Sections

1. **Tencent COS Configuration** - For Tencent Cloud Object Storage
2. **Aliyun OSS Configuration** - For Aliyun Object Storage Service
3. **Application Configuration** - Runtime behavior settings

## Tencent COS Configuration

### TENCENT_SECRET_ID

- **Required**: Yes (if using Tencent provider)
- **Default**: None
- **Format**: String (starts with "AKID")
- **Example**: `TENCENT_SECRET_ID=AKIDxxxxxxxxxxxxxxxxxxxxxx`

**Description**: Tencent Cloud API Secret ID for authentication.

**How to Obtain**:
1. Visit [Tencent Cloud API Key Management](https://console.cloud.tencent.com/cam/capi)
2. Click "Create Key" or use existing key
3. Copy the **SecretId** value

**Security Notes**:
- Never commit to version control
- Rotate regularly (recommended: every 90 days)
- Use least-privilege IAM policies

---

### TENCENT_SECRET_KEY

- **Required**: Yes (if using Tencent provider)
- **Default**: None
- **Format**: String (32-40 characters)
- **Example**: `TENCENT_SECRET_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`

**Description**: Tencent Cloud API Secret Key for authentication.

**How to Obtain**:
1. Visit [Tencent Cloud API Key Management](https://console.cloud.tencent.com/cam/capi)
2. Create or view existing key
3. Copy the **SecretKey** value (shown only once at creation)

**Security Notes**:
- Masked in logs automatically (Pydantic SecretStr)
- Store securely (never in plain text in production)
- If compromised, rotate immediately

---

## Aliyun OSS Configuration

### ALIYUN_ACCESS_KEY_ID

- **Required**: Yes (if using Aliyun provider)
- **Default**: None
- **Format**: String (starts with "LTAI")
- **Example**: `ALIYUN_ACCESS_KEY_ID=LTAI5xxxxxxxxxxxxx`

**Description**: Aliyun AccessKey ID for authentication.

**How to Obtain**:
1. Visit [Aliyun RAM Console](https://ram.console.aliyun.com/)
2. Navigate to **AccessKey Management**
3. Create new AccessKey or use existing
4. Copy the **AccessKeyId** value

**Security Notes**:
- Never commit to version control
- Rotate regularly (recommended: every 90 days)
- Use RAM user policies (not root account)

---

### ALIYUN_ACCESS_KEY_SECRET

- **Required**: Yes (if using Aliyun provider)
- **Default**: None
- **Format**: String (30 characters)
- **Example**: `ALIYUN_ACCESS_KEY_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`

**Description**: Aliyun AccessKey Secret for authentication.

**How to Obtain**:
1. Visit [Aliyun RAM Console](https://ram.console.aliyun.com/)
2. Create new AccessKey
3. Copy the **AccessKeySecret** (shown only once at creation)

**Security Notes**:
- Masked in logs automatically (Pydantic SecretStr)
- Cannot be retrieved after creation (must create new if lost)
- If compromised, disable and create new key immediately

---

## Application Configuration

### LOG_FILE

- **Required**: No
- **Default**: Empty (no file logging)
- **Format**: String (file path, relative or absolute)
- **Example**: `LOG_FILE=logs/cleanup.log`

**Description**: Path to file where structured JSON logs will be written.

**Behavior**:
- If empty: Only console output (no file logging)
- If set: Logs written to file in structured JSON format
- Can be overridden with `--log-file` CLI flag

**Examples**:
```bash
# Relative path (current directory)
LOG_FILE=cleanup.log

# Relative path (subdirectory)
LOG_FILE=logs/cleanup.log

# Absolute path
LOG_FILE=/var/log/cloud-storage-clean/cleanup.log

# Home directory
LOG_FILE=~/cloud-storage-cleanup.log
```

**Best Practices**:
- Create logs directory: `mkdir -p logs`
- Add to `.gitignore`: `echo "logs/" >> .gitignore`
- Use dated filenames via CLI: `--log-file logs/cleanup-$(date +%Y%m%d).log`

---

### VERBOSE

- **Required**: No
- **Default**: `false`
- **Format**: Boolean (`true` or `false`)
- **Example**: `VERBOSE=true`

**Description**: Enable verbose debug-level logging.

**Behavior**:
- `false`: INFO level and above (recommended for production)
- `true`: DEBUG level and above (detailed logging)
- Can be overridden with `--verbose` CLI flag

**When to Use**:
- Debugging issues
- Understanding API call patterns
- Monitoring rate limiting behavior
- Troubleshooting authentication

**Performance Impact**: Minimal (logging is asynchronous)

---

### RATE_LIMIT

- **Required**: No
- **Default**: `100`
- **Format**: Integer (1-1000)
- **Example**: `RATE_LIMIT=50`

**Description**: Maximum API calls per second (token bucket algorithm).

**Behavior**:
- Limits API request rate to prevent throttling
- Applies to both list and delete operations
- Self-refilling token bucket implementation

**Recommendations**:
- **Conservative**: `50` calls/sec (safe starting point)
- **Default**: `100` calls/sec (balanced)
- **Aggressive**: `150-200` calls/sec (only if provider allows)

**Provider Limits**:
- **Tencent COS**: ~100-200 calls/sec (varies by region)
- **Aliyun OSS**: ~200-300 calls/sec (varies by bucket)

**Tuning**:
1. Start conservative (50)
2. Monitor for rate limit errors
3. Gradually increase if stable
4. Contact provider to increase limits if needed

---

### BATCH_SIZE

- **Required**: No
- **Default**: `100`
- **Format**: Integer (1-1000)
- **Example**: `BATCH_SIZE=200`

**Description**: Maximum number of files per batch deletion operation.

**Behavior**:
- Files are deleted in batches to improve efficiency
- Larger batches = fewer API calls
- Smaller batches = better error isolation
- Hard limit: 1000 (enforced by code)

**Trade-offs**:

| Batch Size | API Calls | Error Isolation | Risk |
|------------|-----------|-----------------|------|
| 50 | More | Excellent | Low |
| 100 | Balanced | Good | Medium |
| 200 | Fewer | Fair | Higher |
| 1000 | Minimal | Poor | Highest |

**Recommendations**:
- **Conservative**: `50` (better error handling)
- **Default**: `100` (balanced approach)
- **Aggressive**: `200-500` (faster, but higher risk per batch)

**Provider Limits**:
- **Tencent COS**: Max 1000 files per batch
- **Aliyun OSS**: Max 1000 files per batch

---

## Complete Configuration Examples

### Example 1: Tencent COS Production

```bash
# Tencent COS Configuration
TENCENT_SECRET_ID=AKIDxxxxxxxxxxxxxxxxxxxxxx
TENCENT_SECRET_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Application Configuration
LOG_FILE=logs/cleanup.log
VERBOSE=false
RATE_LIMIT=100
BATCH_SIZE=100
```

### Example 2: Aliyun OSS Development

```bash
# Aliyun OSS Configuration
ALIYUN_ACCESS_KEY_ID=LTAI5xxxxxxxxxxxxx
ALIYUN_ACCESS_KEY_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Application Configuration
LOG_FILE=logs/dev-cleanup.log
VERBOSE=true
RATE_LIMIT=50
BATCH_SIZE=50
```

### Example 3: Both Providers (Multi-Cloud)

```bash
# Tencent COS Configuration
TENCENT_SECRET_ID=AKIDxxxxxxxxxxxxxxxxxxxxxx
TENCENT_SECRET_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Aliyun OSS Configuration
ALIYUN_ACCESS_KEY_ID=LTAI5xxxxxxxxxxxxx
ALIYUN_ACCESS_KEY_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Application Configuration
LOG_FILE=logs/multicloud-cleanup.log
VERBOSE=false
RATE_LIMIT=100
BATCH_SIZE=100
```

### Example 4: Minimal Configuration

```bash
# Only required fields
TENCENT_SECRET_ID=AKIDxxxxxxxxxxxxxxxxxxxxxx
TENCENT_SECRET_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# All other fields use defaults
```

## Validation Rules

### Required Field Validation

The application validates configuration at startup:

- **Tencent**: Requires `TENCENT_SECRET_ID` and `TENCENT_SECRET_KEY` when using `tencent` provider
- **Aliyun**: Requires `ALIYUN_ACCESS_KEY_ID` and `ALIYUN_ACCESS_KEY_SECRET` when using `aliyun` provider

### Error Messages

**Missing Credentials**:
```
Configuration error:
1 validation error for TencentConfig
secret_id
  Field required [type=missing, input_value={}, input_type=dict]
```

**Invalid Format**:
```
Configuration error:
Invalid value for RATE_LIMIT: must be between 1 and 1000
```

## Security Best Practices

### DO ✅

- Use `.env` files for local development
- Use environment variables in production (not files)
- Add `.env` to `.gitignore`
- Rotate credentials every 90 days
- Use least-privilege IAM policies
- Enable verbose logging for debugging only
- Use `--dry-run` before actual deletions

### DON'T ❌

- Commit `.env` files to version control
- Share credentials via email or chat
- Use root account credentials
- Hardcode credentials in source code
- Use HTTP scheme in production
- Disable logging in production
- Skip dry-run for large deletions

## Troubleshooting

### Issue: "Configuration error: secret_id Field required"

**Cause**: Missing required environment variable

**Fix**:
1. Check `.env` file exists: `ls -la .env`
2. Verify variable is set: `grep "TENCENT_SECRET_ID" .env`
3. Ensure no typos in variable name
4. Restart application after changes

---

### Issue: "Authentication failed"

**Cause**: Invalid credentials

**Fix**:
1. Verify credentials in cloud console
2. Check for extra spaces: `TENCENT_SECRET_ID= AKIDxxx` (wrong)
3. Ensure no quotes around values: `TENCENT_SECRET_ID="AKIDxxx"` (wrong)
4. Correct format: `TENCENT_SECRET_ID=AKIDxxx` (correct)

---

### Issue: "Rate limit exceeded"

**Cause**: RATE_LIMIT too high

**Fix**:
```bash
# Reduce in .env
RATE_LIMIT=50

# Or contact provider to increase limits
```

---

### Issue: Logs not being written

**Cause**: LOG_FILE path invalid or directory doesn't exist

**Fix**:
```bash
# Create logs directory
mkdir -p logs

# Set in .env
LOG_FILE=logs/cleanup.log

# Test
cloud-storage-clean list-buckets tencent --verbose
cat logs/cleanup.log
```

## Testing Configuration

### Verify Tencent COS Configuration

```bash
# Test connection
cloud-storage-clean list-buckets tencent

# Expected: List of buckets
# Error: Check credentials
```

### Verify Aliyun OSS Configuration

```bash
# Test connection
cloud-storage-clean list-buckets aliyun

# Expected: List of buckets
# Error: Check credentials
```

### Verify Logging Configuration

```bash
# Run with logging
cloud-storage-clean list-buckets tencent --verbose

# Check log file was created
cat logs/cleanup.log | jq
```

## Migration Guide

### From Hardcoded Credentials

**Before** (❌ Bad):
```python
secret_id = "AKIDxxxxx"
secret_key = "xxxxxxxx"
```

**After** (✅ Good):
```bash
# In .env
TENCENT_SECRET_ID=AKIDxxxxx
TENCENT_SECRET_KEY=xxxxxxxx
```

### From Different Environment Variable Names

If migrating from a system using different variable names:

```bash
# Old names (example)
TENCENT_COS_SECRET_ID=xxx
TENCENT_COS_SECRET_KEY=xxx

# New names (required)
TENCENT_SECRET_ID=xxx
TENCENT_SECRET_KEY=xxx
```

## References

- **Tencent COS Documentation**: https://cloud.tencent.com/document/product/436
- **Aliyun OSS Documentation**: https://help.aliyun.com/product/31815.html
- **Pydantic Settings**: https://docs.pydantic.dev/latest/concepts/pydantic_settings/
- **Python dotenv**: https://github.com/theskumar/python-dotenv
