"""
Three-Layer API Architecture Configuration Management
支持Public API、App API、MCP API的分层配置
"""

import os
from typing import Any, Dict, List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Three-layer API Gateway configuration"""

    # Supabase Configuration
    SUPABASE_URL: str = "https://your-project-id.supabase.co"  # Default placeholder
    SUPABASE_SECRET_KEY: str = ""  # Service Role key - used for all Supabase operations

    # gRPC Configuration
    WORKFLOW_SERVICE_HOST: str = "localhost"
    WORKFLOW_SERVICE_PORT: int = 50051

    # Authentication Configuration
    JWT_SECRET_KEY: Optional[str] = None  # For additional JWT operations if needed
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60  # Default 1 hour
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7  # Default 7 days

    # CORS Configuration
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",  # React dev server
        "http://localhost:8080",  # Vue dev server
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8080",
        "*",  # MVP: Allow all origins for development
    ]

    # Application Configuration
    APP_NAME: str = "Workflow Agent API Gateway"
    VERSION: str = "2.0.0"
    DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"
    LOG_LEVEL: str = os.getenv(
        "LOG_LEVEL", "DEBUG" if os.getenv("DEBUG", "true").lower() == "true" else "INFO"
    )
    LOG_FORMAT: str = os.getenv("LOG_FORMAT", "standard")  # standard, json, simple

    # Server Configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    RELOAD: bool = True

    # Redis Configuration
    REDIS_URL: str = "redis://localhost:6379/0"
    CACHE_TTL: int = 3600  # 缓存过期时间（秒）

    # Public API Configuration
    PUBLIC_API_ENABLED: bool = True
    PUBLIC_RATE_LIMIT_ENABLED: bool = True

    # App API Configuration
    APP_API_ENABLED: bool = True
    SUPABASE_AUTH_ENABLED: bool = True
    RLS_ENABLED: bool = True
    ENABLE_AUTH: bool = True  # Set to False to disable authentication for testing
    REQUIRE_EMAIL_VERIFICATION: bool = False  # MVP: Disable email verification for simplicity

    # MCP API Configuration
    MCP_API_ENABLED: bool = True
    MCP_API_KEY_REQUIRED: bool = True

    # API Key Management
    MCP_API_KEYS: Dict[str, Dict[str, Any]] = Field(
        default_factory=lambda: {
            "dev_default": {
                "client_name": "Development Client",
                "scopes": ["tools:read", "tools:execute", "health:check"],
                "rate_limit_tier": "development",
                "active": True,
            }
        }
    )

    # Rate Limiting Configuration
    RATE_LIMIT_STORAGE: str = "redis"  # redis, memory
    RATE_LIMIT_STRATEGY: str = "sliding_window"  # fixed_window, sliding_window

    # MCP Configuration
    MCP_ENABLED: bool = True
    NODE_KNOWLEDGE_SUPABASE_URL: str = ""
    NODE_KNOWLEDGE_SUPABASE_KEY: str = ""
    NODE_KNOWLEDGE_DEFAULT_THRESHOLD: float = 0.5
    MCP_MAX_RESULTS_PER_TOOL: int = 100
    SECRET_KEY: str = "your-secret-key-here"
    ELASTICSEARCH_HOST: str = "localhost"
    ELASTICSEARCH_PORT: int = 9200

    # Security Configuration
    API_SECRET_KEY: str = Field(
        default="your-secret-key-change-in-production", description="API 签名密钥"
    )
    JWT_SECRET_KEY: str = Field(
        default="jwt-secret-key-change-in-production", description="JWT 签名密钥"
    )
    ENCRYPTION_KEY: str = Field(default="encryption-key-change-in-production", description="数据加密密钥")

    # Monitoring Configuration
    METRICS_ENABLED: bool = True
    HEALTH_CHECK_ENABLED: bool = True

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # Ignore extra fields that don't match the model

    def get_supabase_config(self) -> dict:
        """Get Supabase configuration for client initialization"""
        return {
            "url": self.SUPABASE_URL,
            "service_key": self.SUPABASE_SECRET_KEY,
        }

    def is_production(self) -> bool:
        """Check if running in production environment"""
        return not self.DEBUG and "localhost" not in self.SUPABASE_URL


# Global settings instance
settings = Settings()
