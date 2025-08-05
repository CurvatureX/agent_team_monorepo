import os
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Core service configuration
    port: int = 8003
    host: str = "0.0.0.0"
    debug: bool = False
    service_name: str = "workflow_scheduler"

    # External service URLs
    workflow_engine_url: str = "http://workflow-engine:8002"
    api_gateway_url: str = "http://api-gateway:8000"

    # Database configuration
    database_url: str = "postgresql://user:pass@postgres/workflow_scheduler"
    redis_url: str = "redis://redis:6379/1"

    # Email monitoring configuration (for EmailTrigger)
    imap_server: str = "imap.gmail.com"
    email_user: Optional[str] = None
    email_password: Optional[str] = None
    email_check_interval: int = 60

    # Migadu SMTP configuration (for sending notifications)
    smtp_host: str = "smtp.migadu.com"  # Fixed for Migadu
    smtp_port: int = 465  # 465 for SSL, 587 for STARTTLS
    smtp_username: Optional[str] = None  # Your full Migadu email address
    smtp_password: Optional[str] = None  # Your Migadu email password
    smtp_use_tls: bool = False  # False = SSL (port 465), True = STARTTLS (port 587)
    smtp_use_ssl: bool = True  # Automatically handled by Migadu client
    smtp_sender_email: Optional[str] = None  # Defaults to smtp_username
    smtp_sender_name: Optional[str] = "Workflow Scheduler"
    smtp_timeout: int = 30

    # GitHub App configuration
    github_app_id: Optional[str] = None
    github_app_private_key: Optional[str] = None
    github_webhook_secret: Optional[str] = None
    github_api_base_url: str = "https://api.github.com"

    # APScheduler configuration
    scheduler_timezone: str = "UTC"
    scheduler_max_workers: int = 10

    # Distributed lock configuration
    lock_timeout: int = 300  # 5 minutes
    lock_retry_delay: float = 0.1

    # Logging configuration
    log_level: str = "INFO"
    log_format: str = "json"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Ignore unknown environment variables
    )


# Global settings instance
settings = Settings()
