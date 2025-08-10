"""
Configuration for Workflow Scheduler Service
"""

import os
from functools import lru_cache
from typing import Any, Dict

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Workflow Scheduler configuration settings
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    # Core Service Configuration
    service_name: str = Field(default="workflow_scheduler", description="Service name")
    host: str = Field(default="0.0.0.0", description="Service host")
    port: int = Field(default=8003, description="Service port")
    debug: bool = Field(default=False, description="Debug mode")

    # External Service URLs
    workflow_engine_url: str = Field(
        default="http://localhost:8002", description="Workflow Engine service URL"
    )
    api_gateway_url: str = Field(
        default="http://localhost:8000", description="API Gateway service URL"
    )

    # Database Configuration
    database_url: str = Field(
        default="postgresql://user:pass@localhost/workflow_scheduler",
        description="Database connection URL",
        validation_alias=AliasChoices("DATABASE_URL", "database_url"),
    )
    redis_url: str = Field(default="redis://localhost:6379/1", description="Redis connection URL")

    # Email Configuration (for EmailTrigger)
    imap_server: str = Field(default="imap.gmail.com", description="IMAP server")
    email_user: str = Field(default="", description="Email user")
    email_password: str = Field(default="", description="Email password")
    email_check_interval: int = Field(default=60, description="Email check interval in seconds")

    # SMTP Configuration (for notifications)
    smtp_host: str = Field(default="smtp.migadu.com", description="SMTP host")
    smtp_port: int = Field(default=465, description="SMTP port")
    smtp_username: str = Field(default="", description="SMTP username")
    smtp_password: str = Field(default="", description="SMTP password")
    smtp_use_tls: bool = Field(default=False, description="Use TLS for SMTP")
    smtp_use_ssl: bool = Field(default=True, description="Use SSL for SMTP")
    smtp_sender_email: str = Field(default="", description="SMTP sender email")
    smtp_sender_name: str = Field(default="Workflow Scheduler", description="SMTP sender name")
    smtp_timeout: int = Field(default=30, description="SMTP timeout in seconds")

    # GitHub App Configuration
    github_app_id: str = Field(default="", description="GitHub App ID")
    github_app_private_key: str = Field(default="", description="GitHub App private key")
    github_webhook_secret: str = Field(default="", description="GitHub webhook secret")

    # Slack Configuration
    slack_bot_token: str = Field(
        default="",
        description="Slack bot token",
        validation_alias=AliasChoices("DEFAULT_SLACK_BOT_TOKEN", "slack_bot_token"),
    )

    # APScheduler Configuration
    scheduler_timezone: str = Field(default="UTC", description="Scheduler timezone")
    scheduler_max_workers: int = Field(default=10, description="Scheduler max workers")

    # Distributed Lock Configuration
    lock_timeout: int = Field(default=300, description="Lock timeout in seconds")
    lock_retry_delay: float = Field(default=0.1, description="Lock retry delay in seconds")

    # Logging Configuration
    log_level: str = Field(default="INFO", description="Log level")
    log_format: str = Field(default="text", description="Log format (text/json)")

    def get_database_config(self) -> Dict[str, str]:
        """Get database configuration"""
        return {"url": self.database_url}

    def get_redis_config(self) -> Dict[str, str]:
        """Get Redis configuration"""
        return {"url": self.redis_url}

    def get_smtp_config(self) -> Dict[str, Any]:
        """Get SMTP configuration"""
        return {
            "host": self.smtp_host,
            "port": self.smtp_port,
            "username": self.smtp_username,
            "password": self.smtp_password,
            "use_tls": self.smtp_use_tls,
            "use_ssl": self.smtp_use_ssl,
            "sender_email": self.smtp_sender_email,
            "sender_name": self.smtp_sender_name,
            "timeout": self.smtp_timeout,
        }

    def get_github_config(self) -> Dict[str, str]:
        """Get GitHub configuration"""
        return {
            "app_id": self.github_app_id,
            "private_key": self.github_app_private_key,
            "webhook_secret": self.github_webhook_secret,
        }


@lru_cache()
def get_settings() -> Settings:
    """Get settings instance (cached)"""
    return Settings()


# Global settings instance
settings = get_settings()
