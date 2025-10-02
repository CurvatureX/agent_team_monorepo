"""
Workflow Engine V2 - Main Application

Modern FastAPI-based workflow execution engine with comprehensive user-friendly logging.
Integrates seamlessly with the API Gateway's logs endpoint system.

Features:
- Modern execution engine with detailed progress tracking
- User-friendly logs exposed via /v2/workflows/executions/{execution_id}/logs
- Real-time log streaming
- Direct Supabase integration
- Clean, professional API organization
"""

from __future__ import annotations

import logging
import os

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Import the aggregated API router
from workflow_engine_v2.api import router as api_router

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Create FastAPI app
app = FastAPI(
    title="Workflow Engine V2",
    description="Modern workflow execution engine with comprehensive user-friendly logging",
    version="2.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all API routes
app.include_router(api_router)


@app.on_event("startup")
async def startup_event():
    """Application startup event"""
    logger.info("🚀 Workflow Engine V2 starting up...")
    logger.info("✅ Modern execution engine initialized")
    logger.info("✅ User-friendly logging system active")
    logger.info("✅ API endpoints ready")
    logger.info("   - Health: /health")
    logger.info("   - API: /v2/*")


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event"""
    logger.info("🛑 Workflow Engine V2 shutting down...")


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    logger.error(f"🚨 Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=500, content={"error": "Internal server error", "detail": str(exc)}
    )


def main():
    """Main entry point"""
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8002"))

    logger.info(f"🚀 Starting Workflow Engine V2 on {host}:{port}")

    uvicorn.run("main:app", host=host, port=port, reload=True, log_level="info")


if __name__ == "__main__":
    main()


__all__ = ["app"]
