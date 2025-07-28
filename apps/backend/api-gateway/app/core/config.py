"""
Unified Configuration Management for Three-Layer API Gateway
整合所有配置选项，支持FastAPI最佳实践
"""

import os
from functools import lru_cache
from typing import Any, Dict, List, Optional, Union

from pydantic import Field, validator
from pydantic_settings import BaseSettings


class DatabaseSettings(BaseSettings):
    """数据库相关配置"""

    # Supabase Configuration
    SUPABASE_URL: str = Field(
        default_factory=lambda: os.getenv("SUPABASE_URL", "https://your-project-id.supabase.co"),
        description="Supabase项目URL",
    )
    SUPABASE_SECRET_KEY: str = Field(
        default_factory=lambda: os.getenv("SUPABASE_SECRET_KEY", ""),
        description="Supabase服务角色密钥 (replaces both service and anon keys)",
    )

    # Redis Configuration
    REDIS_URL: str = Field(
        default_factory=lambda: os.getenv("REDIS_URL", "redis://localhost:6379/0"),
        description="Redis连接URL",
    )
    REDIS_POOL_SIZE: int = Field(default=20, description="Redis连接池大小")
    REDIS_CONNECT_TIMEOUT: int = Field(default=5, description="Redis连接超时时间（秒）")
    REDIS_SOCKET_TIMEOUT: int = Field(default=5, description="Redis套接字超时时间（秒）")

    # Cache TTL Settings (per data type)
    CACHE_TTL_DEFAULT: int = Field(default=3600, description="默认缓存过期时间（秒）")
    CACHE_TTL_JWT_TOKEN: int = Field(default=1800, description="JWT令牌缓存过期时间（秒）")
    CACHE_TTL_USER_INFO: int = Field(default=900, description="用户信息缓存过期时间（秒）")
    CACHE_TTL_RATE_LIMIT: int = Field(default=3600, description="限流计数器过期时间（秒）")
    CACHE_TTL_SESSION_STATE: int = Field(default=7200, description="会话状态缓存过期时间（秒）")


class AuthSettings(BaseSettings):
    """认证相关配置"""

    # JWT Configuration
    JWT_SECRET_KEY: str = Field(
        default="jwt-secret-key-change-in-production", description="JWT签名密钥"
    )
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=60, description="访问令牌过期时间（分钟）")
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7, description="刷新令牌过期时间（天）")

    # Authentication Toggle
    ENABLE_AUTH: bool = Field(default=True, description="启用认证（测试时可设为False）")
    SUPABASE_AUTH_ENABLED: bool = Field(default=True, description="启用Supabase认证")
    MCP_API_KEY_REQUIRED: bool = Field(default=True, description="MCP API需要API密钥")
    REQUIRE_EMAIL_VERIFICATION: bool = Field(default=False, description="需要邮箱验证")

    # RLS Configuration
    RLS_ENABLED: bool = Field(default=True, description="启用行级安全(RLS)")


class APILayerSettings(BaseSettings):
    """三层API配置"""

    # Public API Configuration
    PUBLIC_API_ENABLED: bool = Field(default=True, description="启用公共API层")
    PUBLIC_RATE_LIMIT_ENABLED: bool = Field(default=True, description="启用公共API限流")

    # App API Configuration
    APP_API_ENABLED: bool = Field(default=True, description="启用应用API层")

    # MCP API Configuration
    MCP_API_ENABLED: bool = Field(default=True, description="启用MCP API层")
    MCP_ENABLED: bool = Field(default=True, description="启用MCP服务")

    # API Key Management for MCP
    MCP_API_KEYS: Dict[str, Dict[str, Any]] = Field(
        default_factory=lambda: {
            "dev_default": {
                "client_name": "Development Client",
                "scopes": ["tools:read", "tools:execute", "health:check"],
                "rate_limit_tier": "development",
                "active": True,
            }
        },
        description="MCP API密钥配置",
    )


class ServiceSettings(BaseSettings):
    """外部服务配置"""

    # gRPC Services
    WORKFLOW_SERVICE_HOST: str = Field(default="localhost", description="工作流服务主机")
    WORKFLOW_SERVICE_PORT: int = Field(default=50051, description="工作流服务端口")
    WORKFLOW_AGENT_HOST: str = Field(default="localhost", description="工作流代理主机")
    WORKFLOW_AGENT_PORT: int = Field(default=50051, description="工作流代理端口")

    # MCP Services
    NODE_KNOWLEDGE_SUPABASE_URL: str = Field(default="", description="节点知识库Supabase URL")
    NODE_KNOWLEDGE_SUPABASE_KEY: str = Field(default="", description="节点知识库Supabase密钥")
    NODE_KNOWLEDGE_DEFAULT_THRESHOLD: float = Field(default=0.5, description="节点知识库默认阈值")
    MCP_MAX_RESULTS_PER_TOOL: int = Field(default=100, description="MCP工具最大结果数")

    # Elasticsearch Configuration
    ELASTICSEARCH_HOST: str = Field(default="localhost", description="Elasticsearch主机")
    ELASTICSEARCH_PORT: int = Field(default=9200, description="Elasticsearch端口")


