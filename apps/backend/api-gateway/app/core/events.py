"""
Application Lifecycle Events
应用程序生命周期事件管理
"""

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from app.core.config import get_settings
from app.core.database import get_database_manager
from app.utils.logger import get_logger
from fastapi import FastAPI


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    FastAPI应用程序生命周期管理
    处理启动和关闭事件
    """
    # 启动事件
    await startup_event(app)

    try:
        yield
    finally:
        # 关闭事件
        await shutdown_event(app)


async def startup_event(app: FastAPI) -> None:
    """应用程序启动事件"""
    logger = get_logger(__name__)

    settings = get_settings()

    logger.info("🚀 Starting API Gateway...")
    logger.info(f"📊 Environment: {settings.ENVIRONMENT}")
    logger.info(f"🐛 Debug mode: {settings.DEBUG}")
    logger.info(f"🌐 Version: {settings.VERSION}")

    # 初始化数据库连接
    await initialize_database_connections()

    # 执行健康检查
    await perform_startup_health_checks()

    # 设置应用状态
    app.state.settings = settings
    app.state.db_manager = get_database_manager()

    logger.info("✅ API Gateway startup completed successfully")


async def shutdown_event(app: FastAPI) -> None:
    """应用程序关闭事件"""
    logger = get_logger(__name__)

    logger.info("🛑 Shutting down API Gateway...")

    # 关闭数据库连接
    await cleanup_database_connections(app)

    # 清理其他资源
    await cleanup_resources(app)

    logger.info("✅ API Gateway shutdown completed")


async def initialize_database_connections() -> None:
    """初始化数据库连接"""
    logger = get_logger(__name__)

    try:
        db_manager = get_database_manager()

        # Initialize the database manager first
        await db_manager.initialize()

        # 初始化各个数据库连接
        supabase_client = db_manager.supabase
        supabase_admin_client = db_manager.supabase_admin

        # Try to get Redis client to test connection
        redis_client = None
        try:
            redis_client = await db_manager.get_redis_client()
        except Exception as redis_e:
            logger.warning(f"⚠️ Redis connection failed: {redis_e}")

        # 记录连接状态
        connections_status = []
        if supabase_client:
            connections_status.append("✅ Supabase (user)")
        else:
            connections_status.append("❌ Supabase (user)")

        if supabase_admin_client:
            connections_status.append("✅ Supabase (admin)")
        else:
            connections_status.append("❌ Supabase (admin)")

        if redis_client:
            connections_status.append("✅ Redis")
        else:
            connections_status.append("❌ Redis")

        logger.info(f"🔗 Database connections: {', '.join(connections_status)}")

    except Exception as e:
        logger.warning(f"⚠️ Database connections initialization completed with warnings: {e}")
        # Don't raise - allow app to start with degraded functionality


async def perform_startup_health_checks() -> None:
    """执行启动时的健康检查"""
    logger = get_logger(__name__)
    settings = get_settings()

    try:
        # 数据库健康检查
        db_manager = get_database_manager()
        health_status = await db_manager.health_check()

        logger.info(f"🏥 Database health check: {health_status}")

        # 关键服务检查
        critical_services = []

        # 检查Supabase配置
        if settings.SUPABASE_URL and settings.SUPABASE_URL != "https://your-project-id.supabase.co":
            critical_services.append("✅ Supabase configured")
        else:
            critical_services.append("⚠️ Supabase not configured")

        # 检查Redis配置
        if health_status.get("redis"):
            critical_services.append("✅ Redis available")
        else:
            critical_services.append("⚠️ Redis not available")

        # 检查认证配置
        if settings.SUPABASE_AUTH_ENABLED and settings.SUPABASE_SECRET_KEY:
            critical_services.append("✅ Authentication configured")
        else:
            critical_services.append("⚠️ Authentication not fully configured")

        logger.info(f"🔍 Service checks: {', '.join(critical_services)}")

        # 警告检查
        warnings = []
        if settings.DEBUG and settings.is_production():
            warnings.append("🚨 DEBUG mode enabled in production environment")

        if not settings.SUPABASE_SECRET_KEY:
            warnings.append("🚨 Supabase secret key not configured")

        if warnings:
            for warning in warnings:
                logger.warning(warning)

    except Exception as e:
        logger.error(f"❌ Startup health check failed: {e}")
        # 不要阻止启动，只是记录警告
        logger.warning("⚠️ Continuing startup despite health check failures")


async def cleanup_database_connections(app: FastAPI) -> None:
    """清理数据库连接"""
    logger = get_logger(__name__)

    try:
        if hasattr(app.state, "db_manager"):
            await app.state.db_manager.close_connections()
            logger.info("✅ Database connections cleaned up")
    except Exception as e:
        logger.error(f"❌ Error cleaning up database connections: {e}")


async def cleanup_resources(app: FastAPI) -> None:
    """清理其他应用资源"""
    logger = get_logger(__name__)

    try:
        # 清理应用状态
        if hasattr(app.state, "settings"):
            delattr(app.state, "settings")
        if hasattr(app.state, "db_manager"):
            delattr(app.state, "db_manager")

        # 等待异步任务完成
        pending_tasks = [task for task in asyncio.all_tasks() if not task.done()]
        if pending_tasks:
            logger.info(f"⏳ Waiting for {len(pending_tasks)} pending tasks to complete...")
            await asyncio.gather(*pending_tasks, return_exceptions=True)

        logger.info("✅ Resources cleanup completed")

    except Exception as e:
        logger.error(f"❌ Error during resource cleanup: {e}")


# 用于手动触发的健康检查函数
async def health_check() -> dict:
    """执行完整的健康检查"""
    logger = get_logger(__name__)
    settings = get_settings()

    try:
        # 基础信息
        health_info = {
            "service": "API Gateway",
            "version": settings.VERSION,
            "environment": settings.ENVIRONMENT,
            "debug": settings.DEBUG,
            "timestamp": None,  # 会在路由中设置
            "status": "healthy",
        }

        # 数据库健康检查
        db_manager = get_database_manager()
        db_health = await db_manager.health_check()
        health_info["databases"] = db_health

        # API层状态
        health_info["api_layers"] = {
            "public": settings.PUBLIC_API_ENABLED,
            "app": settings.APP_API_ENABLED,
            "mcp": settings.MCP_API_ENABLED,
        }

        # 认证状态
        health_info["authentication"] = {
            "supabase_enabled": settings.SUPABASE_AUTH_ENABLED,
            "mcp_api_key_required": settings.MCP_API_KEY_REQUIRED,
            "rls_enabled": settings.RLS_ENABLED,
        }

        # 整体状态判断
        if not db_health.get("overall"):
            health_info["status"] = "degraded"
            health_info["message"] = "Database connections unavailable"

        return health_info

    except Exception as e:
        logger.error(f"❌ Health check failed: {e}")
        return {
            "service": "API Gateway",
            "version": settings.VERSION,
            "status": "unhealthy",
            "error": str(e),
            "timestamp": None,
        }
