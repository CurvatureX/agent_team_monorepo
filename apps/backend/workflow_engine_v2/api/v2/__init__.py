"""
V2 API Router Aggregation

Modern API endpoints with enhanced features and better documentation.
"""

from fastapi import APIRouter

from .executions import router as executions_router
from .logs import router as logs_router
from .workflows import router as workflows_router

# Create v2 router
router = APIRouter(prefix="/v2", tags=["V2 API"])

# Include all v2 sub-routers
router.include_router(workflows_router)
router.include_router(executions_router)
router.include_router(logs_router)
