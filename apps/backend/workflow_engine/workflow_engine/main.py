"""
Main gRPC server application.
"""

import logging
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

# 遥测组件
try:
    from shared.telemetry import setup_telemetry, TrackingMiddleware, MetricsMiddleware  # type: ignore[assignment]
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
from workflow_engine.api.v1 import executions, triggers, workflows
from workflow_engine.core.config import get_settings
from workflow_engine.models.database import close_db

logger = logging.getLogger(__name__)


settings = get_settings()

app = FastAPI(
    title="Workflow Engine API",
    description="Service for managing and executing workflows.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# 初始化遥测系统
# 从环境变量获取 OTLP 端点，默认使用 otel-collector
otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://otel-collector:4317")
setup_telemetry(app, service_name="workflow-engine", service_version="1.0.0", otlp_endpoint=otlp_endpoint)

# 添加遥测中间件
app.add_middleware(TrackingMiddleware)  # type: ignore
app.add_middleware(MetricsMiddleware, service_name="workflow-engine")  # type: ignore

@app.on_event("startup")
def on_startup():
    logger.info("Workflow Engine service starting up")
    

# Trace ID middleware
@app.middleware("http")
async def trace_id_middleware(request: Request, call_next):
    """Extract and propagate trace_id from request headers"""
    trace_id = request.headers.get("x-trace-id") or request.headers.get("X-Trace-ID")
    
    if trace_id:
        # Store trace_id in request state for access in endpoints
        request.state.trace_id = trace_id
        
        # Configure logging to include trace_id
        import contextvars
        trace_id_context = contextvars.ContextVar('trace_id', default=None)
        trace_id_context.set(trace_id)
        
        logger.info(f"Request received with trace_id: {trace_id}")
    
    response = await call_next(request)
    
    # Optionally add trace_id to response headers
    if trace_id:
        response.headers["X-Trace-ID"] = trace_id
    
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
