"""
Documentation Redirect API endpoints.

Provides API documentation redirection and discovery endpoints.
"""

from typing import Any, Dict

from app.core.config import settings
from fastapi import APIRouter, Response
from fastapi.responses import JSONResponse, RedirectResponse

router = APIRouter()


@router.get("/docs")
async def redirect_to_docs():
    """
    Redirect to API documentation.

    Returns:
        RedirectResponse: Redirect to the main API docs (accessible without auth)
    """
    # Note: /docs is in the public_paths list in auth middleware, so it's accessible
    return RedirectResponse(url="/docs", status_code=302)


@router.get("/redoc")
async def redirect_to_redoc():
    """
    Redirect to ReDoc documentation.

    Returns:
        RedirectResponse: Redirect to the ReDoc interface
    """
    return RedirectResponse(url="/redoc", status_code=302)


@router.get("/openapi")
async def get_openapi_info():
    """
    Get OpenAPI specification information.

    Returns:
        Dict: Information about the OpenAPI specification
    """
    return {
        "openapi_url": "/openapi.json",
        "docs_url": "/docs",
        "redoc_url": "/redoc",
        "title": settings.API_TITLE,
        "version": settings.VERSION,
        "description": "API Gateway for Workflow Agent Team",
        "api_layers": {
            "public": {
                "prefix": "/api/v1/public",
                "description": "Public API endpoints - no authentication required",
            },
            "app": {
                "prefix": "/api/v1",
                "description": "Application API endpoints - Supabase JWT authentication required",
            },
            "mcp": {
                "prefix": "/api/v1/mcp",
                "description": "MCP API endpoints - API key authentication required",
            },
        },
    }


@router.get("/api-info")
async def get_api_info():
    """
    Get comprehensive API information and endpoint discovery.

    Returns:
        Dict: Detailed API information including all available endpoints
    """
    return {
        "title": settings.API_TITLE,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "base_url": f"http://localhost:{settings.PORT}"
        if settings.DEBUG
        else "https://api.example.com",
        "documentation": {
            "swagger_ui": "/docs",
            "redoc": "/redoc",
            "openapi_spec": "/openapi.json",
            "public_docs": "/api/v1/public/docs",
            "access_note": "Documentation endpoints (/docs, /redoc) are publicly accessible without authentication",
        },
        "authentication": {
            "public_api": {
                "type": "none",
                "description": "No authentication required for public endpoints",
            },
            "app_api": {
                "type": "bearer_jwt",
                "description": "Supabase JWT token required in Authorization header",
                "header": "Authorization: Bearer <jwt_token>",
            },
            "mcp_api": {
                "type": "api_key",
                "description": "API key required in X-API-Key header or Authorization header",
                "headers": ["X-API-Key: <api_key>", "Authorization: Bearer <api_key>"],
            },
        },
        "api_layers": {
            "public": {
                "prefix": "/api/v1/public",
                "enabled": settings.PUBLIC_API_ENABLED,
                "endpoints": [
                    {
                        "path": "/api/v1/public/health",
                        "method": "GET",
                        "description": "Health check endpoint",
                    },
                    {
                        "path": "/api/v1/public/status",
                        "method": "GET",
                        "description": "System status and information",
                    },
                    {
                        "path": "/api/v1/public/docs",
                        "method": "GET",
                        "description": "API documentation redirect",
                    },
                ],
            },
            "app": {
                "prefix": "/api/v1",
                "enabled": settings.APP_API_ENABLED,
                "authentication_required": True,
                "endpoints": [
                    {
                        "path": "/api/v1/sessions",
                        "methods": ["GET", "POST"],
                        "description": "Session management",
                    },
                    {
                        "path": "/api/v1/sessions/{session_id}",
                        "methods": ["GET", "PUT", "DELETE"],
                        "description": "Individual session operations",
                    },
                    {
                        "path": "/api/v1/workflows",
                        "methods": ["GET", "POST"],
                        "description": "Workflow management",
                    },
                    {
                        "path": "/api/v1/workflows/{workflow_id}",
                        "methods": ["GET", "PUT", "DELETE"],
                        "description": "Individual workflow operations",
                    },
                    {
                        "path": "/api/v1/workflows/{workflow_id}/execute",
                        "methods": ["POST"],
                        "description": "Execute workflow",
                    },
                    {
                        "path": "/api/v1/executions/{execution_id}",
                        "methods": ["GET"],
                        "description": "Get execution status",
                    },
                    {
                        "path": "/api/v1/auth/profile",
                        "methods": ["GET"],
                        "description": "User profile information",
                    },
                ],
            },
            "mcp": {
                "prefix": "/api/v1/mcp",
                "enabled": settings.MCP_API_ENABLED,
                "authentication_required": True,
                "endpoints": [
                    {
                        "path": "/api/v1/mcp/tools",
                        "methods": ["GET"],
                        "description": "List available MCP tools",
                    },
                    {
                        "path": "/api/v1/mcp/invoke",
                        "methods": ["POST"],
                        "description": "Invoke MCP tool",
                    },
                    {
                        "path": "/api/v1/mcp/health",
                        "methods": ["GET"],
                        "description": "MCP service health check",
                    },
                ],
            },
        },
        "rate_limiting": {
            "enabled": settings.PUBLIC_RATE_LIMIT_ENABLED,
            "public_api": "Rate limited per IP address",
            "authenticated_apis": "Rate limited per user/API key",
        },
        "support": {
            "contact": "team@example.com",
            "documentation": "/docs",
            "status_page": "/api/v1/public/status",
        },
    }


@router.get("/endpoints")
async def list_endpoints():
    """
    List all available API endpoints by layer.

    Returns:
        Dict: Organized list of all endpoints
    """
    endpoints = {
        "public_endpoints": [
            "GET /api/v1/public/health",
            "GET /api/v1/public/status",
            "GET /api/v1/public/version",
            "GET /api/v1/public/feature-flags",
            "GET /api/v1/public/services",
            "GET /api/v1/public/docs",
            "GET /api/v1/public/api-info",
            "GET /api/v1/public/endpoints",
        ],
        "app_endpoints": [
            "GET /api/v1/sessions",
            "POST /api/v1/sessions",
            "GET /api/v1/sessions/{session_id}",
            "PUT /api/v1/sessions/{session_id}",
            "DELETE /api/v1/sessions/{session_id}",
            "GET /api/v1/workflows",
            "POST /api/v1/workflows",
            "GET /api/v1/workflows/{workflow_id}",
            "PUT /api/v1/workflows/{workflow_id}",
            "DELETE /api/v1/workflows/{workflow_id}",
            "POST /api/v1/workflows/{workflow_id}/execute",
            "GET /api/v1/workflows/{workflow_id}/execution_history",
            "GET /api/v1/executions/{execution_id}",
            "POST /api/v1/executions/{execution_id}/cancel",
            "GET /api/v1/auth/profile",
            "GET /api/v1/auth/sessions",
        ],
        "mcp_endpoints": [
            "GET /api/v1/mcp/tools",
            "POST /api/v1/mcp/invoke",
            "GET /api/v1/mcp/health",
            "GET /api/v1/mcp/tools/{tool_name}",
        ],
        "total_endpoints": 26,
        "last_updated": "2025-01-28",
    }

    return endpoints
