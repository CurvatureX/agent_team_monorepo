"""
Core Components for API Gateway
核心组件模块导出
"""

from .config import (
    APILayerSettings,
    AppSettings,
    AuthSettings,
    DatabaseSettings,
    SecuritySettings,
    ServiceSettings,
    Settings,
    get_app_settings,
    get_settings,
)
from .database import (
    DatabaseManager,
    create_user_supabase_client,
    get_database_manager,
    get_database_manager_dependency,
    get_redis,
    get_redis_dependency,
    get_supabase,
    get_supabase_admin,
    get_supabase_dependency,
)
from .events import health_check, lifespan, shutdown_event, startup_event

__all__ = [
    # Configuration
    "Settings",
    "get_settings",
    "get_app_settings",
    "DatabaseSettings",
    "AuthSettings",
    "APILayerSettings",
    "ServiceSettings",
    "SecuritySettings",
    "AppSettings",
    # Database
    "DatabaseManager",
    "get_database_manager",
    "get_supabase",
    "get_supabase_admin",
    "get_redis",
    "create_user_supabase_client",
    "get_database_manager_dependency",
    "get_supabase_dependency",
    "get_redis_dependency",
    # Events
    "lifespan",
    "startup_event",
    "shutdown_event",
    "health_check",
]
