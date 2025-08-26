"""
Data models for API Call SDK.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union


@dataclass
class ApiRequest:
    """Represents an API request configuration."""

    method: str
    url: str
    headers: Optional[Dict[str, str]] = None
    query_params: Optional[Dict[str, str]] = None
    body: Optional[Union[Dict[str, Any], str, bytes]] = None
    timeout: Optional[int] = 30
    auth_type: Optional[str] = None  # "bearer", "api_key", "basic", "oauth2"
    auth_credentials: Optional[Dict[str, str]] = None

    def __post_init__(self):
        """Validate request parameters."""
        if self.method not in ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]:
            raise ValueError(f"Invalid HTTP method: {self.method}")

        if not self.url:
            raise ValueError("URL cannot be empty")

        if self.headers is None:
            self.headers = {}

        if self.query_params is None:
            self.query_params = {}

        if self.auth_credentials is None:
            self.auth_credentials = {}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ApiRequest":
        """Create ApiRequest from dictionary."""
        return cls(
            method=data.get("method", "GET").upper(),
            url=data["url"],
            headers=data.get("headers", {}),
            query_params=data.get("query_params", {}),
            body=data.get("body"),
            timeout=data.get("timeout", 30),
            auth_type=data.get("auth_type"),
            auth_credentials=data.get("auth_credentials", {}),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "method": self.method,
            "url": self.url,
            "headers": self.headers,
            "query_params": self.query_params,
            "body": self.body,
            "timeout": self.timeout,
            "auth_type": self.auth_type,
            "auth_credentials": self.auth_credentials,
        }


@dataclass
class ApiResponse:
    """Represents an API response."""

    status_code: int
    headers: Dict[str, str]
    body: Union[Dict[str, Any], str, bytes, None] = None
    content_type: Optional[str] = None
    encoding: Optional[str] = None
    request_duration: Optional[float] = None
    request_url: Optional[str] = None

    def __post_init__(self):
        """Process response data."""
        if self.headers is None:
            self.headers = {}

        # Extract content type from headers if not provided
        if not self.content_type and "content-type" in self.headers:
            self.content_type = self.headers["content-type"].split(";")[0].strip()

    @property
    def is_success(self) -> bool:
        """Check if response indicates success (2xx status codes)."""
        return 200 <= self.status_code < 300

    @property
    def is_json(self) -> bool:
        """Check if response content type is JSON."""
        return self.content_type and "application/json" in self.content_type

    @property
    def is_xml(self) -> bool:
        """Check if response content type is XML."""
        return self.content_type and (
            "application/xml" in self.content_type or "text/xml" in self.content_type
        )

    @property
    def is_text(self) -> bool:
        """Check if response content type is text."""
        return self.content_type and self.content_type.startswith("text/")

    @classmethod
    def from_httpx_response(cls, response, request_url: str = None) -> "ApiResponse":
        """Create ApiResponse from httpx response."""
        try:
            # Try to parse JSON first
            if "application/json" in response.headers.get("content-type", ""):
                body = response.json()
            else:
                body = response.text
        except Exception:
            body = response.content

        return cls(
            status_code=response.status_code,
            headers=dict(response.headers),
            body=body,
            content_type=response.headers.get("content-type"),
            request_url=request_url or str(response.url),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "status_code": self.status_code,
            "headers": self.headers,
            "body": self.body,
            "content_type": self.content_type,
            "encoding": self.encoding,
            "request_duration": self.request_duration,
            "request_url": self.request_url,
            "is_success": self.is_success,
        }