class SecuritySettings(BaseSettings):
    """安全配置"""

    # API Keys
    API_SECRET_KEY: str = Field(
        default="your-secret-key-change-in-production", description="API签名密钥"
    )
    SECRET_KEY: str = Field(default="your-secret-key-here", description="应用密钥")
    ENCRYPTION_KEY: str = Field(default="encryption-key-change-in-production", description="数据加密密钥")

    # CORS Configuration
    ALLOWED_ORIGINS: List[str] = Field(
        default=[
            "http://localhost:3000",  # React dev server
            "http://localhost:8080",  # Vue dev server
            "http://127.0.0.1:3000",
            "http://127.0.0.1:8080",
            "*",  # MVP: Allow all origins for development
        ],
        description="允许的CORS源",
    )

    # Rate Limiting
    RATE_LIMIT_STORAGE: str = Field(default="redis", description="限流存储类型 (redis, memory)")
    RATE_LIMIT_STRATEGY: str = Field(
        default="sliding_window", description="限流策略 (fixed_window, sliding_window)"
    )


class AppSettings(BaseSettings):
    """应用程序配置"""

    # Basic App Info
    APP_NAME: str = Field(default="Workflow Agent API Gateway", description="应用名称")
    API_TITLE: str = Field(default="Workflow Agent API Gateway", description="API标题")
    VERSION: str = Field(default="2.0.0", description="API版本")
    API_VERSION: str = Field(default="2.0.0", description="API版本（兼容）")

    # Environment
    DEBUG: bool = Field(
        default_factory=lambda: os.getenv("DEBUG", "true").lower() == "true", description="调试模式"
    )
    ENVIRONMENT: str = Field(
        default=os.getenv("ENVIRONMENT", "development"),
        description="运行环境 (development, staging, production)",
    )

    # Server Configuration
    HOST: str = Field(default="0.0.0.0", description="服务器主机")
    PORT: int = Field(default=8000, description="服务器端口")
    RELOAD: bool = Field(default=True, description="自动重载")

    # Logging Configuration
    LOG_LEVEL: str = Field(
        default_factory=lambda: os.getenv(
            "LOG_LEVEL", "DEBUG" if os.getenv("DEBUG", "true").lower() == "true" else "INFO"
        ),
        description="日志级别",
    )
    LOG_FORMAT: str = Field(
        default=os.getenv("LOG_FORMAT", "standard"), description="日志格式 (standard, json, simple)"
    )

    # Monitoring
    METRICS_ENABLED: bool = Field(default=True, description="启用指标收集")
    HEALTH_CHECK_ENABLED: bool = Field(default=True, description="启用健康检查")


class Settings(
    DatabaseSettings, AuthSettings, APILayerSettings, ServiceSettings, SecuritySettings, AppSettings
):
    """
    统一配置类 - 继承所有配置组
    遵循FastAPI最佳实践的配置管理
    """

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # 忽略未定义的额外字段
        case_sensitive = True  # 环境变量大小写敏感

    @validator("SUPABASE_URL")
    def validate_supabase_url(cls, v):
        """验证Supabase URL格式"""
        # Skip validation for placeholder URLs
        if v and v not in ["https://your-project-id.supabase.co", "placeholder"]:
            if not v.startswith("https://") or not v.endswith(".supabase.co"):
                raise ValueError(
                    "Supabase URL must be in format: https://your-project-id.supabase.co"
                )
        return v

    @validator("LOG_LEVEL")
    def validate_log_level(cls, v):
        """验证日志级别"""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"LOG_LEVEL must be one of: {valid_levels}")
        return v.upper()

    @validator("LOG_FORMAT")
    def validate_log_format(cls, v):
        """验证日志格式"""
        valid_formats = ["standard", "json", "simple"]
        if v not in valid_formats:
            raise ValueError(f"LOG_FORMAT must be one of: {valid_formats}")
        return v

    def get_supabase_config(self) -> Dict[str, str]:
        """获取Supabase配置"""
        return {
            "url": self.SUPABASE_URL,
            "service_key": self.SUPABASE_SECRET_KEY,
        }

    def get_grpc_config(self) -> Dict[str, Union[str, int]]:
        """获取gRPC配置"""
        return {
            "workflow_service": {
                "host": self.WORKFLOW_SERVICE_HOST,
                "port": self.WORKFLOW_SERVICE_PORT,
            },
            "workflow_agent": {
                "host": self.WORKFLOW_AGENT_HOST,
                "port": self.WORKFLOW_AGENT_PORT,
            },
        }

    def get_redis_config(self) -> Dict[str, Union[str, int]]:
        """获取Redis配置"""
        return {
            "url": self.REDIS_URL,
            "pool_size": self.REDIS_POOL_SIZE,
            "connect_timeout": self.REDIS_CONNECT_TIMEOUT,
            "socket_timeout": self.REDIS_SOCKET_TIMEOUT,
            "ttl": {
                "default": self.CACHE_TTL_DEFAULT,
                "jwt_token": self.CACHE_TTL_JWT_TOKEN,
                "user_info": self.CACHE_TTL_USER_INFO,
                "rate_limit": self.CACHE_TTL_RATE_LIMIT,
                "session_state": self.CACHE_TTL_SESSION_STATE,
            },
        }

    def is_production(self) -> bool:
        """判断是否为生产环境"""
        return (
            not self.DEBUG
            and self.ENVIRONMENT == "production"
            and "localhost" not in self.SUPABASE_URL
        )

    def is_development(self) -> bool:
        """判断是否为开发环境"""
        return self.DEBUG or self.ENVIRONMENT == "development"


@lru_cache()
def get_settings() -> Settings:
    """
    获取配置实例（使用缓存）
    FastAPI推荐的配置获取方式
    """
    return Settings()


# 全局配置实例（向后兼容）
settings = get_settings()


# 导出配置获取函数（用于依赖注入）
def get_app_settings() -> Settings:
    """用于FastAPI依赖注入的配置获取函数"""
    return get_settings()
