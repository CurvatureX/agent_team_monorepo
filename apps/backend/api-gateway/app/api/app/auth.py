"""
Authentication and user profile API endpoints
认证和用户资料API端点
"""

from typing import Any, Dict, List, Optional

from app.core.database import create_user_supabase_client
from app.dependencies import AuthenticatedDeps
from app.exceptions import NotFoundError, ValidationError
from app.models import ResponseModel
from pydantic import BaseModel, Field
from typing import Dict, Any, List

# Local models for auth endpoints
class UserProfileResponse(ResponseModel):
    user_profile: Dict[str, Any] = Field(description="User profile information")

class UserSessionListResponse(ResponseModel):
    sessions: List[Dict[str, Any]] = Field(description="List of user sessions")
    total_count: int = Field(default=0, description="Total number of sessions")
    page: int = Field(default=1, description="Current page")
    page_size: int = Field(default=20, description="Page size")
from app.utils.logger import get_logger
from fastapi import APIRouter, Depends, HTTPException

logger = get_logger(__name__)
router = APIRouter()


@router.get("/auth/profile", response_model=UserProfileResponse)
async def get_user_profile(deps: AuthenticatedDeps = Depends()):
    """
    Get current user profile information
    获取当前用户资料信息
    """
    try:
        logger.info(f"👤 Getting profile for user {deps.current_user.sub}")

        # Extract user information from JWT token
        user_profile = {
            "user_id": deps.current_user.sub,
            "email": deps.current_user.email,
            "name": getattr(deps.current_user, "name", None),
            "avatar_url": getattr(deps.current_user, "avatar_url", None),
            "created_at": getattr(deps.current_user, "created_at", None),
            "updated_at": getattr(deps.current_user, "updated_at", None),
            "email_verified": getattr(deps.current_user, "email_verified", False),
            "phone": getattr(deps.current_user, "phone", None),
            "metadata": getattr(deps.current_user, "user_metadata", {}),
        }

        logger.info(f"✅ Profile retrieved for user {deps.current_user.sub}")

        return UserProfileResponse(
            user_profile=user_profile, message="User profile retrieved successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting user profile: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/auth/sessions", response_model=UserSessionListResponse)
async def get_user_sessions(
    page: int = 1, page_size: int = 20, deps: AuthenticatedDeps = Depends()
):
    """
    Get user's active sessions (auth-specific)
    获取用户的活跃会话（认证相关）
    """
    try:
        logger.info(f"🔐 Getting auth sessions for user {deps.current_user.sub}")

        # Get service role client
        admin_client = deps.db_manager.supabase_admin
        if not admin_client:
            raise HTTPException(status_code=500, detail="Failed to create database client")

        # Get sessions with auth context
        result = (
            admin_client.table("sessions")
            .select("id, session_type, status, created_at, updated_at, last_activity, metadata")
            .eq("user_id", deps.current_user.sub)
            .order("created_at", desc=True)
            .execute()
        )

        sessions_data = result.data if result.data else []

        # Apply pagination
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_sessions = sessions_data[start_idx:end_idx]

        # Add additional auth context to sessions
        auth_sessions = []
        for session in paginated_sessions:
            auth_session = {
                **session,
                "auth_context": {
                    "token_issued_at": getattr(deps.current_user, "iat", None),
                    "token_expires_at": getattr(deps.current_user, "exp", None),
                    "issuer": getattr(deps.current_user, "iss", None),
                    "audience": getattr(deps.current_user, "aud", None),
                },
            }
            auth_sessions.append(auth_session)

        logger.info(
            f"✅ Retrieved {len(auth_sessions)} auth sessions for user {deps.current_user.sub}"
        )

        return UserSessionListResponse(
            sessions=auth_sessions,
            total_count=len(sessions_data),
            page=page,
            page_size=page_size,
            message="User sessions retrieved successfully",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting user sessions: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
