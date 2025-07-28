"""
API Gateway - Three-Layer Architecture with FastAPI Best Practices
三层API架构：Public API, App API, MCP API
"""

import time
from datetime import datetime, timezone

# 核心组件
from app.core.config import get_settings
from app.core.events import health_check, lifespan
from app.core.logging import setup_logging
from app.exceptions import register_exception_handlers

# 中间件
from app.middleware.auth import unified_auth_middleware
from app.middleware.rate_limit import rate_limit_middleware

# 工具
from app.utils.logger import get_logger
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .api.app.router import router as app_router
from .api.mcp.router import router as mcp_router

# API路由 - Use relative imports to avoid package discovery issues
from .api.public.router import router as public_router

# 在应用启动前设置日志
setup_logging()
logger = get_logger(__name__)

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
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
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

    # 注册中间件（顺序很重要）
    # 1. 限流中间件（最外层，先限流再认证）
    app.middleware("http")(rate_limit_middleware)

    # 2. 认证中间件
    app.middleware("http")(unified_auth_middleware)

    # 3. 请求日志中间件
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
    logger.info(
        f"📨 {request.method} {request.url.path}",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "client_ip": (
                request.headers.get("X-Forwarded-For")
                or request.headers.get("X-Real-IP")
                or str(request.client.host)
                if request.client
                else "unknown"
            ),
            "user_agent": request.headers.get("User-Agent"),
        },
    )

    # 处理请求
    response = await call_next(request)

    # 计算处理时间
    process_time = time.time() - start_time

    # 添加响应头
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time"] = str(round(process_time * 1000, 2))

    # 记录响应
    logger.info(
        f"📤 {request.method} {request.url.path} -> {response.status_code}",
        extra={
            "request_id": request_id,
            "status_code": response.status_code,
            "process_time_ms": round(process_time * 1000, 2),
        },
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
