"""
Google Calendar API endpoints for workflow scheduler service
"""

import logging
from typing import Dict

from fastapi import APIRouter, HTTPException, Path

from workflow_scheduler.services.google_calendar_token_manager import (
    get_google_calendar_token_manager,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/google_calendar/token_manager/status")
async def get_token_manager_status() -> Dict:
    """
    Get Google Calendar token manager status.

    Returns information about the background token refresh service.
    """
    try:
        token_manager = get_google_calendar_token_manager()
        status = await token_manager.get_status()
        return status
    except Exception as e:
        logger.error(f"❌ Error getting token manager status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error getting status: {str(e)}")


@router.post("/google_calendar/token_manager/refresh/{user_id}")
async def force_refresh_user_token(
    user_id: str = Path(..., description="User ID to refresh token for")
) -> Dict:
    """
    Force refresh a specific user's Google Calendar token.

    This endpoint allows manual token refresh for testing or troubleshooting.
    """
    try:
        token_manager = get_google_calendar_token_manager()
        success, message = await token_manager.force_refresh_user_token(user_id)

        if success:
            return {
                "success": True,
                "message": message,
                "user_id": user_id,
            }
        else:
            raise HTTPException(status_code=400, detail=f"Token refresh failed: {message}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error force refreshing token for user {user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error refreshing token: {str(e)}")


@router.post("/google_calendar/token_manager/start")
async def start_token_manager() -> Dict:
    """
    Start the Google Calendar token manager (if not already running).

    For administrative use to start the background service.
    """
    try:
        token_manager = get_google_calendar_token_manager()

        if token_manager.is_running:
            return {
                "success": False,
                "message": "Token manager is already running",
                "status": "running",
            }

        await token_manager.start()
        return {
            "success": True,
            "message": "Token manager started successfully",
            "status": "running",
        }
    except Exception as e:
        logger.error(f"❌ Error starting token manager: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error starting token manager: {str(e)}")


@router.post("/google_calendar/token_manager/stop")
async def stop_token_manager() -> Dict:
    """
    Stop the Google Calendar token manager.

    For administrative use to stop the background service.
    """
    try:
        token_manager = get_google_calendar_token_manager()

        if not token_manager.is_running:
            return {
                "success": False,
                "message": "Token manager is not running",
                "status": "stopped",
            }

        await token_manager.stop()
        return {
            "success": True,
            "message": "Token manager stopped successfully",
            "status": "stopped",
        }
    except Exception as e:
        logger.error(f"❌ Error stopping token manager: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error stopping token manager: {str(e)}")
