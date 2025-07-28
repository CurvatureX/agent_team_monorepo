# API Routes Package - Three-layer Architecture

# 三层API路由
from app.api.app import router as app_router
from app.api.mcp import router as mcp_router
from app.api.public import router as public_router

__all__ = ["public_router", "app_router", "mcp_router"]
