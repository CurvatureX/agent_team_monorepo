"""
API Gateway - Three-Layer Architecture with FastAPI Best Practices
三层API架构：Public API, App API, MCP API
"""

import os
import sys
import time
from datetime import datetime, timezone

# Add shared node_specs to Python path for node knowledge access
current_dir = os.path.dirname(os.path.abspath(__file__))
# Try multiple paths to find shared module
possible_paths = [
    os.path.join(current_dir, "../../../shared"),  # Original path
    os.path.join(current_dir, "../../shared"),      # From app directory
    os.path.abspath(os.path.join(current_dir, "..", "..", "shared")),  # Absolute path
]

shared_path = None
for path in possible_paths:
    if os.path.exists(path) and os.path.isdir(path):
        shared_path = path
        break

if shared_path and shared_path not in sys.path:
    sys.path.insert(0, shared_path)

# 工具 - Use custom logging
import logging

# 遥测组件
try:
    from shared.telemetry import setup_telemetry, TrackingMiddleware, MetricsMiddleware
except ImportError:
    # Fallback for tests - create dummy implementations
    print("Warning: Could not import telemetry components, using stubs")
    def setup_telemetry(*args, **kwargs):
        pass
    class TrackingMiddleware:
        def __init__(self, app):
            self.app = app
        async def __call__(self, scope, receive, send):
            await self.app(scope, receive, send)
    class MetricsMiddleware:
        def __init__(self, app):
            self.app = app
        async def __call__(self, scope, receive, send):
            await self.app(scope, receive, send)

from app.api.app.router import router as app_router
from app.api.mcp.router import router as mcp_router

# API路由 - Direct absolute imports to bypass package discovery issues
from app.api.public.router import router as public_router

# 核心组件
from app.core.config import get_settings
from app.core.events import health_check, lifespan
from app.exceptions import register_exception_handlers

# 中间件
from app.middleware.auth import unified_auth_middleware
from app.middleware.rate_limit import rate_limit_middleware
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

logger = logging.getLogger("app.main")

# 获取配置
settings = get_settings()


def create_application() -> FastAPI:
    """
    创建FastAPI应用实例
    使用工厂模式，遵循FastAPI最佳实践
    """

    # 创建应用实例
    app = FastAPI(
        title=settings.APP_NAME,
        description="""
        三层API架构的工作流代理网关

        ## API层级

        - **Public API** (`/api/v1/public/*`) - 无需认证的公开接口
        - **App API** (`/api/v1/app/*`) - 需要Supabase OAuth认证的应用接口
        - **MCP API** (`/api/v1/mcp/*`) - 需要API Key认证的LLM客户端接口

        ## 认证方式

        - **App API**: 使用 `Authorization: Bearer <supabase_jwt_token>`
        - **MCP API**: 使用 `X-API-Key: <api_key>` 或 `Authorization: Bearer <api_key>`
        """,
        version=settings.VERSION,
        lifespan=lifespan,
        debug=settings.DEBUG,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # 配置CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=[
            "X-Request-ID",
            "X-RateLimit-Limit",
            "X-RateLimit-Remaining",
            "X-RateLimit-Reset",
        ],
    )

    # 初始化遥测系统
    setup_telemetry(app, service_name="api-gateway", service_version=settings.VERSION)

    # 注册中间件（顺序很重要）
    # 1. 追踪中间件（最外层，为每个请求生成 tracking_id）
    app.add_middleware(TrackingMiddleware)

    # 2. 指标收集中间件
    app.add_middleware(MetricsMiddleware, service_name="api-gateway")

    # 3. 限流中间件
    app.middleware("http")(rate_limit_middleware)

    # 4. 认证中间件
    app.middleware("http")(unified_auth_middleware)

    # 5. 请求日志中间件（添加 X-Process-Time 头）
    app.middleware("http")(request_logging_middleware)

    # 注册异常处理器
    register_exception_handlers(app)

    # 注册API路由
    register_routes(app)

    # 注册通用路由
    register_common_routes(app)

    return app


