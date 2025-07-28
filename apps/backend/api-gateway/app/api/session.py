"""
Session API endpoints with Supabase Auth integration
"""

from fastapi import APIRouter, HTTPException, Request, Depends
from app.models import SessionCreateRequest, SessionResponse, ErrorResponse
from app.database import sessions_rls_repo 
from app.config import settings
import structlog

logger = structlog.get_logger("session_api")
from typing import Optional


router = APIRouter()

@router.post("/session", response_model=SessionResponse)
async def create_session(request: SessionCreateRequest, http_request: Request):
    """
    Create a new session
    """
    try:
        # Get user from request state (already validated by jwt_auth_middleware)
        user = getattr(http_request.state, 'user', None)
        user_id = user.get("sub") if user else None
        
        # Validate action parameter
        if request.action not in ["create", "edit", "copy"]:
            raise HTTPException(
                status_code=400,
                detail="Invalid action. Must be 'create' or 'edit'"
            )
        
        # For edit action, workflow_id is required
        if request.action in ["edit", "copy"] and not request.workflow_id:
            raise HTTPException(
                status_code=400,
                detail="workflow_id is required for edit action"
            )

        # TODO: if copy, create a new workflow from the workflow_id
        
        # Prepare session data according to tech design
        session_data = {
            "user_id": user_id,
            "action_type": request.action,
            "source_workflow_id": request.workflow_id if request.workflow_id else None,
        }
        result = sessions_rls_repo.create(session_data)
        
        if not result:
            raise HTTPException(
                status_code=500,
                detail="Failed to create session"
            )
        
        return SessionResponse(
            session_id=result["id"],
            created_at=result["created_at"]
        )
    
    except HTTPException:
        raise
    except Exception as e:
        if settings.DEBUG:
            logger.error("Error creating session", error=str(e))
        
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )


@router.get("/session/{session_id}")
async def get_session(session_id: str, http_request: Request):
    """
    Get session by ID with RLS
    """
    try:
        # Get access token (user already validated by jwt_auth_middleware)
        access_token = getattr(http_request.state, 'access_token', None)
        
        # Get session from database with RLS (RLS ensures user can only access their own sessions)
        result = sessions_rls_repo.get_by_id(session_id, access_token=access_token)
        
        if not result:
            raise HTTPException(
                status_code=404,
                detail="Session not found"
            )
        
        return {
            "id": result["id"],
            "user_id": result.get("user_id"),
            "created_at": result["created_at"]
        }
    
    except HTTPException:
        raise
    except Exception as e:
        if settings.DEBUG:
            logger.error("Error getting session", error=str(e))
        
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )


@router.get("/sessions")
async def list_user_sessions(http_request: Request):
    """
    List all sessions for the current authenticated user
    """
    try:
        # Get user and access token (already validated by jwt_auth_middleware)
        user = getattr(http_request.state, 'user', None)
        user_id = user.get("sub") if user else None
        access_token = getattr(http_request.state, 'access_token', None)
        
        # Get all sessions for this user with RLS (RLS ensures user can only access their own sessions)
        sessions = sessions_rls_repo.get_by_user_id(user_id, access_token=access_token)
        
        # Sort by created_at (most recent first)
        sessions.sort(key=lambda x: x["created_at"], reverse=True)
        
        return {
            "user_id": user_id,
            "sessions": sessions,
            "total_count": len(sessions)
        }
    
    except HTTPException:
        raise
    except Exception as e:
        if settings.DEBUG:
            logger.error("Error listing user sessions", error=str(e))
        
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )


@router.delete("/session/{session_id}")
async def delete_session(session_id: str, http_request: Request):
    """
    Delete a session with RLS
    """
    try:
        access_token = getattr(http_request.state, 'access_token', None)
        
        # Delete session with RLS (RLS ensures user can only delete their own sessions)
        success = sessions_rls_repo.delete(session_id, access_token=access_token)
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail="Session not found or could not be deleted"
            )
        
        return {
            "success": True,
            "message": "Session deleted successfully",
            "session_id": session_id
        }
    
    except HTTPException:
        raise
    except Exception as e:
        if settings.DEBUG:
            logger.error("Error deleting session", error=str(e))
        
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )