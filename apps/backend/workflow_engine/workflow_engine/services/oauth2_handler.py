"""
OAuth2 authorization handler for external service integration.

This module provides OAuth2 authorization flow management for Google Calendar,
GitHub, Slack and other external services. It handles state management, token
exchange, and automatic token refresh.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from urllib.parse import urlencode, urljoin

import httpx
from httpx import Response, HTTPStatusError, TimeoutException

from workflow_engine.core.config import get_settings
from workflow_engine.core.redis_client import get_redis_client, RedisStateError
from workflow_engine.models.credential import OAuth2Credential
from workflow_engine.services.credential_service import CredentialService


logger = logging.getLogger(__name__)


class OAuth2Error(Exception):
    """Base exception for OAuth2 errors."""
    pass


class OAuth2StateError(OAuth2Error):
    """Raised when OAuth2 state is invalid or expired."""
    pass


class OAuth2TokenError(OAuth2Error):
    """Raised when token exchange or refresh fails."""
    pass


class OAuth2ConfigurationError(OAuth2Error):
    """Raised when OAuth2 provider configuration is invalid."""
    pass


class OAuth2Handler:
    """
    OAuth2 authorization handler for external services.
    
    Provides methods for generating authorization URLs, exchanging authorization
    codes for tokens, and refreshing access tokens. Supports multiple providers
    with configurable scopes and redirect URIs.
    """
    
    def __init__(self):
        """Initialize OAuth2 handler."""
        self.settings = get_settings()
        self.credential_service = CredentialService()
        
        # HTTP client for token requests
        self.http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(
                connect=self.settings.api_timeout_connect,
                read=self.settings.api_timeout_read
            )
        )
    
    async def generate_auth_url(
        self, 
        provider: str, 
        user_id: str, 
        redirect_uri: str,
        scopes: Optional[List[str]] = None
    ) -> str:
        """
        Generate OAuth2 authorization URL.
        
        Args:
            provider: OAuth2 provider (google_calendar, github, slack)
            user_id: User identifier for state management
            redirect_uri: Callback URI after authorization
            scopes: Optional list of scopes (uses default if None)
            
        Returns:
            Authorization URL for user to visit
            
        Raises:
            OAuth2ConfigurationError: If provider config is invalid
            OAuth2StateError: If state storage fails
        """
        try:
            # Get provider configuration
            provider_config = self.settings.get_oauth2_config(provider)
            
            # Validate provider configuration
            if not provider_config.get("client_id") or not provider_config.get("client_secret"):
                missing_providers = self.settings.validate_oauth2_providers()
                if provider.replace("_", " ").title() in missing_providers:
                    raise OAuth2ConfigurationError(
                        f"OAuth2 configuration missing for {provider}. "
                        f"Please set client_id and client_secret environment variables."
                    )
            
            # Use provided scopes or default
            if scopes is None:
                scopes = provider_config["scopes"]
            
            # Store state in Redis
            redis_client = await get_redis_client()
            state = await redis_client.store_oauth_state(
                user_id=user_id,
                provider=provider,
                redirect_uri=redirect_uri,
                scopes=scopes
            )
            
            # Build authorization URL
            auth_params = {
                "client_id": provider_config["client_id"],
                "redirect_uri": redirect_uri,
                "scope": " ".join(scopes),
                "state": state,
                "response_type": "code",
            }
            
            # Provider-specific parameters
            if provider == "google_calendar":
                auth_params["access_type"] = "offline"
                auth_params["prompt"] = "consent"
            elif provider == "slack":
                auth_params["user_scope"] = ",".join(scopes)
            
            auth_url = f"{provider_config['auth_url']}?{urlencode(auth_params)}"
            
            logger.info(f"Generated OAuth2 auth URL for user {user_id}, provider {provider}")
            return auth_url
            
        except (KeyError, ValueError) as e:
            raise OAuth2ConfigurationError(f"Invalid provider configuration for {provider}: {e}")
        except RedisStateError as e:
            raise OAuth2StateError(f"Failed to store OAuth2 state: {e}")
    
    async def exchange_code_for_tokens(
        self, 
        provider: str, 
        code: str, 
        state: str,
        redirect_uri: str
    ) -> OAuth2Credential:
        """
        Exchange authorization code for access and refresh tokens.
        
        Args:
            provider: OAuth2 provider
            code: Authorization code from callback
            state: State parameter for validation
            redirect_uri: Redirect URI used in authorization
            
        Returns:
            OAuth2Credential with access and refresh tokens
            
        Raises:
            OAuth2StateError: If state is invalid or expired
            OAuth2TokenError: If token exchange fails
        """
        try:
            # Validate state and get stored data
            redis_client = await get_redis_client()
            state_data = await redis_client.get_oauth_state(state)
            
            if not state_data:
                raise OAuth2StateError("Invalid or expired OAuth2 state parameter")
            
            if state_data["provider"] != provider:
                raise OAuth2StateError(f"State provider mismatch: expected {provider}, got {state_data['provider']}")
            
            # Get provider configuration
            provider_config = self.settings.get_oauth2_config(provider)
            
            # Prepare token exchange request
            token_data = {
                "client_id": provider_config["client_id"],
                "client_secret": provider_config["client_secret"],
                "code": code,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            }
            
            # Make token exchange request
            response = await self._make_token_request(
                provider_config["token_url"],
                token_data,
                provider
            )
            
            # Parse response based on provider
            token_response = await self._parse_token_response(response, provider)
            
            # Create OAuth2Credential
            credential = OAuth2Credential(
                access_token=token_response["access_token"],
                refresh_token=token_response.get("refresh_token"),
                token_type=token_response.get("token_type", "Bearer"),
                expires_in=token_response.get("expires_in"),
                expires_at=self._calculate_expires_at(token_response.get("expires_in")),
                scope=token_response.get("scope"),
                provider=provider
            )
            
            # Clean up state
            await redis_client.delete_oauth_state(state)
            
            logger.info(f"Successfully exchanged code for tokens: user {state_data['user_id']}, provider {provider}")
            return credential
            
        except (KeyError, ValueError) as e:
            raise OAuth2TokenError(f"Invalid token exchange response: {e}")
        except (HTTPStatusError, TimeoutException) as e:
            raise OAuth2TokenError(f"Token exchange request failed: {e}")
        except RedisStateError as e:
            raise OAuth2StateError(f"State validation failed: {e}")
    
    async def refresh_access_token(
        self, 
        refresh_token: str, 
        provider: str
    ) -> OAuth2Credential:
        """
        Refresh OAuth2 access token using refresh token.
        
        Args:
            refresh_token: Refresh token from previous authorization
            provider: OAuth2 provider
            
        Returns:
            New OAuth2Credential with refreshed tokens
            
        Raises:
            OAuth2TokenError: If token refresh fails
        """
        try:
            # Get provider configuration
            provider_config = self.settings.get_oauth2_config(provider)
            
            # Prepare token refresh request
            token_data = {
                "client_id": provider_config["client_id"],
                "client_secret": provider_config["client_secret"],
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            }
            
            # Make token refresh request
            response = await self._make_token_request(
                provider_config["token_url"],
                token_data,
                provider
            )
            
            # Parse response
            token_response = await self._parse_token_response(response, provider)
            
            # Create new credential (preserve refresh token if not returned)
            credential = OAuth2Credential(
                access_token=token_response["access_token"],
                refresh_token=token_response.get("refresh_token", refresh_token),
                token_type=token_response.get("token_type", "Bearer"),
                expires_in=token_response.get("expires_in"),
                expires_at=self._calculate_expires_at(token_response.get("expires_in")),
                scope=token_response.get("scope"),
                provider=provider
            )
            
            logger.info(f"Successfully refreshed token for provider {provider}")
            return credential
            
        except (KeyError, ValueError) as e:
            raise OAuth2TokenError(f"Invalid token refresh response: {e}")
        except (HTTPStatusError, TimeoutException) as e:
            raise OAuth2TokenError(f"Token refresh request failed: {e}")
    
    async def is_token_expired(self, credential: OAuth2Credential) -> bool:
        """
        Check if access token is expired or will expire soon.
        
        Args:
            credential: OAuth2 credential to check
            
        Returns:
            True if token is expired or expires within 5 minutes
        """
        if not credential.expires_at:
            # If no expiration time, assume token is valid
            return False
        
        # Consider token expired if it expires within 5 minutes
        buffer_time = timedelta(minutes=5)
        return datetime.utcnow() >= (credential.expires_at - buffer_time)
    
    async def _make_token_request(
        self, 
        token_url: str, 
        token_data: Dict[str, str], 
        provider: str
    ) -> Response:
        """Make HTTP request for token exchange or refresh."""
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
            "User-Agent": f"WorkflowEngine/1.0 ({provider})"
        }
        
        response = await self.http_client.post(
            token_url,
            data=token_data,
            headers=headers
        )
        response.raise_for_status()
        return response
    
    async def _parse_token_response(
        self, 
        response: Response, 
        provider: str
    ) -> Dict[str, Any]:
        """Parse token response based on provider format."""
        if provider == "github":
            # GitHub returns form-encoded response
            content_type = response.headers.get("content-type", "")
            if "application/x-www-form-urlencoded" in content_type:
                # Parse form-encoded response
                from urllib.parse import parse_qs
                response_data = parse_qs(response.text)
                return {k: v[0] if v else None for k, v in response_data.items()}
        
        # Default: JSON response
        return response.json()
    
    def _calculate_expires_at(self, expires_in: Optional[int]) -> Optional[datetime]:
        """Calculate absolute expiration time from relative expires_in."""
        if expires_in is None:
            return None
        return datetime.utcnow() + timedelta(seconds=expires_in)
    
    async def close(self):
        """Close HTTP client."""
        await self.http_client.aclose()


# Global OAuth2 handler instance
_oauth2_handler: Optional[OAuth2Handler] = None


async def get_oauth2_handler() -> OAuth2Handler:
    """Get global OAuth2 handler instance."""
    global _oauth2_handler
    if _oauth2_handler is None:
        _oauth2_handler = OAuth2Handler()
    return _oauth2_handler


async def close_oauth2_handler():
    """Close global OAuth2 handler instance."""
    global _oauth2_handler
    if _oauth2_handler:
        await _oauth2_handler.close()
        _oauth2_handler = None 