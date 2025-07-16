"""
OAuth2 API schemas
"""

from typing import Optional
from pydantic import BaseModel, Field


class AuthURLRequest(BaseModel):
    """Request for generating OAuth2 authorization URL"""
    
    user_id: str = Field(..., description="User identifier")
    scopes: Optional[list[str]] = Field(default=None, description="OAuth2 scopes to request")
    redirect_uri: Optional[str] = Field(default=None, description="Custom redirect URI")


class AuthURLResponse(BaseModel):
    """Response containing OAuth2 authorization URL"""
    
    success: bool = Field(..., description="Whether the request was successful")
    auth_url: Optional[str] = Field(default=None, description="OAuth2 authorization URL")
    state: Optional[str] = Field(default=None, description="OAuth2 state parameter for CSRF protection")
    error: Optional[str] = Field(default=None, description="Error message if failed")


class CallbackResponse(BaseModel):
    """Response for OAuth2 callback processing"""
    
    success: bool = Field(..., description="Whether the callback was processed successfully")
    message: str = Field(..., description="Success or error message")
    credential_id: Optional[str] = Field(default=None, description="Credential ID if stored successfully")
    error: Optional[str] = Field(default=None, description="Error details if failed")


class OAuthErrorResponse(BaseModel):
    """Error response for OAuth2 operations"""
    
    success: bool = Field(default=False, description="Always false for error responses")
    error: str = Field(..., description="Error type or code")
    error_description: Optional[str] = Field(default=None, description="Human-readable error description")
    state: Optional[str] = Field(default=None, description="State parameter from original request") 