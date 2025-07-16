"""
Base API client for external service integrations.

This module provides a unified HTTP client base class for all external API
integrations with common functionality like authentication, retries, error
handling, and rate limiting.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union

import httpx
from httpx import Response, HTTPStatusError, TimeoutException

from workflow_engine.core.config import get_settings
from workflow_engine.models.credential import OAuth2Credential


logger = logging.getLogger(__name__)


class APIClientError(Exception):
    """Base exception for API client errors."""
    pass


class AuthenticationError(APIClientError):
    """Raised when authentication fails."""
    pass


class RateLimitError(APIClientError):
    """Raised when rate limit is exceeded."""
    pass


class TokenExpiredError(APIClientError):
    """Raised when OAuth2 token is expired."""
    pass


class APIResponseError(APIClientError):
    """Raised when API returns an error response."""
    pass


class BaseAPIClient(ABC):
    """
    Base class for external API clients.
    
    Provides common functionality for HTTP requests, authentication,
    error handling, and retry mechanisms.
    """
    
    def __init__(self, credentials: Optional[OAuth2Credential] = None):
        """Initialize base API client."""
        self.settings = get_settings()
        self.credentials = credentials
        self._http_client: Optional[httpx.AsyncClient] = None
        
        # API client configuration
        self.base_url = self._get_base_url()
        self.timeout = httpx.Timeout(
            connect=self.settings.api_timeout_connect,
            read=self.settings.api_timeout_read
        )
        self.retry_delays = self.settings.get_retry_delays()
        self.max_retries = self.settings.api_max_retries
    
    @abstractmethod
    def _get_base_url(self) -> str:
        """Get the base URL for the API service."""
        pass
    
    @abstractmethod
    def _get_service_name(self) -> str:
        """Get the service name for logging and error reporting."""
        pass
    
    async def _get_http_client(self) -> httpx.AsyncClient:
        """Get HTTP client with lazy initialization."""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
                limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
                verify=True
            )
        return self._http_client
    
    async def _get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers."""
        if not self.credentials:
            return {}
        
        # Check if token is expired
        if self._is_token_expired():
            await self._refresh_token()
        
        return {
            "Authorization": f"Bearer {self.credentials.access_token}",
            "User-Agent": f"WorkflowEngine/1.0 ({self._get_service_name()})"
        }
    
    def _is_token_expired(self) -> bool:
        """Check if access token is expired or will expire soon."""
        if not self.credentials or not self.credentials.expires_at:
            return False
        
        # Consider token expired if it expires within 5 minutes
        buffer_time = timedelta(minutes=5)
        return datetime.utcnow() >= (self.credentials.expires_at - buffer_time)
    
    async def _refresh_token(self):
        """Refresh OAuth2 token if expired."""
        if not self.credentials or not self.credentials.refresh_token:
            raise AuthenticationError("No refresh token available")
        
        # Import here to avoid circular imports
        from workflow_engine.services.oauth2_handler import get_oauth2_handler
        
        try:
            oauth2_handler = await get_oauth2_handler()
            new_credential = await oauth2_handler.refresh_access_token(
                self.credentials.refresh_token,
                self.credentials.provider
            )
            
            # Update credentials
            self.credentials.access_token = new_credential.access_token
            self.credentials.expires_at = new_credential.expires_at
            if new_credential.refresh_token:
                self.credentials.refresh_token = new_credential.refresh_token
            
            logger.info(f"Token refreshed for {self._get_service_name()}")
            
        except Exception as e:
            logger.error(f"Failed to refresh token for {self._get_service_name()}: {e}")
            raise TokenExpiredError(f"Token refresh failed: {e}")
    
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Make HTTP request with retry mechanism.
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE, etc.)
            endpoint: API endpoint (relative to base_url)
            params: Query parameters
            data: Form data
            json: JSON payload
            headers: Additional headers
            **kwargs: Additional httpx request parameters
            
        Returns:
            Parsed JSON response
            
        Raises:
            APIClientError: For various API and authentication errors
        """
        http_client = await self._get_http_client()
        
        # Prepare headers
        auth_headers = await self._get_auth_headers()
        request_headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            **auth_headers
        }
        if headers:
            request_headers.update(headers)
        
        # Retry logic
        last_exception = None
        for attempt in range(self.max_retries + 1):
            try:
                # Make the request
                response = await http_client.request(
                    method=method,
                    url=endpoint,
                    params=params,
                    data=data,
                    json=json,
                    headers=request_headers,
                    **kwargs
                )
                
                # Handle response
                return await self._handle_response(response)
                
            except TokenExpiredError:
                # Try to refresh token and retry
                if attempt < self.max_retries:
                    try:
                        await self._refresh_token()
                        auth_headers = await self._get_auth_headers()
                        request_headers.update(auth_headers)
                        continue
                    except Exception as refresh_error:
                        logger.error(f"Token refresh failed: {refresh_error}")
                        raise TokenExpiredError("Authentication failed and token refresh failed")
                else:
                    raise
                    
            except RateLimitError:
                # Exponential backoff for rate limits
                if attempt < self.max_retries:
                    delay = self.retry_delays[min(attempt, len(self.retry_delays) - 1)]
                    logger.warning(f"Rate limit hit, retrying in {delay}s (attempt {attempt + 1})")
                    await asyncio.sleep(delay)
                    continue
                else:
                    raise
                    
            except (HTTPStatusError, TimeoutException, httpx.RequestError) as e:
                last_exception = e
                if attempt < self.max_retries:
                    delay = self.retry_delays[min(attempt, len(self.retry_delays) - 1)]
                    logger.warning(f"Request failed, retrying in {delay}s: {e}")
                    await asyncio.sleep(delay)
                    continue
                else:
                    break
        
        # All retries exhausted
        service_name = self._get_service_name()
        if last_exception:
            raise APIClientError(f"{service_name} API request failed after {self.max_retries} retries: {last_exception}")
        else:
            raise APIClientError(f"{service_name} API request failed after {self.max_retries} retries")
    
    async def _handle_response(self, response: Response) -> Dict[str, Any]:
        """Handle HTTP response and extract data."""
        # Check for rate limiting
        if response.status_code == 429:
            retry_after = response.headers.get("Retry-After", "60")
            raise RateLimitError(f"Rate limit exceeded. Retry after {retry_after} seconds")
        
        # Check for authentication errors
        if response.status_code == 401:
            raise TokenExpiredError("Access token expired or invalid")
        
        # Check for other client errors
        if response.status_code >= 400:
            try:
                error_data = response.json()
                error_message = error_data.get("error", {}).get("message", response.text)
            except (ValueError, KeyError):
                error_message = response.text or f"HTTP {response.status_code}"
            
            raise APIResponseError(f"{self._get_service_name()} API error: {error_message}")
        
        # Parse successful response
        try:
            return response.json()
        except ValueError:
            # Non-JSON response
            return {"data": response.text}
    
    async def close(self):
        """Close HTTP client."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None
            logger.info(f"{self._get_service_name()} HTTP client closed")


class PaginatedResponse:
    """Helper class for handling paginated API responses."""
    
    def __init__(self, items: List[Dict[str, Any]], next_page_token: Optional[str] = None):
        self.items = items
        self.next_page_token = next_page_token
        self.has_more = next_page_token is not None
    
    def __iter__(self):
        return iter(self.items)
    
    def __len__(self):
        return len(self.items) 