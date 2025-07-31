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
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Add backend directory to Python path for shared models
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from shared.models.common import HealthResponse, HealthStatus
from workflow_engine.api.v1 import executions, triggers, workflows
from workflow_engine.core.config import get_settings
from workflow_engine.models.database import close_db

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


settings = get_settings()

app = FastAPI(
    title="Workflow Engine API",
    description="Service for managing and executing workflows.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)


@app.on_event("startup")
def on_startup():
    logger.info("Workflow Engine service starting up")


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
