"""
Core Components for API Gateway
核心组件模块导出
"""

from .config import (
    Settings,
    get_settings,
    get_app_settings,
    DatabaseSettings,
    AuthSettings,
    APILayerSettings,
    ServiceSettings,
    SecuritySettings,
    AppSettings,
)

from .database import (
    DatabaseManager,
    get_database_manager,
    get_supabase,
    get_supabase_admin,
    get_redis,
    create_user_supabase_client,
    get_database_manager_dependency,
    get_supabase_dependency,
    get_redis_dependency,
)


from .events import lifespan, startup_event, shutdown_event, health_check

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
