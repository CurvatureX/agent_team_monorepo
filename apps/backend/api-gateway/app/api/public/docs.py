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
