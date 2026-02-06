"""Configuration management with Pydantic Settings."""

from typing import Optional

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class TencentConfig(BaseSettings):
    """Tencent COS configuration."""

    secret_id: SecretStr = Field(..., validation_alias="TENCENT_SECRET_ID")
    secret_key: SecretStr = Field(..., validation_alias="TENCENT_SECRET_KEY")
    region: str = Field(default="ap-guangzhou", validation_alias="TENCENT_REGION")
    scheme: str = Field(default="https", validation_alias="TENCENT_SCHEME")

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


class AliyunConfig(BaseSettings):
    """Aliyun OSS configuration."""

    access_key_id: SecretStr = Field(..., validation_alias="ALIYUN_ACCESS_KEY_ID")
    access_key_secret: SecretStr = Field(..., validation_alias="ALIYUN_ACCESS_KEY_SECRET")
    endpoint: str = Field(
        default="oss-cn-hangzhou.aliyuncs.com", validation_alias="ALIYUN_ENDPOINT"
    )

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


class AppConfig(BaseSettings):
    """Application configuration."""

    log_file: Optional[str] = Field(default=None, validation_alias="LOG_FILE")
    verbose: bool = Field(default=False, validation_alias="VERBOSE")
    rate_limit: int = Field(default=100, validation_alias="RATE_LIMIT")
    batch_size: int = Field(default=100, validation_alias="BATCH_SIZE")

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


def load_tencent_config() -> TencentConfig:
    """Load Tencent COS configuration.

    Returns:
        Validated Tencent configuration.

    Raises:
        ValidationError: If required credentials are missing.
    """
    return TencentConfig()


def load_aliyun_config() -> AliyunConfig:
    """Load Aliyun OSS configuration.

    Returns:
        Validated Aliyun configuration.

    Raises:
        ValidationError: If required credentials are missing.
    """
    return AliyunConfig()


def load_app_config() -> AppConfig:
    """Load application configuration.

    Returns:
        Application configuration with defaults.
    """
    return AppConfig()
