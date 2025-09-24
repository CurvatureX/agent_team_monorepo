"""
Public authentication endpoints that do not require authentication
公共认证端点，无需认证
"""

from typing import Any, Dict, Optional

from app.dependencies import get_db_manager
from app.exceptions import ValidationError
from app.models import ResponseModel
from app.utils.logger import get_logger
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = get_logger(__name__)
router = APIRouter()


# Request/Response models
class LoginRequest(BaseModel):
    email: str = Field(..., description="User email address")
    password: str = Field(..., description="User password")


class LoginResponse(ResponseModel):
    access_token: str = Field(description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(description="Token expiration time in seconds")
    expires_at: int = Field(description="Token expiration timestamp")
    refresh_token: str = Field(description="Refresh token")
    user: Dict[str, Any] = Field(description="User information")


class RegisterRequest(BaseModel):
    email: str = Field(..., description="User email address")
    password: str = Field(..., description="User password")
    name: Optional[str] = Field(None, description="User display name")


class RegisterResponse(ResponseModel):
    user: Dict[str, Any] = Field(description="User information")
    session: Optional[Dict[str, Any]] = Field(None, description="Session information")


@router.post("/auth/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """
    User login - public endpoint that doesn't require authentication
    用户登录 - 公共端点，无需认证
    """
    try:
        logger.info(f"🔐 Login attempt for email: {request.email}")

        # Get database manager
        db_manager = await get_db_manager()
        supabase = db_manager.supabase_admin

        if not supabase:
            raise HTTPException(status_code=500, detail="Database connection failed")

        # Authenticate with Supabase Auth
        auth_response = supabase.auth.sign_in_with_password(
            {"email": request.email, "password": request.password}
        )

        if not auth_response.user or not auth_response.session:
            raise HTTPException(status_code=401, detail="Invalid email or password")

        logger.info(f"✅ Login successful for user: {auth_response.user.id}")

        return LoginResponse(
            access_token=auth_response.session.access_token,
            token_type="bearer",
            expires_in=auth_response.session.expires_in or 3600,
            expires_at=auth_response.session.expires_at or 0,
            refresh_token=auth_response.session.refresh_token or "",
            user={
                "id": auth_response.user.id,
                "email": auth_response.user.email,
                "name": auth_response.user.user_metadata.get("name"),
                "email_verified": auth_response.user.email_confirmed_at is not None,
                "created_at": auth_response.user.created_at,
                "updated_at": auth_response.user.updated_at,
            },
            message="Login successful",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Login error for {request.email}: {e}")
        raise HTTPException(status_code=500, detail="Login failed")


@router.post("/auth/register", response_model=RegisterResponse)
async def register(request: RegisterRequest):
    """
    User registration - public endpoint that doesn't require authentication
    用户注册 - 公共端点，无需认证
    """
    try:
        logger.info(f"👤 Registration attempt for email: {request.email}")

        # Get database manager
        db_manager = await get_db_manager()
        supabase = db_manager.supabase_admin

        if not supabase:
            raise HTTPException(status_code=500, detail="Database connection failed")

        # Register with Supabase Auth
        auth_response = supabase.auth.sign_up(
            {
                "email": request.email,
                "password": request.password,
                "options": {"data": {"name": request.name} if request.name else {}},
            }
        )

        if not auth_response.user:
            raise HTTPException(status_code=400, detail="Registration failed")

        logger.info(f"✅ Registration successful for user: {auth_response.user.id}")

        return RegisterResponse(
            user={
                "id": auth_response.user.id,
                "email": auth_response.user.email,
                "name": auth_response.user.user_metadata.get("name"),
                "email_verified": auth_response.user.email_confirmed_at is not None,
                "created_at": auth_response.user.created_at,
                "updated_at": auth_response.user.updated_at,
            },
            session={
                "access_token": auth_response.session.access_token
                if auth_response.session
                else None,
                "refresh_token": auth_response.session.refresh_token
                if auth_response.session
                else None,
                "expires_at": auth_response.session.expires_at if auth_response.session else None,
            }
            if auth_response.session
            else None,
            message="Registration successful",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Registration error for {request.email}: {e}")
        raise HTTPException(status_code=500, detail="Registration failed")


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(..., description="Refresh token")


@router.post("/auth/refresh", response_model=LoginResponse)
async def refresh_token(request: RefreshTokenRequest):
    """
    Refresh access token - public endpoint that doesn't require authentication
    刷新访问令牌 - 公共端点，无需认证
    """
    try:
        logger.info("🔄 Token refresh attempt")

        # Get database manager
        db_manager = await get_db_manager()
        supabase = db_manager.supabase_admin

        if not supabase:
            raise HTTPException(status_code=500, detail="Database connection failed")

        # Refresh token with Supabase Auth
        auth_response = supabase.auth.refresh_session(request.refresh_token)

        if not auth_response.user or not auth_response.session:
            raise HTTPException(status_code=401, detail="Invalid refresh token")

        logger.info(f"✅ Token refresh successful for user: {auth_response.user.id}")

        return LoginResponse(
            access_token=auth_response.session.access_token,
            token_type="bearer",
            expires_in=auth_response.session.expires_in or 3600,
            expires_at=auth_response.session.expires_at or 0,
            refresh_token=auth_response.session.refresh_token or "",
            user={
                "id": auth_response.user.id,
                "email": auth_response.user.email,
                "name": auth_response.user.user_metadata.get("name"),
                "email_verified": auth_response.user.email_confirmed_at is not None,
                "created_at": auth_response.user.created_at,
                "updated_at": auth_response.user.updated_at,
            },
            message="Token refresh successful",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Token refresh error: {e}")
        raise HTTPException(status_code=500, detail="Token refresh failed")
