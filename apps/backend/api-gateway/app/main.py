"""
API Gateway - Simplified with Frontend Auth
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.config import settings
from app.database import init_supabase
from app.models import HealthResponse

# 导入三层API路由
from app.api.public import router as public_router
from app.api.app import router as app_router
from app.api.mcp import router as mcp_router

# 导入中间件
from app.middleware.auth import unified_auth_middleware
from app.middleware.rate_limit import rate_limit_middleware

from app.services.grpc_client import workflow_client
from app.utils import log_info, log_warning, log_error, log_exception


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events - replaces deprecated on_event"""
    # Startup
    try:
        log_info("🚀 Starting API Gateway with Frontend Auth...")

        # Initialize Supabase connection
        init_supabase()
        log_info("✅ Supabase client initialized")

        # Initialize gRPC client connection
        await workflow_client.connect()
        log_info("✅ gRPC client connected")

        log_info("🚀 API Gateway started successfully!")
        log_info(f"📖 API Documentation: http://localhost:8000/docs")
        log_info(f"🏥 Health Check: http://localhost:8000/health")
        log_info(f"🔐 Auth: Frontend handles authentication, backend verifies JWT tokens")

    except Exception as e:
        log_exception(f"❌ Failed to start API Gateway: {e}")
        raise

    yield

    # Shutdown
    try:
        # Close gRPC connections
        await workflow_client.close()

        log_info("👋 API Gateway stopped")

    except Exception as e:
        log_exception(f"⚠️  Error during shutdown: {e}")


# FastAPI application with lifespan
app = FastAPI(
    title=settings.APP_NAME,
    description="Three-Layer API Architecture: Public/App/MCP",
    version=settings.VERSION,
    lifespan=lifespan,
)

# 中间件栈配置（顺序很重要）
# 1. CORS 中间件（最外层）
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. 限流中间件
app.middleware("http")(rate_limit_middleware)

# 3. 认证中间件
app.middleware("http")(unified_auth_middleware)

# 三层API路由注册
app.include_router(public_router, prefix="/api/public", tags=["public"])
app.include_router(app_router, prefix="/api/app", tags=["app"])
app.include_router(mcp_router, prefix="/api/mcp", tags=["mcp"])


# 兼容性重定向 - 保持旧的健康检查端点可用
@app.get("/health", response_model=HealthResponse)
async def legacy_health_check():
    """Legacy health check endpoint - redirects to /api/public/health"""
    log_info("Legacy health check requested")
    return HealthResponse(status="healthy", version="2.0.0")


@app.get("/")
async def root():
    """Root endpoint"""
    log_info("Root endpoint accessed")
    return {
        "message": "Workflow Agent API Gateway - Three-Layer Architecture",
        "version": "1.0.0",
        "architecture": "Three-layer API (Public/App/MCP)",
        "api_layers": {
            "public": {
                "prefix": "/api/public",
                "auth": "None (Rate Limited)",
                "description": "Public endpoints for external systems",
            },
            "app": {
                "prefix": "/api/app",
                "auth": "Supabase OAuth + RLS",
                "description": "App endpoints for Web/Mobile applications",
            },
            "mcp": {
                "prefix": "/api/mcp",
                "auth": "API Key with scopes",
                "description": "MCP endpoints for LLM clients",
            },
        },
        "endpoints": {
            "docs": "/docs",
            "health": "/api/public/health",
            "sessions": "/api/app/sessions",
            "chat": "/api/app/chat/stream",
            "workflows": "/api/app/workflows",
            "mcp_tools": "/api/mcp/tools",
            "mcp_invoke": "/api/mcp/invoke",
        },
    }


# 旧的认证中间件已被新的统一认证中间件替代


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc):
    """Global exception handler with enhanced logging"""
    path = request.url.path
    method = request.method

    log_exception(f"💥 {method} {path} - Unhandled exception: {type(exc).__name__}: {str(exc)}")

    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_server_error",
            "message": "Internal server error occurred",
            "path": path,
        },
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, log_level="info")
