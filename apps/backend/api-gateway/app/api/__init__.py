# API Routes Package - Three-layer Architecture

# 三层API路由
# Import routers lazily to avoid circular imports

__all__ = ["get_public_router", "get_app_router", "get_mcp_router"]


def get_public_router():
    from app.api.public.router import router

    return router


def get_app_router():
    from app.api.app.router import router

    return router


def get_mcp_router():
    from app.api.mcp.router import router

    return router
