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
- Graceful shutdown with log flushing
"""

from __future__ import annotations

import logging
import os
import signal
import sys

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Import the aggregated API router
from workflow_engine_v2.api import router as api_router

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Reduce verbosity of noisy loggers
logging.getLogger("httpx").setLevel(logging.WARNING)  # Reduce Supabase HTTP request logs
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)  # Reduce HTTP access logs

# Global flag for shutdown
_shutdown_requested = False


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

    # Start async user-friendly logger
    try:
        from workflow_engine_v2.services.user_friendly_logger import get_async_user_friendly_logger

        async_logger = get_async_user_friendly_logger()
        await async_logger.start()
        logger.info("✅ Async user-friendly logging system started")
    except Exception as e:
        logger.warning(f"⚠️ Failed to start async logger: {e}")

    logger.info("✅ API endpoints ready")
    logger.info("   - Health: /health")
    logger.info("   - API: /v2/*")

    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGTERM, _handle_shutdown_signal)
    signal.signal(signal.SIGINT, _handle_shutdown_signal)
    logger.info("✅ Signal handlers registered (SIGTERM, SIGINT)")


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event - drain all pending logs"""
    global _shutdown_requested
    _shutdown_requested = True

    logger.info("🛑 Workflow Engine V2 shutting down...")
    logger.info("💾 Draining pending logs...")

    try:
        # Stop async user-friendly logger and drain queue
        from workflow_engine_v2.services.user_friendly_logger import get_async_user_friendly_logger

        async_logger = get_async_user_friendly_logger()
        await async_logger.stop(timeout=5.0)
        logger.info("✅ All pending logs drained successfully")
    except Exception as e:
        logger.error(f"❌ Error draining logs during shutdown: {e}")

    logger.info("👋 Shutdown complete")


def _handle_shutdown_signal(signum, frame):
    """Handle shutdown signals (SIGTERM, SIGINT)"""
    global _shutdown_requested
    signal_name = "SIGTERM" if signum == signal.SIGTERM else "SIGINT"
    logger.warning(f"⚠️ Received {signal_name} signal - initiating graceful shutdown...")
    _shutdown_requested = True

    # Note: Async logger will be drained in shutdown_event()
    # Signal handler cannot run async code, so we just exit
    logger.info("📝 Async logs will be drained in shutdown event")

    # Let uvicorn handle the actual shutdown
    sys.exit(0)


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
