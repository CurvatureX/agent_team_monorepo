"""
API Gateway for Workflow Agent Team
"""

import logging
import sys
from contextlib import asynccontextmanager

import structlog
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from core.config import settings
from core.config_validator import ConfigurationError, get_missing_env_vars_message
from core.grpc_client import WorkflowAgentClient
from core.logging_middleware import setup_logging_middleware
from core.startup_checks import StartupCheckError, log_startup_status, run_startup_checks
from routers import mcp, workflow

# Load environment variables
load_dotenv()

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info("🚀 Starting API Gateway initialization")

    try:
        # Run startup health checks
        logger.info("Running startup health checks...")
        check_results = await run_startup_checks()
        log_startup_status(check_results)

        # Store check results in app state for health endpoint
        app.state.startup_checks = check_results

        # Initialize gRPC client
        logger.info("Initializing gRPC client...")
        app.state.workflow_client = WorkflowAgentClient()
        await app.state.workflow_client.connect()

        logger.info("✅ API Gateway startup completed successfully")

    except ConfigurationError as e:
        logger.error("❌ Configuration validation failed", error=str(e))
        if e.missing_vars:
            print("\n" + get_missing_env_vars_message(e.missing_vars))
        sys.exit(1)

    except StartupCheckError as e:
        logger.error("❌ Startup health checks failed", error=str(e), failed_checks=e.failed_checks)
        sys.exit(1)

    except Exception as e:
        logger.error("❌ Unexpected startup error", error=str(e))
        sys.exit(1)

    yield

    # Shutdown
    logger.info("🛑 Shutting down API Gateway")
    try:
        await app.state.workflow_client.close()
        logger.info("✅ API Gateway shutdown completed")
    except Exception as e:
        logger.error("Error during shutdown", error=str(e))


app = FastAPI(
    title="API Gateway",
    description="API Gateway for Workflow Agent Team",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup comprehensive logging middleware
setup_logging_middleware(app)

# Include routers
app.include_router(workflow.router, prefix="/api/v1/workflow", tags=["workflow"])
app.include_router(mcp.router, prefix="/api/v1/mcp", tags=["mcp"])


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    base_health = {
        "status": "healthy",
        "service": "api-gateway",
        "mcp_enabled": settings.MCP_ENABLED,
    }

    # Include startup check results if available
    if hasattr(app.state, "startup_checks"):
        base_health["startup_checks"] = app.state.startup_checks

    return base_health


@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "API Gateway for Workflow Agent Team"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, log_level="info")
