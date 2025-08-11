"""
Main gRPC server application.
"""

import os
import sys
import time
from pathlib import Path
from typing import Optional

import grpc
import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

# Add backend directory to Python path for shared models
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

# Import shared logging
from shared.logging_config import setup_logging

# 遥测组件
try:
    from shared.telemetry import (  # type: ignore[assignment]
        MetricsMiddleware,
        TrackingMiddleware,
        setup_telemetry,
    )
except ImportError:
    # Fallback for deployment - create dummy implementations
    print("Warning: Could not import telemetry components, using stubs")

    def setup_telemetry(*args, **kwargs):  # type: ignore[misc]
        pass

    class TrackingMiddleware:  # type: ignore[misc]
        def __init__(self, app):
            self.app = app

        async def __call__(self, scope, receive, send):
            await self.app(scope, receive, send)

    class MetricsMiddleware:  # type: ignore[misc]
        def __init__(self, app, **kwargs):
            self.app = app

        async def __call__(self, scope, receive, send):
            await self.app(scope, receive, send)


from shared.models.common import HealthResponse, HealthStatus
from workflow_engine.api.v1 import credentials, executions, triggers, workflows
from workflow_engine.core.config import get_settings
from workflow_engine.models.database import close_db

# Setup unified logging
logger = setup_logging(
    service_name="workflow-engine",
    log_level=os.getenv("LOG_LEVEL", "INFO")
)


settings = get_settings()

app = FastAPI(
    title="Workflow Engine API",
    description="Service for managing and executing workflows.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# 初始化遥测系统
# 检查是否禁用OpenTelemetry
otel_disabled = os.getenv("OTEL_SDK_DISABLED", "false").lower() == "true"
environment = os.getenv("ENVIRONMENT", "development")

if not otel_disabled:
    # AWS生产环境使用localhost:4317 (AWS OTEL Collector sidecar)
    # 开发环境使用otel-collector:4317 (Docker Compose service)
    if environment in ["production", "staging"]:
        otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")
    else:
        otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://otel-collector:4317")

    setup_telemetry(
        app, service_name="workflow-engine", service_version="1.0.0", otlp_endpoint=otlp_endpoint
    )

    # 添加遥测中间件
    app.add_middleware(TrackingMiddleware)  # type: ignore
    app.add_middleware(MetricsMiddleware, service_name="workflow-engine")  # type: ignore

    logger.info(
        f"OpenTelemetry configured for workflow-engine in {environment} environment with endpoint: {otlp_endpoint}"
    )
else:
    logger.info(
        "OpenTelemetry disabled for workflow-engine via OTEL_SDK_DISABLED environment variable"
    )


@app.on_event("startup")
def on_startup():
    logger.info("Workflow Engine service starting up")


# Tracking ID middleware
@app.middleware("http")
async def tracking_id_middleware(request: Request, call_next):
    """Extract and propagate tracking_id from request headers"""
    tracking_id = request.headers.get("x-tracking-id") or request.headers.get("X-Tracking-ID")

    if tracking_id:
        # Store tracking_id in request state for access in endpoints
        request.state.tracking_id = tracking_id

        # Configure logging to include tracking_id
        import contextvars

        tracking_id_context = contextvars.ContextVar("tracking_id", default=None)
        tracking_id_context.set(tracking_id)

        logger.info(f"Request received with tracking_id: {tracking_id}")

    response = await call_next(request)

    # Optionally add tracking_id to response headers
    if tracking_id:
        response.headers["X-Tracking-ID"] = tracking_id

    return response


@app.on_event("shutdown")
def on_shutdown():
    close_db()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(workflows.router, prefix="/v1", tags=["Workflows"])
app.include_router(executions.router, prefix="/v1", tags=["Executions"])
app.include_router(triggers.router, prefix="/v1", tags=["Triggers"])
app.include_router(credentials.router, prefix="/api/v1", tags=["Credentials"])


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check that validates database connection."""
    details = {"service": "workflow-engine", "database": "unknown"}

    overall_status = HealthStatus.HEALTHY

    # Check database connection
    try:
        from sqlalchemy import text

        from workflow_engine.models.database import engine

        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        details["database"] = "connected"
        logger.info("Database health check passed")
    except Exception as e:
        details["database"] = f"failed: {str(e)}"
        overall_status = HealthStatus.UNHEALTHY
        logger.error(f"Database health check failed: {e}")

    return HealthResponse(
        status=overall_status, version="1.0.0", timestamp=int(time.time()), details=details
    )


@app.get("/")
async def root():
    return {"message": "Workflow Engine API is running", "version": "1.0.0"}


if __name__ == "__main__":
    uvicorn.run("main:app", host=settings.HOST, port=settings.PORT, reload=True)
