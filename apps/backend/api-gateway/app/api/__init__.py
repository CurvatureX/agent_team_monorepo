# API Routes Package - Three-layer Architecture

# 三层API路由
from app.api.app.router import router as app_router
from app.api.mcp.router import router as mcp_router
from app.api.public.router import router as public_router

__all__ = ["public_router", "app_router", "mcp_router"]
