"""
Generic API Call SDK for workflow automation.

This SDK provides generic HTTP API integration including:
- RESTful API calls (GET, POST, PUT, DELETE, PATCH)
- Request/response handling and validation
- Authentication methods (Bearer token, API key, Basic auth)
- Error handling and retry mechanisms
- Custom headers and query parameters
"""

from .client import ApiCallSDK
from .exceptions import (
    ApiCallError,
    ApiCallAuthError,
    ApiCallNotFoundError,
    ApiCallRateLimitError,
    ApiCallValidationError,
    ApiCallTimeoutError,
)
from .models import ApiRequest, ApiResponse

__version__ = "1.0.0"
__all__ = [
    "ApiCallSDK",
    "ApiCallError",
    "ApiCallAuthError",
    "ApiCallRateLimitError",
    "ApiCallNotFoundError",
    "ApiCallValidationError",
    "ApiCallTimeoutError",
    "ApiRequest",
    "ApiResponse",
]