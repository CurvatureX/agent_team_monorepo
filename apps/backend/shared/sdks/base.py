"""
Base SDK classes and utilities for external API integrations.
"""

import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx


class SDKError(Exception):
    """Base exception for SDK-related errors."""
    pass


class AuthenticationError(SDKError):
    """Raised when authentication fails."""
    pass


class AuthorizationError(SDKError):
    """Raised when authorization is insufficient."""
    pass


class RateLimitError(SDKError):
    """Raised when rate limit is exceeded."""
    pass


class ValidationError(SDKError):
    """Raised when parameters are invalid."""
    pass


class TemporaryError(SDKError):
    """Raised for temporary errors that should be retried."""
    pass


class PermanentError(SDKError):
    """Raised for permanent errors that should not be retried."""
    pass


@dataclass
class APIResponse:
    """Standard API response wrapper."""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    status_code: Optional[int] = None
    response_time_ms: Optional[int] = None
    provider: Optional[str] = None
    operation: Optional[str] = None


@dataclass
class OAuth2Config:
    """OAuth2 configuration for an API provider."""
    client_id: str
    client_secret: str
    auth_url: str
    token_url: str
    revoke_url: Optional[str] = None
    scopes: List[str] = None
    redirect_uri: Optional[str] = None


class BaseSDK(ABC):
    """Base class for all external API SDKs."""
    
    def __init__(self, **kwargs):
        self.logger = logging.getLogger(self.__class__.__name__)
        self._http_client = httpx.AsyncClient(timeout=30.0)
        self.provider_name = self.__class__.__name__.replace('SDK', '').lower()
        
    @property
    @abstractmethod
    def base_url(self) -> str:
        """Get the base URL for the API."""
        pass
    
    @property
    @abstractmethod
    def supported_operations(self) -> Dict[str, str]:
        """Get supported operations and their descriptions."""
        pass
    
    @abstractmethod
    def get_oauth2_config(self) -> OAuth2Config:
        """Get OAuth2 configuration for this provider."""
        pass
    
    @abstractmethod
    def validate_credentials(self, credentials: Dict[str, str]) -> bool:
        """Validate that the provided credentials are valid."""
        pass
    
    @abstractmethod
    async def call_operation(
        self, 
        operation: str, 
        parameters: Dict[str, Any], 
        credentials: Dict[str, str]
    ) -> APIResponse:
        """Execute an API operation with the given parameters and credentials."""
        pass
    
    async def make_http_request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None
    ) -> httpx.Response:
        """Make an HTTP request with proper error handling."""
        start_time = time.time()
        
        try:
            response = await self._http_client.request(
                method=method,
                url=url,
                headers=headers,
                json=json_data,
                data=data,
                params=params,
                timeout=timeout or 30
            )
            
            self.logger.debug(
                f"{method} {url} - {response.status_code} "
                f"({int((time.time() - start_time) * 1000)}ms)"
            )
            
            return response
            
        except httpx.TimeoutException:
            raise TemporaryError(f"Request timeout after {timeout or 30}s")
        except httpx.ConnectError:
            raise TemporaryError("Connection failed")
        except Exception as e:
            raise TemporaryError(f"HTTP request failed: {str(e)}")
    
    def prepare_headers(self, credentials: Dict[str, str], extra_headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """Prepare HTTP headers with authentication."""
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "AgentTeam-Workflow-Engine/1.0"
        }
        
        # Add extra headers if provided
        if extra_headers:
            headers.update(extra_headers)
        
        # Add authentication
        if "access_token" in credentials:
            headers["Authorization"] = f"Bearer {credentials['access_token']}"
        elif "api_key" in credentials:
            headers["Authorization"] = f"Bearer {credentials['api_key']}"
        
        return headers
    
    def handle_http_error(self, response: httpx.Response, operation: str = None) -> APIResponse:
        """Handle HTTP error responses and return appropriate APIResponse."""
        error_msg = f"HTTP {response.status_code}"
        
        # Try to extract error message from response
        try:
            error_data = response.json()
            if isinstance(error_data, dict):
                error_msg = error_data.get('error', error_data.get('message', error_msg))
        except:
            error_msg = response.text or error_msg
        
        # Determine error type
        if response.status_code == 401:
            raise AuthenticationError(f"Authentication failed: {error_msg}")
        elif response.status_code == 403:
            raise AuthorizationError(f"Insufficient permissions: {error_msg}")
        elif response.status_code == 429:
            raise RateLimitError(f"Rate limit exceeded: {error_msg}")
        elif 400 <= response.status_code < 500:
            raise PermanentError(f"Client error: {error_msg}")
        elif 500 <= response.status_code < 600:
            raise TemporaryError(f"Server error: {error_msg}")
        else:
            raise SDKError(f"Unexpected HTTP status {response.status_code}: {error_msg}")
    
    async def test_connection(self, credentials: Dict[str, str]) -> APIResponse:
        """Test the connection with the given credentials."""
        try:
            result = await self._test_connection_impl(credentials)
            return APIResponse(
                success=True,
                data=result,
                provider=self.provider_name,
                operation="connection_test"
            )
        except Exception as e:
            self.logger.error(f"Connection test failed: {str(e)}")
            return APIResponse(
                success=False,
                error=str(e),
                provider=self.provider_name,
                operation="connection_test"
            )
    
    async def _test_connection_impl(self, credentials: Dict[str, str]) -> Dict[str, Any]:
        """Default implementation of connection test. Override in subclasses."""
        if self.validate_credentials(credentials):
            return {"credentials_valid": True}
        else:
            raise ValidationError("Invalid credentials")
    
    def format_datetime(self, dt_input) -> str:
        """Format datetime for API consumption. Override in subclasses if needed."""
        if dt_input is None:
            raise ValidationError("Datetime input cannot be None")
        elif isinstance(dt_input, str):
            return dt_input
        elif isinstance(dt_input, datetime):
            return dt_input.isoformat()
        else:
            raise ValidationError(f"Invalid datetime format: {type(dt_input)}")
    
    async def close(self):
        """Close the HTTP client."""
        if self._http_client:
            await self._http_client.aclose()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()