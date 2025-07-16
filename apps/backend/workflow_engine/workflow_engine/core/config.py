"""
Application configuration.
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings


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
    
    # Tool Integration Configuration
    credential_encryption_key: str = "your-credential-encryption-key"
    oauth2_state_expiry: int = 1800  # 30 minutes in seconds
    
    # Redis Configuration (reuse existing REDIS_URL from workflow_agent)
    redis_url: str = "redis://localhost:6379/1"  # Use database 1 to avoid conflicts
    
    # API Client Configuration
    api_timeout_connect: int = 5  # Connection timeout in seconds
    api_timeout_read: int = 30    # Read timeout in seconds
    api_max_retries: int = 3      # Maximum retry attempts
    api_retry_delays: str = "2,4,8"  # Retry delays in seconds (comma-separated)
    
    # OAuth2 Provider Configuration
    google_oauth_client_id: Optional[str] = None
    google_oauth_client_secret: Optional[str] = None
    github_oauth_client_id: Optional[str] = None
    github_oauth_client_secret: Optional[str] = None
    slack_oauth_client_id: Optional[str] = None
    slack_oauth_client_secret: Optional[str] = None
    
    # Security and Rate Limiting
    max_concurrent_requests_per_user: int = 10
    max_response_size_mb: int = 10
    
    def get_retry_delays(self) -> list[int]:
        """Parse retry delays from comma-separated string."""
        try:
            return [int(delay.strip()) for delay in self.api_retry_delays.split(",")]
        except (ValueError, AttributeError):
            return [2, 4, 8]  # Default fallback
    
    def get_max_response_size_bytes(self) -> int:
        """Get maximum response size in bytes."""
        return self.max_response_size_mb * 1024 * 1024
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
    
    def validate_encryption_key(self) -> None:
        """Validate encryption key configuration."""
        if len(self.credential_encryption_key) < 32:
            raise ValueError(
                f"credential_encryption_key must be at least 32 characters long. "
                f"Got {len(self.credential_encryption_key)} characters. "
                f"Generate a secure key with: "
                f"python -c \"from workflow_engine.core.encryption import CredentialEncryption; "
                f"print(CredentialEncryption.generate_key())\""
            )
    
    def validate_oauth2_providers(self) -> list[str]:
        """Validate OAuth2 provider configuration and return missing providers."""
        missing_providers = []
        
        # Check Google Calendar configuration
        if not self.google_oauth_client_id or not self.google_oauth_client_secret:
            missing_providers.append("Google Calendar")
        
        # Check GitHub configuration
        if not self.github_oauth_client_id or not self.github_oauth_client_secret:
            missing_providers.append("GitHub")
        
        # Check Slack configuration
        if not self.slack_oauth_client_id or not self.slack_oauth_client_secret:
            missing_providers.append("Slack")
        
        return missing_providers
    
    def get_oauth2_config(self, provider: str) -> dict:
        """Get OAuth2 configuration for a specific provider."""
        configs = {
            "google_calendar": {
                "client_id": self.google_oauth_client_id,
                "client_secret": self.google_oauth_client_secret,
                "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
                "token_url": "https://oauth2.googleapis.com/token",
                "scopes": ["https://www.googleapis.com/auth/calendar.events"],
            },
            "github": {
                "client_id": self.github_oauth_client_id,
                "client_secret": self.github_oauth_client_secret,
                "auth_url": "https://github.com/login/oauth/authorize",
                "token_url": "https://github.com/login/oauth/access_token",
                "scopes": ["repo", "read:user"],
            },
            "slack": {
                "client_id": self.slack_oauth_client_id,
                "client_secret": self.slack_oauth_client_secret,
                "auth_url": "https://slack.com/oauth/v2/authorize",
                "token_url": "https://slack.com/api/oauth.v2.access",
                "scopes": ["chat:write", "channels:read"],
            },
        }
        
        if provider not in configs:
            raise ValueError(f"Unknown OAuth2 provider: {provider}")
        
        return configs[provider]


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get application settings."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings 