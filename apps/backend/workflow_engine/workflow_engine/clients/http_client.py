"""
HTTP Client for API requests.

Supports multiple authentication methods, retry mechanisms, and timeout controls.
"""

import json
import logging
import time
from typing import Any, Dict, List, Optional, Union
from datetime import datetime

import httpx
from httpx import Timeout, Limits, HTTPError, ConnectError, TimeoutException

from workflow_engine.core.config import get_settings


logger = logging.getLogger(__name__)


class HTTPClientError(Exception):
    """Base exception for HTTP client errors."""
    pass


class AuthenticationError(HTTPClientError):
    """Raised when authentication fails."""
    pass


class RateLimitError(HTTPClientError):
    """Raised when rate limit is exceeded."""
    pass


class ResponseSizeError(HTTPClientError):
    """Raised when response size exceeds limit."""
    pass


class HTTPClient:
    """
    HTTP client with authentication, retry, and size limit support.
    
    Supports Bearer Token, API Key, and Basic Auth authentication methods.
    Includes automatic retry with exponential backoff.
    """
    
    def __init__(self):
        """Initialize HTTP client with configuration."""
        self.settings = get_settings()
        
        # Configure timeouts based on TASK requirements
        self.timeout = httpx.Timeout(
            connect=5.0,  # 5 second connect timeout
            read=30.0,    # 30 second read timeout
            write=None,   # No write timeout
            pool=None     # No pool timeout
        )
        
        # Configure connection limits
        self.limits = Limits(
            max_connections=20,
            max_keepalive_connections=10
        )
        
        # Response size limit (10MB)
        self.max_response_size = 10 * 1024 * 1024  # 10MB in bytes
        
        # Retry configuration (2s, 4s, 8s exponential backoff)
        self.max_retries = 3
        self.retry_delays = [2, 4, 8]
        
        # Default headers
        self.default_headers = {
            "User-Agent": "WorkflowEngine/1.0",
            "Accept": "application/json"
        }
    
    def request(
        self,
        method: str,
        url: str,
        auth_config: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        data: Optional[Union[Dict[str, Any], str]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Make HTTP request with authentication and retry.
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE, etc.)
            url: Request URL
            auth_config: Authentication configuration
            headers: Request headers
            data: Request body data
            json_data: JSON request data
            **kwargs: Additional httpx request parameters
            
        Returns:
            Dictionary containing response data and metadata
            
        Raises:
            HTTPClientError: For various HTTP client errors
        """
        method = method.upper()
        
        # Validate method
        if method not in ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]:
            raise HTTPClientError(f"Unsupported HTTP method: {method}")
        
        # Prepare headers
        request_headers = self.default_headers.copy()
        if headers:
            request_headers.update(headers)
        
        # Apply authentication
        if auth_config:
            auth_headers = self._apply_auth(auth_config)
            request_headers.update(auth_headers)
        
        # Prepare request data
        request_kwargs = {
            "headers": request_headers,
            "timeout": self.timeout,
            **kwargs
        }
        
        if json_data:
            request_kwargs["json"] = json_data
        elif data:
            if isinstance(data, dict):
                request_kwargs["json"] = data
            else:
                request_kwargs["content"] = data
        
        # Execute request with retry
        for attempt in range(self.max_retries + 1):
            try:
                logger.info(f"HTTP {method} request to {url} (attempt {attempt + 1})")
                
                with httpx.Client(limits=self.limits) as client:
                    response = client.request(method, url, **request_kwargs)
                    
                    # Check response size limit
                    content_length = response.headers.get("content-length")
                    if content_length and int(content_length) > self.max_response_size:
                        raise ResponseSizeError(
                            f"Response size {content_length} exceeds limit {self.max_response_size}"
                        )
                    
                    # Handle HTTP status codes
                    if response.status_code == 429:  # Rate limit
                        if attempt < self.max_retries:
                            time.sleep(self.retry_delays[attempt])
                            continue
                        else:
                            raise RateLimitError(f"Rate limit exceeded: {response.text}")
                    
                    if response.status_code == 401:
                        raise AuthenticationError(f"Authentication failed: {response.text}")
                    
                    response.raise_for_status()
                    
                    # Parse response
                    return self._handle_response(response)
                    
            except (ConnectError, TimeoutException) as e:
                logger.warning(f"Network error on attempt {attempt + 1}: {e}")
                if attempt < self.max_retries:
                    time.sleep(self.retry_delays[attempt])
                    continue
                else:
                    raise HTTPClientError(f"Network error after {self.max_retries} retries: {e}") from e
            
            except HTTPError as e:
                # Don't retry on HTTP errors (except rate limit, handled above)
                raise HTTPClientError(f"HTTP error: {e}") from e
            
            except Exception as e:
                logger.error(f"Unexpected error on attempt {attempt + 1}: {e}")
                if attempt < self.max_retries:
                    time.sleep(self.retry_delays[attempt])
                    continue
                else:
                    raise HTTPClientError(f"Request failed after {self.max_retries} retries: {e}") from e
        
        # Should not reach here
        raise HTTPClientError("Request failed after all retry attempts")
    
    def _apply_auth(self, auth_config: Dict[str, Any]) -> Dict[str, str]:
        """
        Apply authentication to request headers.
        
        Args:
            auth_config: Authentication configuration
            
        Returns:
            Headers dictionary with authentication
            
        Raises:
            AuthenticationError: If auth config is invalid
        """
        auth_type = auth_config.get("type")
        headers = {}
        
        if auth_type == "bearer":
            token = auth_config.get("token")
            if not token:
                raise AuthenticationError("Bearer token is required")
            headers["Authorization"] = f"Bearer {token}"
        
        elif auth_type == "api_key":
            key_name = auth_config.get("key_name")
            key_value = auth_config.get("key_value")
            location = auth_config.get("location", "header")
            
            if not key_name or not key_value:
                raise AuthenticationError("API key name and value are required")
            
            if location == "header":
                headers[key_name] = key_value
            else:
                # For query parameters, we'll let the caller handle it
                # This is a simplified implementation
                raise AuthenticationError("Query parameter API keys not supported in headers")
        
        elif auth_type == "basic_auth":
            username = auth_config.get("username")
            password = auth_config.get("password")
            
            if not username or not password:
                raise AuthenticationError("Username and password are required for basic auth")
            
            import base64
            credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
            headers["Authorization"] = f"Basic {credentials}"
        
        else:
            raise AuthenticationError(f"Unsupported authentication type: {auth_type}")
        
        return headers
    
    def _handle_response(self, response: httpx.Response) -> Dict[str, Any]:
        """
        Handle HTTP response and parse content.
        
        Args:
            response: HTTP response object
            
        Returns:
            Dictionary with response data and metadata
        """
        # Get response text with size limit check
        content = response.content
        if len(content) > self.max_response_size:
            raise ResponseSizeError(
                f"Response content size {len(content)} exceeds limit {self.max_response_size}"
            )
        
        # Try to parse JSON response
        response_data = None
        content_type = response.headers.get("content-type", "").lower()
        
        if "application/json" in content_type:
            try:
                response_data = response.json()
            except json.JSONDecodeError:
                response_data = response.text
        else:
            response_data = response.text
        
        return {
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "data": response_data,
            "url": str(response.url),
            "method": response.request.method,
            "success": True,
            "response_time": response.elapsed.total_seconds(),
            "timestamp": datetime.utcnow().isoformat()
        }


# Convenience functions for common HTTP methods

def get(url: str, auth_config: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
    """Make GET request."""
    client = HTTPClient()
    return client.request("GET", url, auth_config=auth_config, **kwargs)


def post(url: str, auth_config: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
    """Make POST request."""
    client = HTTPClient()
    return client.request("POST", url, auth_config=auth_config, **kwargs)


def put(url: str, auth_config: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
    """Make PUT request."""
    client = HTTPClient()
    return client.request("PUT", url, auth_config=auth_config, **kwargs)


def delete(url: str, auth_config: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
    """Make DELETE request."""
    client = HTTPClient()
    return client.request("DELETE", url, auth_config=auth_config, **kwargs) 