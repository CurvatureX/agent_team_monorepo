"""
Application configuration.
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import field_validator


class Settings(BaseSettings):
    """Application settings."""
    
    # Database Configuration
    # 可以直接使用完整的数据库URL，或者分别配置各个参数
    database_url: Optional[str] = None
    
    # 分别配置数据库参数（当database_url为空时使用）
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "workflow_engine"
    db_user: str = "postgres"
    db_password: str = "password"
    db_schema: str = "public"
    
    # Supabase 特定配置
    supabase_url: Optional[str] = None
    supabase_key: Optional[str] = None
    supabase_service_key: Optional[str] = None
    
    # 数据库连接配置
    database_echo: bool = False
    database_pool_size: int = 10
    database_max_overflow: int = 20
    database_pool_timeout: int = 30
    database_pool_recycle: int = 3600
    
    # SSL配置（Supabase需要）
    database_ssl_mode: str = "prefer"  # disable, allow, prefer, require, verify-ca, verify-full
    
    # gRPC Server
    grpc_host: str = "0.0.0.0"
    grpc_port: int = 8000
    # Logging
    log_level: str = "INFO"
    
    # Security
    secret_key: str = "your-secret-key-here"
    
    # AI Configuration
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    
    @field_validator('database_url', mode='before')
    @classmethod
    def build_database_url(cls, v, info):
        """构建数据库URL，优先使用database_url，否则从分别的参数构建"""
        if v:
            return v
        
        # 获取其他字段的值
        data = info.data if hasattr(info, 'data') else {}
        
        # 如果设置了supabase_url，从中提取数据库连接信息
        if data.get('supabase_url'):
            supabase_url = data['supabase_url']
            # Supabase URL格式: https://xxx.supabase.co
            # 数据库连接格式: postgresql://postgres:[password]@db.xxx.supabase.co:5432/postgres
            if supabase_url.startswith('https://'):
                project_ref = supabase_url.replace('https://', '').replace('.supabase.co', '')
                db_host = f"db.{project_ref}.supabase.co"
                db_user = "postgres"
                db_password = data.get('db_password', '')
                db_name = "postgres"
                return f"postgresql://{db_user}:{db_password}@{db_host}:5432/{db_name}?sslmode=require"
        
        # 从分别的参数构建
        db_host = data.get('db_host', 'localhost')
        db_port = data.get('db_port', 5432)
        db_name = data.get('db_name', 'workflow_engine')
        db_user = data.get('db_user', 'postgres')
        db_password = data.get('db_password', 'password')
        ssl_mode = data.get('database_ssl_mode', 'prefer')
        
        url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        if ssl_mode != "disable":
            url += f"?sslmode={ssl_mode}"
        
        return url
    
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