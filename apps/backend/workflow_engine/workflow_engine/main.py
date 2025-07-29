"""
Main gRPC server application.
"""

import logging
import sys
from typing import Optional

import grpc

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from workflow_engine.api.v1 import workflows, executions, triggers
from workflow_engine.core.config import get_settings
from shared.models.common import HealthResponse, HealthStatus
from workflow_engine.models.database import init_db, close_db
import time
import uvicorn

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


settings = get_settings()

app = FastAPI(
    title="Workflow Engine API",
    description="Service for managing and executing workflows.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

@app.on_event("startup")
def on_startup():
    init_db()

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
    # In a real application, you'd check dependencies (e.g., DB, Redis)
    return HealthResponse(
        status=HealthStatus.HEALTHY,
        version="1.0.0",
        timestamp=int(time.time()),
        details={
            "service": "workflow-engine",
            "database": "connected",  # Placeholder
            "redis": "connected"      # Placeholder
        }
    )

@app.get("/")
async def root():
    return {"message": "Workflow Engine API is running", "version": "1.0.0"}

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True
    ) 