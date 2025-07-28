"""
Public API endpoints - No authentication required
包括健康检查、系统信息等公开端点
"""

import time
from datetime import datetime, timezone

from app.core.config import Settings, get_settings
from app.core.events import health_check
from app.dependencies import CommonDeps
from app.models.base import HealthCheckModel
from app.utils.logger import get_logger
from fastapi import APIRouter, Depends, Request

logger = get_logger(__name__)
router = APIRouter()


@router.get("/health", response_model=HealthCheckModel)
async def health_check_endpoint(request: Request, settings: Settings = Depends(get_settings)):
    """Health check endpoint - 公开健康检查接口"""
    start_time = time.time()

    logger.info("🏥 Public health check requested")

    try:
        # 使用核心健康检查
        health_info = await health_check()

        # 添加请求信息
        health_info["timestamp"] = datetime.now(timezone.utc).isoformat()
        health_info["request_id"] = getattr(request.state, "request_id", None)
        health_info["processing_time_ms"] = round((time.time() - start_time) * 1000, 2)

        return health_info

    except Exception as e:
        logger.error(f"❌ Health check failed: {e}")
        return HealthCheckModel(
            service="API Gateway",
            version=settings.VERSION,
            status="unhealthy",
            timestamp=datetime.now(timezone.utc),
            message=f"Health check failed: {str(e)}",
        )


@router.get("/info")
async def system_info(request: Request, settings: Settings = Depends(get_settings)):
    """System information endpoint - 公开系统信息接口"""
    logger.info("🔍 Public system info requested")

    return {
        "service": settings.APP_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "architecture": "Three-layer API (Public/App/MCP)",
        "auth_model": "Layer-specific authentication strategies",
        "api_layers": {
            "public": {
                "prefix": "/api/public",
                "auth": "None (rate limited)",
                "enabled": settings.PUBLIC_API_ENABLED,
                "description": "Public endpoints for external systems",
            },
            "app": {
                "prefix": "/api/app",
                "auth": "Supabase OAuth + RLS",
                "enabled": settings.APP_API_ENABLED,
                "description": "App endpoints for Web/Mobile applications",
            },
            "mcp": {
                "prefix": "/api/mcp",
                "auth": "API Key with scopes",
                "enabled": settings.MCP_API_ENABLED,
                "description": "MCP endpoints for LLM clients",
            },
        },
        "features": {
            "rate_limiting": settings.PUBLIC_RATE_LIMIT_ENABLED,
            "authentication": {
                "supabase": settings.SUPABASE_AUTH_ENABLED,
                "mcp_api_key": settings.MCP_API_KEY_REQUIRED,
                "rls": settings.RLS_ENABLED,
            },
            "monitoring": settings.METRICS_ENABLED,
        },
        "documentation": {
            "openapi": "/docs" if settings.DEBUG else None,
            "redoc": "/redoc" if settings.DEBUG else None,
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "request_id": getattr(request.state, "request_id", None),
    }


@router.get("/status")
async def service_status(request: Request, deps: CommonDeps = Depends()):
    """Service status endpoint - 公开服务状态接口"""
    logger.info("🔍 Public service status requested")

    try:
        # 检查数据库连接状态
        db_health = await deps.db_manager.health_check()

        # 确定整体状态
        overall_status = "operational"
        if not db_health.get("overall"):
            overall_status = "degraded"

        return {
            "status": overall_status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "services": {
                "api_gateway": "operational",
                "database": {
                    "supabase": "connected" if db_health.get("supabase") else "disconnected",
                    "supabase_admin": "connected"
                    if db_health.get("supabase_admin")
                    else "disconnected",
                    "redis": "connected" if db_health.get("redis") else "unavailable",
                },
            },
            "api_layers": {
                "public_api": "operational" if deps.settings.PUBLIC_API_ENABLED else "disabled",
                "app_api": "operational" if deps.settings.APP_API_ENABLED else "disabled",
                "mcp_api": "operational" if deps.settings.MCP_API_ENABLED else "disabled",
            },
            "features": {
                "authentication": deps.settings.SUPABASE_AUTH_ENABLED,
                "rate_limiting": deps.settings.PUBLIC_RATE_LIMIT_ENABLED,
                "monitoring": deps.settings.METRICS_ENABLED,
            },
            "request_id": getattr(request.state, "request_id", None),
        }

    except Exception as e:
        logger.error(f"❌ Service status check failed: {e}")
        return {
            "status": "error",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "error": str(e),
            "request_id": getattr(request.state, "request_id", None),
        }
