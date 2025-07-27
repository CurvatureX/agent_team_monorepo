"""
Session API endpoints with Supabase Auth integration
支持RLS的会话管理端点
"""

from fastapi import APIRouter, HTTPException, Request, Depends
from typing import Optional, List
from app.models.session import (
    SessionCreate,
    SessionUpdate,
    Session,
    SessionResponse,
    SessionListResponse,
)
from app.models.base import ResponseModel
from app.dependencies import AuthenticatedDeps, get_session_id
from app.exceptions import ValidationError, NotFoundError
from app.database import sessions_rls_repo
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.post("/session", response_model=SessionResponse)
async def create_session(request: SessionCreate, deps: AuthenticatedDeps = Depends()):
    """
    Create a new session
    创建新的会话
    """
    try:
        logger.info(f"📝 Creating session for user {deps.current_user.sub}")

        # Validate action parameter
        valid_actions = ["chat", "workflow_generation", "workflow_execution", "tool_invocation"]
        if request.action and request.action not in valid_actions:
            raise ValidationError(
                f"Invalid action. Must be one of: {valid_actions}",
                details={"valid_actions": valid_actions},
            )

        # For workflow actions, workflow_id might be required
        if request.action in ["workflow_execution"] and not request.workflow_id:
            raise ValidationError(
                "workflow_id is required for workflow execution", details={"action": request.action}
            )

        # Prepare session data
        session_data = {
            "user_id": deps.current_user.sub,
            "session_type": request.session_type,
            "action": request.action,
            "workflow_id": request.workflow_id,
            "metadata": request.metadata,
            "status": "active",
        }

        # Create session using RLS repository
        result = sessions_rls_repo.create(session_data)

        if not result:
            raise HTTPException(status_code=500, detail="Failed to create session")

        logger.info(f"✅ Session created: {result['id']}")

        # Create session object
        session = Session(**result)

        return SessionResponse(session=session, message="Session created successfully")

    except (ValidationError, HTTPException):
        raise
    except Exception as e:
        logger.error(f"❌ Error creating session: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/session/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str = Depends(get_session_id), deps: AuthenticatedDeps = Depends()
):
    """
    Get session by ID with RLS
    通过ID获取会话（支持RLS）
    """
    try:
        logger.info(f"🔍 Getting session {session_id} for user {deps.current_user.sub}")

        # Get session from database with RLS
        result = sessions_rls_repo.get_by_id(session_id, access_token=deps.current_user.token)

        if not result:
            raise NotFoundError("Session")

        # Create session object
        session = Session(**result)

        logger.info(f"✅ Session retrieved: {session_id}")

        return SessionResponse(session=session, message="Session retrieved successfully")

    except (NotFoundError, HTTPException):
        raise
    except Exception as e:
        logger.error(f"❌ Error getting session {session_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/sessions", response_model=SessionListResponse)
async def list_user_sessions(
    page: int = 1, page_size: int = 20, deps: AuthenticatedDeps = Depends()
):
    """
    List all sessions for the current authenticated user
    列出当前认证用户的所有会话
    """
    try:
        logger.info(f"📋 Listing sessions for user {deps.current_user.sub}")

        # Get all sessions for this user with RLS
        sessions_data = sessions_rls_repo.get_by_user_id(
            deps.current_user.sub, access_token=deps.current_user.token
        )

        # Sort by created_at (most recent first)
        sessions_data.sort(key=lambda x: x.get("created_at", ""), reverse=True)

        # Apply pagination
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_sessions = sessions_data[start_idx:end_idx]

        # Convert to Session objects
        sessions = [Session(**session_data) for session_data in paginated_sessions]

        logger.info(f"✅ Retrieved {len(sessions)} sessions for user {deps.current_user.sub}")

        return SessionListResponse(
            sessions=sessions, total_count=len(sessions_data), page=page, page_size=page_size
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error listing sessions for user {deps.current_user.sub}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/session/{session_id}", response_model=ResponseModel)
async def delete_session(
    session_id: str = Depends(get_session_id), deps: AuthenticatedDeps = Depends()
):
    """
    Delete a session with RLS
    删除会话（支持RLS）
    """
    try:
        logger.info(f"🗑️ Deleting session {session_id} for user {deps.current_user.sub}")

        # Delete session with RLS (ensures user can only delete their own sessions)
        success = sessions_rls_repo.delete(session_id, access_token=deps.current_user.token)

        if not success:
            raise NotFoundError("Session")

        logger.info(f"✅ Session deleted: {session_id}")

        return ResponseModel(success=True, message="Session deleted successfully")

    except (NotFoundError, HTTPException):
        raise
    except Exception as e:
        logger.error(f"❌ Error deleting session {session_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/session/{session_id}", response_model=SessionResponse)
async def update_session(
    session_update: SessionUpdate,
    session_id: str = Depends(get_session_id),
    deps: AuthenticatedDeps = Depends(),
):
    """
    Update a session with RLS
    更新会话（支持RLS）
    """
    try:
        logger.info(f"📝 Updating session {session_id} for user {deps.current_user.sub}")

        # Prepare update data (only include non-None fields)
        update_data = session_update.dict(exclude_none=True)

        if not update_data:
            raise ValidationError("No update data provided")

        # Update session with RLS
        result = sessions_rls_repo.update(
            session_id, update_data, access_token=deps.current_user.token
        )

        if not result:
            raise NotFoundError("Session")

        # Create session object
        session = Session(**result)

        logger.info(f"✅ Session updated: {session_id}")

        return SessionResponse(session=session, message="Session updated successfully")

    except (ValidationError, NotFoundError, HTTPException):
        raise
    except Exception as e:
        logger.error(f"❌ Error updating session {session_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
