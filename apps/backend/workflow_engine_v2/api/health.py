"""
Health Check Endpoint for Workflow Engine V2
"""

import time

from fastapi import APIRouter

from workflow_engine_v2.api.models import HealthResponse

# Track app start time for uptime
START_TIME = time.time()

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        version="2.0.0",
        uptime_seconds=time.time() - START_TIME,
        service="workflow_engine_v2",
    )
