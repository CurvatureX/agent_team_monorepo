# API Routes Package - Three-layer Architecture

# 三层API路由
from .public import router as public_router
from .app import router as app_router
from .mcp import router as mcp_router

__all__ = ["public_router", "app_router", "mcp_router"]
