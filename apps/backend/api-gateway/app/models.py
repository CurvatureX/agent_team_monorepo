"""
MVP Data Models including Supabase Auth models
"""

from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum


class MessageType(str, Enum):
    """Message types"""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class WorkflowEventType(str, Enum):
    """Workflow event types"""

    WAITING = "waiting"
    START = "start"
    DRAFT = "draft"
    DEBUGGING = "debugging"
    COMPLETE = "complete"
    ERROR = "error"


# Authentication Request Models
class RegisterRequest(BaseModel):
    """Request model for user registration"""

    email: str = Field(..., description="User email address")
    password: str = Field(..., min_length=6, description="User password (minimum 6 characters)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Optional user metadata")


class LoginRequest(BaseModel):
    """Request model for user login"""

    email: str = Field(..., description="User email address")
    password: str = Field(..., description="User password")


class RefreshTokenRequest(BaseModel):
    """Request model for token refresh"""

    refresh_token: str = Field(..., description="Refresh token")


# Authentication Response Models
class UserData(BaseModel):
    """User data model"""

    id: str = Field(..., description="User unique identifier")
    email: str = Field(..., description="User email")
    email_confirmed: bool = Field(..., description="Whether email is confirmed")
    created_at: str = Field(..., description="Account creation timestamp")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="User metadata")


class AuthResponse(BaseModel):
    """Response model for authentication operations"""

    access_token: Optional[str] = Field(
        None, description="JWT access token (null if email confirmation required)"
    )
    refresh_token: Optional[str] = Field(
        None, description="Refresh token (null if email confirmation required)"
    )
    expires_in: Optional[int] = Field(
        None, description="Token expiration time in seconds (null if email confirmation required)"
    )
    user: UserData = Field(..., description="User information")
    email_confirmation_required: Optional[bool] = Field(
        False, description="Whether email confirmation is required"
    )


class LogoutResponse(BaseModel):
    """Response model for logout"""

    success: bool = Field(..., description="Whether logout was successful")
    message: str = Field(..., description="Logout message")


class UserProfileResponse(BaseModel):
    """Response model for user profile"""

    id: str = Field(..., description="User unique identifier")
    email: str = Field(..., description="User email")
    email_confirmed: bool = Field(..., description="Whether email is confirmed")
    created_at: str = Field(..., description="Account creation timestamp")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="User metadata")


# Session Request Models
class SessionCreateRequest(BaseModel):
    """Request model for creating a session"""

    action: str = Field(..., description="Action type: 'create' or 'edit'")
    workflow_id: Optional[str] = Field(None, description="Workflow ID for edit action")
    meta_data: Dict[str, Any] = Field(default_factory=dict, description="Session metadata")


class ChatRequest(BaseModel):
    """Request model for chat"""

    session_id: str = Field(..., description="Session ID")
    message: str = Field(..., description="User message content")


# Response Models
class SessionResponse(BaseModel):
    """Response model for session operations"""

    session_id: str = Field(..., description="Session unique identifier")
    created_at: str = Field(..., description="Creation timestamp")


class WorkflowEventResponse(BaseModel):
    """Response model for workflow events"""

    type: WorkflowEventType = Field(..., description="Event type")
    workflow_id: Optional[str] = Field(None, description="Workflow ID")
    data: Optional[Dict[str, Any]] = Field(None, description="Event data")
    timestamp: str = Field(..., description="Event timestamp")


class ErrorResponse(BaseModel):
    """Error response model"""

    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")


class HealthResponse(BaseModel):
    """Health check response"""

    status: str = Field(..., description="Service status")
    version: str = Field(..., description="Service version")
