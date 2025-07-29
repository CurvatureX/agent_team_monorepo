"""
FastAPI main application for Workflow Engine.
Replaces the gRPC server with HTTP/REST API endpoints.
"""

import logging
import sys
import time
from contextlib import asynccontextmanager
from typing import Any, Dict

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from workflow_engine.workflow_engine.api.v1 import triggers_router, workflows_router
from workflow_engine.workflow_engine.core.config import get_settings
from workflow_engine.workflow_engine.models.database import init_db, test_db_connection
from workflow_engine.workflow_engine.models.responses import (
    ErrorResponse,
    HealthCheckResponse,
    HealthStatus,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info("🚀 Starting Workflow Engine FastAPI Server")
    logger.info("=" * 50)

    # Initialize database
    logger.info("Initializing database...")
    if not test_db_connection():
        logger.error("❌ Database connection failed")
        raise Exception("Database connection failed")

    logger.info("✅ Database connection successful")

    try:
        init_db()
        logger.info("✅ Database tables initialized")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        raise

    logger.info(f"🌐 Server starting on port {getattr(settings, 'PORT', 8000)}")
    logger.info("✅ Workflow Engine FastAPI server started successfully")

    yield

    # Shutdown
    logger.info("🛑 Shutting down Workflow Engine FastAPI server...")
    logger.info("✅ Workflow Engine FastAPI server stopped")


# Create FastAPI application
app = FastAPI(
    title="Workflow Engine API",
    description="AI-powered workflow execution and management service",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add trusted host middleware for production security
if not getattr(settings, "DEBUG", False):
    app.add_middleware(
        TrustedHostMiddleware, allowed_hosts=["*"]  # Configure appropriately for production
    )


# Request/Response middleware for logging
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all HTTP requests and responses."""
    start_time = time.time()

    # Log request
    logger.info(
        f"→ {request.method} {request.url.path} - {request.client.host if request.client else 'unknown'}"
    )

    try:
        response = await call_next(request)
        process_time = time.time() - start_time

        # Log response
        logger.info(
            f"← {response.status_code} {request.method} {request.url.path} - {process_time:.3f}s"
        )

        return response
    except Exception as e:
        process_time = time.time() - start_time
        logger.error(
            f"← ERROR {request.method} {request.url.path} - {process_time:.3f}s - {str(e)}"
        )
        raise


# Exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle request validation errors."""
    logger.error(f"Validation error: {exc.errors()}")

    error_details = []
    for error in exc.errors():
        error_details.append(
            {
                "code": error["type"],
                "message": error["msg"],
                "field": ".".join(str(x) for x in error["loc"][1:])
                if len(error["loc"]) > 1
                else None,
            }
        )

    error_response = ErrorResponse(
        error="ValidationError",
        message="Request validation failed",
        details=error_details,
        timestamp=int(time.time()),
    )

    return JSONResponse(status_code=422, content=error_response.dict())


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle HTTP exceptions."""
    logger.error(f"HTTP error {exc.status_code}: {exc.detail}")

    error_response = ErrorResponse(
        error=f"HTTP{exc.status_code}Error", message=str(exc.detail), timestamp=int(time.time())
    )

    return JSONResponse(status_code=exc.status_code, content=error_response.dict())


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions."""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)

    error_response = ErrorResponse(
        error="InternalServerError",
        message="An internal server error occurred" if not settings.DEBUG else str(exc),
        timestamp=int(time.time()),
    )

    return JSONResponse(status_code=500, content=error_response.dict())


# Include routers
app.include_router(workflows_router)
app.include_router(triggers_router)


# Health check endpoint
@app.get("/health", response_model=HealthCheckResponse, tags=["health"])
async def health_check() -> HealthCheckResponse:
    """
    Health check endpoint for load balancers and monitoring.

    Returns service health status and dependency information.
    """
    try:
        # Check database connection
        db_healthy = test_db_connection()

        # Determine overall health status
        if db_healthy:
            status = HealthStatus.SERVING
            message = "Workflow Engine is healthy"
        else:
            status = HealthStatus.NOT_SERVING
            message = "Database connection failed"

        details = {
            "database": "connected" if db_healthy else "disconnected",
            "version": "1.0.0",
            "debug_mode": str(getattr(settings, "DEBUG", False)),
            "port": str(getattr(settings, "PORT", 8000)),
        }

        response = HealthCheckResponse(
            status=status, message=message, details=details, timestamp=int(time.time())
        )

        if status != HealthStatus.SERVING:
            return JSONResponse(status_code=503, content=response.dict())

        return response

    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        error_response = HealthCheckResponse(
            status=HealthStatus.NOT_SERVING,
            message=f"Health check failed: {str(e)}",
            details={"error": str(e)},
            timestamp=int(time.time()),
        )

        return JSONResponse(status_code=503, content=error_response.dict())


# Root endpoint
@app.get("/", tags=["root"])
async def root() -> Dict[str, Any]:
    """
    Root endpoint with API information.
    """
    return {
        "service": "Workflow Engine API",
        "version": "1.0.0",
        "description": "AI-powered workflow execution and management service",
        "docs_url": "/docs",
        "health_url": "/health",
        "endpoints": {"workflows": "/v1/workflows", "triggers": "/v1/triggers"},
        "status": "running",
        "timestamp": int(time.time()),
    }


# API versioning endpoint
@app.get("/v1", tags=["version"])
async def api_v1_info() -> Dict[str, Any]:
    """
    API v1 information endpoint.
    """
    return {
        "version": "v1",
        "description": "Workflow Engine API Version 1",
        "endpoints": {
            "workflows": {
                "base": "/v1/workflows",
                "operations": ["create", "get", "update", "delete", "list", "execute"],
                "description": "Workflow CRUD and execution operations",
            },
            "triggers": {
                "base": "/v1/triggers",
                "operations": ["create", "get", "update", "delete", "list", "fire", "events"],
                "description": "Workflow trigger management operations",
            },
        },
        "timestamp": int(time.time()),
    }


if __name__ == "__main__":
    import uvicorn

    logger.info("🎯 Workflow Engine - FastAPI Server")
    logger.info("=" * 50)

    uvicorn.run(
        "workflow_engine.main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info" if not settings.DEBUG else "debug",
        access_log=True,
    )
