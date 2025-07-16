"""
Credential data models for OAuth2 token management.

This module defines SQLAlchemy models for storing and managing
API credentials and OAuth2 tokens.
"""

from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID, uuid4

from sqlalchemy import (
    Column, String, Text, Boolean, DateTime, ForeignKey, TIMESTAMP, JSON
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from workflow_engine.models.database import Base


class OAuthToken(Base):
    """
    Model for storing OAuth2 tokens and API credentials.
    
    Based on the oauth_tokens table schema from supabase migration.
    Supports encrypted storage of sensitive credential data.
    """
    
    __tablename__ = "oauth_tokens"
    
    # Primary key
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Foreign key relationships
    user_id = Column(PG_UUID(as_uuid=True), nullable=False, index=True)
    integration_id = Column(String(255), nullable=True, index=True)
    
    # Provider information
    provider = Column(String(100), nullable=False, index=True)
    
    # Token data (encrypted in service layer)
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text, nullable=True)
    token_type = Column(String(50), default="Bearer")
    expires_at = Column(TIMESTAMP(timezone=True), nullable=True)
    
    # Additional credential data (JSONB for flexibility)
    credential_data = Column(JSONB, default=dict)
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(TIMESTAMP(timezone=True), default=func.current_timestamp())
    updated_at = Column(TIMESTAMP(timezone=True), default=func.current_timestamp(), onupdate=func.current_timestamp())
    
    def __repr__(self) -> str:
        return f"<OAuthToken(id={self.id}, user_id={self.user_id}, provider={self.provider})>"
    
    def to_dict(self, include_sensitive: bool = False) -> Dict[str, Any]:
        """
        Convert to dictionary representation.
        
        Args:
            include_sensitive: Whether to include sensitive token data
            
        Returns:
            Dictionary representation of the credential
        """
        data = {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "integration_id": self.integration_id,
            "provider": self.provider,
            "token_type": self.token_type,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        
        if include_sensitive:
            data.update({
                "access_token": self.access_token,
                "refresh_token": self.refresh_token,
                "credential_data": self.credential_data,
            })
        else:
            # Only include non-sensitive metadata
            data["credential_data"] = {
                k: v for k, v in (self.credential_data or {}).items()
                if k not in ["access_token", "refresh_token", "client_secret", "api_key"]
            }
        
        return data
    
    def is_expired(self) -> bool:
        """Check if the token is expired."""
        if not self.expires_at:
            return False
        return datetime.utcnow().replace(tzinfo=self.expires_at.tzinfo) >= self.expires_at
    
    def is_valid(self) -> bool:
        """Check if the credential is valid and usable."""
        return self.is_active and not self.is_expired()


class CredentialConfig:
    """
    Configuration model for credential data.
    
    This is a Pydantic-like model for validating and structuring
    credential data before storage.
    """
    
    def __init__(
        self,
        provider: str,
        access_token: str,
        refresh_token: Optional[str] = None,
        token_type: str = "Bearer",
        expires_at: Optional[datetime] = None,
        credential_data: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        self.provider = provider
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.token_type = token_type
        self.expires_at = expires_at
        self.credential_data = credential_data or {}
        
        # Add any additional fields to credential_data
        for key, value in kwargs.items():
            self.credential_data[key] = value
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "provider": self.provider,
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "token_type": self.token_type,
            "expires_at": self.expires_at,
            "credential_data": self.credential_data,
        }
    
    @classmethod
    def from_oauth2_response(
        cls,
        provider: str,
        oauth_response: Dict[str, Any]
    ) -> "CredentialConfig":
        """
        Create credential config from OAuth2 response.
        
        Args:
            provider: OAuth2 provider name
            oauth_response: Response from OAuth2 token endpoint
            
        Returns:
            Configured CredentialConfig instance
        """
        # Extract standard OAuth2 fields
        access_token = oauth_response.get("access_token")
        if not access_token:
            raise ValueError("OAuth2 response missing access_token")
        
        refresh_token = oauth_response.get("refresh_token")
        token_type = oauth_response.get("token_type", "Bearer")
        
        # Calculate expiry time
        expires_at = None
        expires_in = oauth_response.get("expires_in")
        if expires_in:
            from datetime import timedelta
            expires_at = datetime.utcnow() + timedelta(seconds=int(expires_in))
        
        # Store additional fields in credential_data
        credential_data = {}
        for key, value in oauth_response.items():
            if key not in ["access_token", "refresh_token", "token_type", "expires_in"]:
                credential_data[key] = value
        
        return cls(
            provider=provider,
            access_token=access_token,
            refresh_token=refresh_token,
            token_type=token_type,
            expires_at=expires_at,
            credential_data=credential_data,
        )


class OAuth2Credential:
    """
    Structured representation of OAuth2 credentials.
    
    Used for passing credential data between services
    without exposing internal model structure.
    """
    
    def __init__(
        self,
        access_token: str,
        refresh_token: Optional[str] = None,
        token_type: str = "Bearer",
        expires_at: Optional[datetime] = None,
        **metadata
    ):
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.token_type = token_type
        self.expires_at = expires_at
        self.metadata = metadata
    
    def is_expired(self) -> bool:
        """Check if the credential is expired."""
        if not self.expires_at:
            return False
        return datetime.utcnow().replace(tzinfo=self.expires_at.tzinfo) >= self.expires_at
    
    def get_auth_header(self) -> Dict[str, str]:
        """Get authorization header for API requests."""
        return {"Authorization": f"{self.token_type} {self.access_token}"}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "token_type": self.token_type,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            **self.metadata
        } 