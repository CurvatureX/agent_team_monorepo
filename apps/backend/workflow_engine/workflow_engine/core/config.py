"""
Application configuration.
"""

import os
from typing import Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    # Database Configuration
    # 可以直接使用完整的数据库URL，或者分别配置各个参数
    database_url: Optional[str] = os.getenv("DATABASE_URL")

    # 数据库连接配置
    database_echo: bool = False
    database_pool_size: int = 10
    database_max_overflow: int = 20
    database_pool_timeout: int = 30
    database_pool_recycle: int = 3600

    # SSL配置（Supabase需要）
    database_ssl_mode: str = "require"  # require for Supabase

    # Server Configuration
    HOST: str = "0.0.0.0"
    PORT: int = int(os.getenv("PORT", "8002"))

    # Logging
    log_level: str = "INFO"

    # Security
    secret_key: str = "your-secret-key-here"

    # AI Configuration
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None

    @field_validator("database_url", mode="before")
    @classmethod
    def validate_database_url(cls, v):
        """Validate that DATABASE_URL is provided"""
        if not v:
            raise ValueError("DATABASE_URL environment variable is required")
        return v

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        # 允许额外的字段，保持兼容性
        extra = "ignore"


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get application settings."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
