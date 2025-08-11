"""
Session API endpoints with Supabase Auth integration
支持RLS的会话管理端点
"""

from typing import List, Optional

from app.core.database import create_user_supabase_client, get_supabase_admin
from app.dependencies import AuthenticatedDeps, get_session_id
from app.exceptions import NotFoundError, ValidationError
from app.models import (
    ResponseModel,
    Session,
    SessionCreate,
    SessionListResponse,
    SessionResponse,
    SessionUpdate,
)
from shared.logging_config import get_logger
from fastapi import APIRouter, Depends, HTTPException, Request

logger = get_logger(__name__)
router = APIRouter()


@router.post("/sessions", response_model=SessionResponse)
async def create_session(request: SessionCreate, deps: AuthenticatedDeps = Depends()):
    """
    Create a new session - 只 init session，不新建 workflow_agent_state
    根据最新的 proto 定义，workflow_agent_state 的管理全部由 workflow_agent 服务负责
    """
    try:
        logger.info(f"📝 Creating session for user {deps.current_user.sub}")

        # Prepare session data - 只存储基本会话信息
        session_data = {
            "user_id": deps.current_user.sub,
            "action_type": request.action,
            "source_workflow_id": request.workflow_id,  # 对于 edit/copy 这是 source_workflow_id
        }

        # Use the service role key for database operations
        admin_client = deps.db_manager.supabase_admin
        if not admin_client:
            raise HTTPException(status_code=500, detail="Failed to create database client")

        result = admin_client.table("sessions").insert(session_data).execute()
        result = result.data[0] if result.data else None

        if not result:
            raise HTTPException(status_code=500, detail="Failed to create session")

        logger.info(
            f"✅ Session created: {result['id']} (workflow_agent_state will be initialized by workflow_agent service)"
        )

        # Create session object
        session = Session(**result)

        return SessionResponse(session=session, message="Session created successfully")

    except (ValidationError, HTTPException):
        raise
    except Exception as e:
        import traceback

        logger.error(f"❌ Error creating session: {e}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/sessions/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str = Depends(get_session_id), deps: AuthenticatedDeps = Depends()
):
    """
    Get session by ID with RLS
    通过ID获取会话（支持RLS）
    """
    try:
        logger.info(f"🔍 Getting session {session_id} for user {deps.current_user.sub}")

        # Get session from database with service role key
        admin_client = deps.db_manager.supabase_admin
        if not admin_client:
            raise HTTPException(status_code=500, detail="Failed to create database client")

        result = (
            admin_client.table("sessions")
            .select("*")
            .eq("id", session_id)
            .eq("user_id", deps.current_user.sub)
            .execute()
        )
        result = result.data[0] if result.data else None

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

        # Get all sessions for this user with service role key
        admin_client = deps.db_manager.supabase_admin
        if not admin_client:
            raise HTTPException(status_code=500, detail="Failed to create database client")

        result = (
            admin_client.table("sessions")
            .select("*")
            .eq("user_id", deps.current_user.sub)
            .execute()
        )
        sessions_data = result.data if result.data else []

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


@router.delete("/sessions/{session_id}", response_model=ResponseModel)
async def delete_session(
    session_id: str = Depends(get_session_id), deps: AuthenticatedDeps = Depends()
):
    """
    Delete a session with RLS
    删除会话（支持RLS）
    """
    try:
        logger.info(f"🗑️ Deleting session {session_id} for user {deps.current_user.sub}")

        # Delete session with service role key (filter by user_id for security)
        admin_client = deps.db_manager.supabase_admin
        if not admin_client:
            raise HTTPException(status_code=500, detail="Failed to create database client")

        result = (
            admin_client.table("sessions")
            .delete()
            .eq("id", session_id)
            .eq("user_id", deps.current_user.sub)
            .execute()
        )
        success = len(result.data) > 0 if result.data else False

        if not success:
            raise NotFoundError("Session")

        logger.info(f"✅ Session deleted: {session_id}")

        return ResponseModel(success=True, message="Session deleted successfully")

    except (NotFoundError, HTTPException):
        raise
    except Exception as e:
        logger.error(f"❌ Error deleting session {session_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/sessions/{session_id}", response_model=SessionResponse)
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

        # Update session with service role key
        admin_client = deps.db_manager.supabase_admin
        if not admin_client:
            raise HTTPException(status_code=500, detail="Failed to create database client")

        result = (
            admin_client.table("sessions")
            .update(update_data)
            .eq("id", session_id)
            .eq("user_id", deps.current_user.sub)
            .execute()
        )
        result = result.data[0] if result.data else None

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
