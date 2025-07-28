"""
System Status API endpoints.

Provides comprehensive system status information including:
- Feature flags and system information
- Service version and environment details
- API layer availability status
- Dependency health checks
"""

import os
import sys
from datetime import datetime
from typing import Any, Dict

from app.core.config import settings
from app.core.database import get_database_manager
from app.models.base import ResponseModel
from app.services.enhanced_grpc_client import WorkflowGRPCClientManager
from fastapi import APIRouter, Depends

router = APIRouter()


class SystemStatusResponse(ResponseModel):
    """System status response model."""

    status: str
    timestamp: str
    version: str
    environment: str
    system_info: Dict[str, Any]
    services: Dict[str, Any]
    feature_flags: Dict[str, bool]
    api_layers: Dict[str, Dict[str, Any]]


@router.get("/status", response_model=SystemStatusResponse)
async def get_system_status():
    """
    Get comprehensive system status information.

    Returns:
        SystemStatusResponse: Complete system status including health checks
    """

    # Get database manager for health checks
    db_manager = await get_database_manager()

    # Perform health checks
    db_health = await db_manager.health_check()

    # Check gRPC client health
    grpc_health = {"healthy": False, "error": "Not implemented"}
    try:
        from app.services.enhanced_grpc_client import get_workflow_client

        grpc_client = await get_workflow_client()
        grpc_health = await grpc_client.health_check()
    except Exception as e:
        grpc_health = {"healthy": False, "error": str(e)}

    # Determine overall system health
    overall_healthy = db_health.get("overall", False) and grpc_health.get("healthy", False)

    # System information
    system_info = {
        "python_version": sys.version,
        "platform": sys.platform,
        "hostname": os.getenv("HOSTNAME", "unknown"),
        "pid": os.getpid(),
        "uptime_info": "Not implemented",
        "memory_usage": "Not implemented",
    }

    # Service health status
    services = {
        "database": {
            "status": "healthy" if db_health.get("overall") else "unhealthy",
            "details": db_health,
        },
        "grpc_client": {
            "status": "healthy" if grpc_health.get("healthy") else "unhealthy",
            "details": grpc_health,
        },
        "redis": {
            "status": "healthy" if db_health.get("redis") else "unhealthy",
            "connection": db_health.get("details", {}).get("redis", "unknown"),
        },
        "supabase": {
            "status": "healthy" if db_health.get("supabase_auth") else "unhealthy",
            "connection": db_health.get("details", {}).get("supabase_auth", "unknown"),
        },
    }

    # Feature flags
    feature_flags = {
        "public_api_enabled": settings.PUBLIC_API_ENABLED,
        "app_api_enabled": settings.APP_API_ENABLED,
        "mcp_api_enabled": settings.MCP_API_ENABLED,
        "rate_limiting_enabled": settings.PUBLIC_RATE_LIMIT_ENABLED,
        "auth_enabled": settings.ENABLE_AUTH,
        "supabase_auth_enabled": settings.SUPABASE_AUTH_ENABLED,
        "rls_enabled": settings.RLS_ENABLED,
        "debug_mode": settings.DEBUG,
        "metrics_enabled": settings.METRICS_ENABLED,
        "health_check_enabled": settings.HEALTH_CHECK_ENABLED,
    }

    # API layer status
    api_layers = {
        "public": {
            "enabled": settings.PUBLIC_API_ENABLED,
            "prefix": "/api/v1/public",
            "authentication": "none",
            "rate_limiting": settings.PUBLIC_RATE_LIMIT_ENABLED,
            "endpoints": ["/api/v1/public/health", "/api/v1/public/status", "/api/v1/public/docs"],
        },
        "app": {
            "enabled": settings.APP_API_ENABLED,
            "prefix": "/api/v1",
            "authentication": "supabase_jwt",
            "rate_limiting": True,
            "endpoints": [
                "/api/v1/sessions",
                "/api/v1/workflows",
                "/api/v1/executions",
                "/api/v1/auth/profile",
            ],
        },
        "mcp": {
            "enabled": settings.MCP_API_ENABLED,
            "prefix": "/api/v1/mcp",
            "authentication": "api_key",
            "rate_limiting": True,
            "endpoints": ["/api/v1/mcp/tools", "/api/v1/mcp/invoke", "/api/v1/mcp/health"],
        },
    }

    return SystemStatusResponse(
        status="healthy" if overall_healthy else "degraded",
        timestamp=datetime.utcnow().isoformat(),
        version=settings.VERSION,
        environment=settings.ENVIRONMENT,
        system_info=system_info,
        services=services,
        feature_flags=feature_flags,
        api_layers=api_layers,
    )


@router.get("/version")
async def get_version():
    """
    Get simple version information.

    Returns:
        Dict: Version and basic system info
    """
    return {
        "version": settings.VERSION,
        "api_version": settings.API_VERSION,
        "environment": settings.ENVIRONMENT,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/feature-flags")
async def get_feature_flags():
    """
    Get current feature flag configuration.

    Returns:
        Dict: All feature flags and their current states
    """
    return {
        "public_api_enabled": settings.PUBLIC_API_ENABLED,
        "app_api_enabled": settings.APP_API_ENABLED,
        "mcp_api_enabled": settings.MCP_API_ENABLED,
        "rate_limiting_enabled": settings.PUBLIC_RATE_LIMIT_ENABLED,
        "auth_enabled": settings.ENABLE_AUTH,
        "supabase_auth_enabled": settings.SUPABASE_AUTH_ENABLED,
        "rls_enabled": settings.RLS_ENABLED,
        "debug_mode": settings.DEBUG,
        "metrics_enabled": settings.METRICS_ENABLED,
        "health_check_enabled": settings.HEALTH_CHECK_ENABLED,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/services")
async def get_services_status():
    """
    Get detailed service health status.

    Returns:
        Dict: Health status of all system dependencies
    """
    # Get database manager for health checks
    db_manager = await get_database_manager()
    db_health = await db_manager.health_check()

    # Check gRPC client health
    grpc_health = {"healthy": False, "error": "Not implemented"}
    try:
        from app.services.enhanced_grpc_client import get_workflow_client

        grpc_client = await get_workflow_client()
        grpc_health = await grpc_client.health_check()
    except Exception as e:
        grpc_health = {"healthy": False, "error": str(e)}

    return {
        "database": {
            "overall": db_health.get("overall", False),
            "redis": db_health.get("redis", False),
            "supabase_auth": db_health.get("supabase_auth", False),
            "details": db_health.get("details", {}),
        },
        "grpc_workflow_service": grpc_health,
        "timestamp": datetime.utcnow().isoformat(),
    }
