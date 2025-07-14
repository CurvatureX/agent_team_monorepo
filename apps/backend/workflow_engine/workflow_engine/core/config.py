"""
Application configuration.
"""

import os
from typing import Optional
from pydantic import BaseSettings


class Settings(BaseSettings):
    """Application settings."""
    
    # Database
    database_url: str = "postgresql://postgres:password@localhost:5432/workflow_engine"
    database_echo: bool = False
    
    # gRPC Server
    grpc_host: str = "0.0.0.0"
    grpc_port: int = 50051
    
    # Logging
    log_level: str = "INFO"
    
    # Security
    secret_key: str = "your-secret-key-here"
    
    # AI Configuration
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get application settings."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings 