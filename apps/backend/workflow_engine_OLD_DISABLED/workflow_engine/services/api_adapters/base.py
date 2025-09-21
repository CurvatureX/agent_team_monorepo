"""
Base classes and utilities for API adapters.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


class APIError(Exception):
    """Base exception for API-related errors."""

    pass


class ValidationError(APIError):
    """Raised when API parameters are invalid."""

    pass


class AuthenticationError(APIError):
    """Raised when authentication fails."""

    pass


class AuthorizationError(APIError):
    """Raised when authorization is insufficient."""

    pass


class RateLimitError(APIError):
    """Raised when rate limit is exceeded."""

    pass


class TemporaryError(APIError):
    """Raised for temporary errors that should be retried."""

    pass


class PermanentError(APIError):
    """Raised for permanent errors that should not be retried."""

    pass


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


class HTTPResponse:
    """Wrapper for HTTP responses."""

    def __init__(self, response: httpx.Response):
        self.response = response
        self.status_code = response.status_code
        self.headers = dict(response.headers)
        self.content = response.content
        self.text = response.text

    @property
    def is_success(self) -> bool:
        """Check if the response indicates success."""
        return 200 <= self.status_code < 300

    def json(self) -> Dict[str, Any]:
        """Parse response as JSON."""
        return self.response.json()


class APIAdapter(ABC):
    """Base class for all API adapters."""

    def __init__(self, **kwargs):
        self.logger = logging.getLogger(self.__class__.__name__)
        self._http_client = httpx.AsyncClient()

    @abstractmethod
    async def call(
        self, operation: str, parameters: Dict[str, Any], credentials: Dict[str, str]
    ) -> Dict[str, Any]:
        """Execute an API operation with the given parameters and credentials."""
        pass

    @abstractmethod
    def get_oauth2_config(self) -> OAuth2Config:
        """Get OAuth2 configuration for this provider."""
        pass

    @abstractmethod
    def validate_credentials(self, credentials: Dict[str, str]) -> bool:
        """Validate that the provided credentials are valid."""
        pass

    async def make_http_request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        data: Optional[Any] = None,
        params: Optional[Dict[str, str]] = None,
        timeout: int = 30,
    ) -> HTTPResponse:
        """Make an HTTP request with proper error handling."""
        try:
            # Prepare request kwargs
            request_kwargs = {
                "method": method,
                "url": url,
                "headers": headers,
                "params": params,
                "timeout": timeout,
            }

            # Use either json or data, but not both
            if json_data is not None:
                request_kwargs["json"] = json_data
            elif data is not None:
                request_kwargs["data"] = data

            response = await self._http_client.request(**request_kwargs)
            return HTTPResponse(response)
        except httpx.TimeoutException:
            raise TemporaryError(f"Request timeout after {timeout}s")
        except httpx.ConnectError:
            raise TemporaryError("Connection failed")
        except Exception as e:
            raise TemporaryError(f"HTTP request failed: {str(e)}")

    def _prepare_headers(self, credentials: Dict[str, str]) -> Dict[str, str]:
        """Prepare HTTP headers with authentication."""
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "AgentTeam-Workflow-Engine/1.0",
        }

        if "access_token" in credentials:
            headers["Authorization"] = f"Bearer {credentials['access_token']}"

        return headers

    def _handle_http_error(self, response: HTTPResponse):
        """Handle HTTP error responses."""
        if response.status_code == 401:
            raise AuthenticationError("Authentication failed")
        elif response.status_code == 403:
            raise AuthorizationError("Insufficient permissions")
        elif response.status_code == 429:
            raise RateLimitError("Rate limit exceeded")
        elif 400 <= response.status_code < 500:
            raise PermanentError(f"Client error: {response.status_code}")
        elif 500 <= response.status_code < 600:
            raise TemporaryError(f"Server error: {response.status_code}")
        else:
            raise APIError(f"Unexpected HTTP status: {response.status_code}")

    async def connection_test(self, credentials: Dict[str, str]) -> Dict[str, Any]:
        """Test the connection with the given credentials."""
        try:
            return await self._default_connection_test(credentials)
        except Exception as e:
            self.logger.error(f"Connection test failed: {str(e)}")
            return {"credentials_valid": False, "error": str(e)}

    async def _default_connection_test(self, credentials: Dict[str, str]) -> Dict[str, Any]:
        """Default implementation of connection test."""
        if self.validate_credentials(credentials):
            return {"credentials_valid": True}
        else:
            return {"credentials_valid": False, "error": "Invalid credentials"}

    async def close(self):
        """Close the HTTP client."""
        if self._http_client:
            await self._http_client.aclose()


# Registry for API adapters
_adapter_registry: Dict[str, type] = {}


def register_adapter(provider_name: str):
    """Decorator to register an API adapter."""

    def decorator(adapter_class):
        _adapter_registry[provider_name] = adapter_class
        return adapter_class

    return decorator


def get_adapter(provider_name: str) -> Optional[type]:
    """Get an adapter class by provider name."""
    return _adapter_registry.get(provider_name)


def list_adapters() -> List[str]:
    """List all registered adapter provider names."""
    return list(_adapter_registry.keys())
