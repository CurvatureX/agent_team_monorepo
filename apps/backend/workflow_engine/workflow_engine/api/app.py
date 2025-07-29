"""
FastAPI application for workflow engine APIs.

This runs alongside the gRPC server to provide REST API endpoints
for node specifications and workflow validation.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from shared.node_specs import node_spec_registry
from workflow_engine.api.node_specs import router as node_specs_router
from workflow_engine.core.config import get_settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan events."""
    logger.info("🚀 Starting Workflow Engine API...")

    # Initialize node specifications
    try:
        spec_count = len(node_spec_registry.list_all_specs())
        logger.info(f"✅ Loaded {spec_count} node specifications")
    except Exception as e:
        logger.error(f"❌ Failed to load node specifications: {e}")

    yield

    logger.info("🛑 Shutting down Workflow Engine API...")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="Workflow Engine API",
        description="REST API for workflow engine node specifications and validation",
        version="1.0.0",
        lifespan=lifespan,
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(node_specs_router, prefix="/api/v1")

    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {"status": "healthy", "service": "workflow_engine_api"}

    @app.get("/")
    async def root():
        """Root endpoint."""
        return {"service": "Workflow Engine API", "version": "1.0.0", "docs": "/docs"}

    return app


# Create app instance
app = create_app()

if __name__ == "__main__":
    import uvicorn

    settings = get_settings()

    # Run FastAPI server
    uvicorn.run(
        "workflow_engine.api.app:app",
        host="0.0.0.0",
        port=8001,  # Different port from gRPC (8000)
        reload=settings.DEBUG,
        log_level="info",
    )
