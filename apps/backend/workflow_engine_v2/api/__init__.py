"""
API Router Aggregation for Workflow Engine V2

Combines all API endpoints into a single importable router.
"""

from fastapi import APIRouter

from .health import router as health_router
from .v2 import router as v2_router

# Create main API router
router = APIRouter()

# Include health check (at root level)
router.include_router(health_router)

# Include v2 API
router.include_router(v2_router)

__all__ = ["router"]