async def request_logging_middleware(request: Request, call_next):
    """请求日志中间件"""
    start_time = time.time()

    # 生成请求ID
    request_id = f"{int(time.time() * 1000)}-{hash(str(request.url)) % 10000:04d}"
    request.state.request_id = request_id

    # 记录请求开始
    client_ip = (
        request.headers.get("X-Forwarded-For")
        or request.headers.get("X-Real-IP")
        or str(request.client.host)
        if request.client
        else "unknown"
    )
    logger.info(f"📨 {request.method} {request.url.path} [ID:{request_id}] [IP:{client_ip}]")

    # 处理请求
    response = await call_next(request)

    # 计算处理时间
    process_time = time.time() - start_time

    # 添加响应头
    # X-Tracking-ID is already set by TrackingMiddleware
    response.headers["X-Process-Time"] = str(round(process_time * 1000, 2))

    # 记录响应
    logger.info(
        f"📤 {request.method} {request.url.path} -> {response.status_code} [{round(process_time * 1000, 2)}ms]"
    )

    return response


def register_routes(app: FastAPI) -> None:
    """注册API路由"""

    # 注册三层API路由 (with v1 versioning)
    app.include_router(
        public_router,
        prefix="/api/v1/public",
        tags=["Public API"],
        responses={
            429: {"description": "Rate limit exceeded"},
            500: {"description": "Internal server error"},
        },
    )

    app.include_router(
        app_router,
        prefix="/api/v1/app",
        tags=["App API"],
        responses={
            401: {"description": "Authentication required"},
            403: {"description": "Insufficient permissions"},
            429: {"description": "Rate limit exceeded"},
            500: {"description": "Internal server error"},
        },
    )

    app.include_router(
        mcp_router,
        prefix="/api/v1/mcp",
        tags=["MCP API"],
        responses={
            401: {"description": "API key required"},
            403: {"description": "Insufficient API key permissions"},
            429: {"description": "Rate limit exceeded"},
            500: {"description": "Internal server error"},
        },
    )

    logger.info("✅ API routes registered")


def register_common_routes(app: FastAPI) -> None:
    """注册通用路由"""

    @app.get("/", include_in_schema=False)
    async def root():
        """根路径，重定向到文档"""
        return {
            "service": settings.APP_NAME,
            "version": settings.VERSION,
            "environment": settings.ENVIRONMENT,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "documentation": "/docs",
            "health_check": "/health",
            "api_layers": {
                "public": "/api/v1/public/",
                "app": "/api/v1/app/",
                "mcp": "/api/v1/mcp/",
            },
        }

    @app.get("/health", include_in_schema=False)
    async def health_endpoint(request: Request):
        """健康检查端点"""
        health_info = await health_check()
        health_info["timestamp"] = datetime.now(timezone.utc).isoformat()
        health_info["request_id"] = getattr(request.state, "request_id", None)

        status_code = 200 if health_info.get("status") == "healthy" else 503
        return JSONResponse(status_code=status_code, content=health_info)

    @app.get("/version", include_in_schema=False)
    async def version_endpoint():
        """版本信息端点"""
        return {
            "service": settings.APP_NAME,
            "version": settings.VERSION,
            "environment": settings.ENVIRONMENT,
            "debug": settings.DEBUG,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    logger.info("✅ Common routes registered")


# 创建应用实例
app = create_application()


if __name__ == "__main__":
    import uvicorn

    logger.info(f"🚀 Starting {settings.APP_NAME} v{settings.VERSION}")
    logger.info(f"🌍 Environment: {settings.ENVIRONMENT}")
    logger.info(f"🐛 Debug mode: {settings.DEBUG}")

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.RELOAD and settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
        access_log=False,  # 我们使用自己的请求日志中间件
        server_header=False,
        date_header=False,
    )
