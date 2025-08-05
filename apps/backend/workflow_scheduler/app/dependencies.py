"""
FastAPI dependencies for workflow_scheduler
"""

from typing import Generator

from fastapi import Depends, HTTPException

from .services.deployment_service import DeploymentService
from .services.lock_manager import DistributedLockManager
from .services.trigger_manager import TriggerManager

# Global service instances - will be set during app startup
_deployment_service: DeploymentService = None
_trigger_manager: TriggerManager = None
_lock_manager: DistributedLockManager = None


def set_global_services(
    deployment_service: DeploymentService,
    trigger_manager: TriggerManager,
    lock_manager: DistributedLockManager,
):
    """Set global service instances during app startup"""
    global _deployment_service, _trigger_manager, _lock_manager
    _deployment_service = deployment_service
    _trigger_manager = trigger_manager
    _lock_manager = lock_manager


def get_deployment_service() -> DeploymentService:
    """Get deployment service dependency"""
    if _deployment_service is None:
        raise HTTPException(status_code=503, detail="Deployment service not available")
    return _deployment_service


def get_trigger_manager() -> TriggerManager:
    """Get trigger manager dependency"""
    if _trigger_manager is None:
        raise HTTPException(status_code=503, detail="Trigger manager not available")
    return _trigger_manager


def get_lock_manager() -> DistributedLockManager:
    """Get lock manager dependency"""
    if _lock_manager is None:
        raise HTTPException(status_code=503, detail="Lock manager not available")
    return _lock_manager
