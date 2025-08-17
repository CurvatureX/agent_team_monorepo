"""
Exception classes for API Call SDK.
"""


class ApiCallError(Exception):
    """Base exception for API Call SDK."""
    pass


class ApiCallAuthError(ApiCallError):
    """Raised when authentication fails."""
    pass


class ApiCallRateLimitError(ApiCallError):
    """Raised when rate limit is exceeded."""
    pass


class ApiCallNotFoundError(ApiCallError):
    """Raised when a resource is not found."""
    pass


class ApiCallValidationError(ApiCallError):
    """Raised when request validation fails."""
    pass


class ApiCallTimeoutError(ApiCallError):
    """Raised when request times out."""
    pass