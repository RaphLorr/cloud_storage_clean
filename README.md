# Cloud Storage Cleanup Tool

清理腾讯云 COS / 阿里云 OSS 中的废弃文件，释放存储空间，降低云存储费用。

## 为什么需要这个工具？

云存储按量计费，长期积累的过期日志、临时文件、旧备份等会持续产生费用。手动清理耗时且容易遗漏，这个工具可以：

- **按时间批量清理** — 删除指定日期之前的旧文件
- **按文件类型筛选** — 只清理 `*.log`、`*.tmp`、`*.mp4` 等指定类型
- **跨 Bucket 操作** — 用正则一次匹配多个 Bucket，无需逐个处理
- **先看再删** — `--dry-run` 预览要删除的文件和大小，确认后再执行
- **自动识别跨区域 Bucket** — 无需手动配置 region/endpoint

## 快速开始

### 安装

```bash
python3 -m venv venv && source venv/bin/activate
pip install -e .
```

### 配置凭证

```bash
cp .env.example .env
```

编辑 `.env`，填入云厂商密钥（只需要你用到的那个）：

```bash
# 腾讯云 COS
TENCENT_SECRET_ID=your_secret_id
TENCENT_SECRET_KEY=your_secret_key

# 阿里云 OSS
ALIYUN_ACCESS_KEY_ID=your_access_key_id
ALIYUN_ACCESS_KEY_SECRET=your_access_key_secret
```

### 典型工作流

```bash
# 1. 先看看有哪些 Bucket
cloud-storage-clean list-buckets tencent

# 2. 统计一下各类文件占了多少空间
cloud-storage-clean stat tencent ".*" 2025-01-01

# 3. 预览要清理的文件（不会真删）
cloud-storage-clean clean tencent "test-.*" "*.log" 2025-01-01 --dry-run

# 4. 确认没问题，执行清理
cloud-storage-clean clean tencent "test-.*" "*.log" 2025-01-01
```

## 命令参考

### `stat` — 查看存储占用

统计指定日期前各类文件的数量和大小，帮你找到最值得清理的目标：

```bash
cloud-storage-clean stat PROVIDER BUCKET_PATTERN BEFORE [OPTIONS]

# 示例：查看所有 Bucket 中 2025 年前的文件分布
cloud-storage-clean stat aliyun ".*" 2025-01-01

# 只看测试环境
cloud-storage-clean stat tencent "test-.*" 2024-06-01
```

### `list-files` — 列出匹配文件

列出符合条件的文件明细，不做删除：

```bash
cloud-storage-clean list-files PROVIDER BUCKET_PATTERN FILE_PATTERN BEFORE [OPTIONS]

# 示例：查看测试 Bucket 中的旧视频文件
cloud-storage-clean list-files tencent "test-.*" "*.mp4" 2025-01-01
```

### `clean` — 批量清理文件

删除匹配的文件，默认会显示摘要并要求确认：

```bash
cloud-storage-clean clean PROVIDER BUCKET_PATTERN FILE_PATTERN BEFORE [OPTIONS]
```

| 参数 | 说明 |
|------|------|
| `PROVIDER` | 云厂商：`tencent` 或 `aliyun` |
| `BUCKET_PATTERN` | Bucket 名称正则（如 `"test-.*"`） |
| `FILE_PATTERN` | 文件名 glob 模式（如 `"*.log"`、`"temp/*"`） |
| `BEFORE` | 删除此日期之前的文件（格式 `YYYY-MM-DD`） |

| 选项 | 说明 |
|------|------|
| `--dry-run` | 只预览，不实际删除 |
| `--tz TZ` | 指定时区（如 `Asia/Shanghai`），默认使用本机时区 |
| `--no-confirm` | 跳过确认直接删除（慎用） |
| `--log-file PATH` | 将操作日志写入 JSON 文件 |
| `--verbose` | 输出调试级别日志 |

### `list-buckets` — 列出 Bucket

```bash
cloud-storage-clean list-buckets PROVIDER [--pattern REGEX]
```

## 使用场景

### 清理测试环境日志

```bash
cloud-storage-clean clean tencent "test-env-.*" "*.log" 2024-01-01 --log-file cleanup.log
```

### 删除过期备份

```bash
cloud-storage-clean clean tencent "backup-.*" "backup-*.tar.gz" 2023-01-01
```

### 清理 staging 临时文件

```bash
cloud-storage-clean clean aliyun "staging-.*" "temp/*" 2024-06-01
```

### 定时清理脚本（cron）

```bash
cloud-storage-clean clean tencent "logs-.*" "*.log" $(date -d '30 days ago' +%Y-%m-%d) \
  --tz Asia/Shanghai \
  --log-file logs/cleanup-$(date +%Y%m%d).log \
  --no-confirm
```

## 安全机制

- **确认提示** — 删除前显示文件数量、总大小、Bucket 分布，需手动确认
- **Dry-run 模式** — `--dry-run` 模拟整个流程但不实际删除任何文件
- **操作日志** — 所有删除操作写入结构化 JSON 日志，便于审计
- **错误隔离** — 单个文件删除失败不会中断整个批次

## 时区说明

日期参数默认使用本机时区。团队协作时建议显式指定，避免不同机器结果不一致：

```bash
cloud-storage-clean clean tencent "test-.*" "*.log" 2025-01-01 --tz Asia/Shanghai
```

常用时区：`Asia/Shanghai`（北京时间）、`UTC`、`America/New_York`

## 故障排查

| 错误 | 原因 | 解决 |
|------|------|------|
| `AuthenticationError` | 凭证无效或权限不足 | 检查 `.env` 中的密钥，确认 IAM 权限 |
| `RateLimitError` | API 调用频率超限 | 在 `.env` 中调低 `RATE_LIMIT`（默认 100） |
| `BucketNotFoundError` | Bucket 不存在 | 用 `list-buckets` 确认名称，检查凭证权限 |

## License

MIT License
