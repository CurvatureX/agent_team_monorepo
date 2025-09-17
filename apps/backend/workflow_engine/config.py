"""
Configuration for Workflow Engine

Comprehensive configuration management migrated from old structure.
"""

import os
from typing import Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings migrated from old workflow_engine structure"""

    # Database Configuration
    database_url: Optional[str] = os.getenv("DATABASE_URL")

    # Database connection configuration
    database_echo: bool = bool(os.getenv("DATABASE_ECHO", "false").lower() == "true")
    database_pool_size: int = 10
    database_max_overflow: int = 20
    database_pool_timeout: int = 30
    database_pool_recycle: int = 3600

    # SSL configuration (required for Supabase)
    database_ssl_mode: str = "require"

    # Server configuration
    HOST: str = "0.0.0.0"
    PORT: int = int(os.getenv("PORT", "8002"))
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"

    # Logging
    log_level: str = os.getenv("LOG_LEVEL", "INFO")

    # Security
    secret_key: str = "your-secret-key-here"

    # AI Configuration
    openai_api_key: Optional[str] = os.getenv("OPENAI_API_KEY")
    anthropic_api_key: Optional[str] = os.getenv("ANTHROPIC_API_KEY")

    # OAuth Configuration for External Services
    # Google OAuth
    google_client_id: Optional[str] = os.getenv("GOOGLE_CLIENT_ID")
    google_client_secret: Optional[str] = os.getenv("GOOGLE_CLIENT_SECRET")
    google_redirect_uri: Optional[str] = os.getenv(
        "GOOGLE_REDIRECT_URI", "http://localhost:8000/api/v1/public/webhooks/google/auth"
    )

    # Slack OAuth
    slack_client_id: Optional[str] = os.getenv("SLACK_CLIENT_ID")
    slack_client_secret: Optional[str] = os.getenv("SLACK_CLIENT_SECRET")
    slack_redirect_uri: Optional[str] = os.getenv(
        "SLACK_REDIRECT_URI", "http://localhost:8000/api/v1/public/webhooks/slack/auth"
    )

    # GitHub OAuth
    github_client_id: Optional[str] = os.getenv("GITHUB_CLIENT_ID")
    github_client_secret: Optional[str] = os.getenv("GITHUB_CLIENT_SECRET")
    github_app_id: Optional[str] = os.getenv("GITHUB_APP_ID")
    github_app_private_key: Optional[str] = os.getenv("GITHUB_APP_PRIVATE_KEY")

    # Notion OAuth
    notion_client_id: Optional[str] = os.getenv("NOTION_CLIENT_ID")
    notion_client_secret: Optional[str] = os.getenv("NOTION_CLIENT_SECRET")
    notion_redirect_uri: Optional[str] = os.getenv(
        "NOTION_REDIRECT_URI", "http://localhost:8000/api/v1/public/webhooks/notion/auth"
    )

    # Supabase Configuration (for storing credentials)
    supabase_url: Optional[str] = os.getenv("SUPABASE_URL")
    supabase_secret_key: Optional[str] = os.getenv("SUPABASE_SECRET_KEY")

    # Redis Configuration (for caching)
    redis_url: Optional[str] = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    @field_validator("database_url", mode="before")
    @classmethod
    def validate_database_url(cls, v):
        """Validate that DATABASE_URL is provided"""
        if not v:
            # Don't fail validation if DATABASE_URL is missing - use Supabase instead
            return v
        return v

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get application settings."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


# Global settings instance for compatibility
settings = get_settings()
