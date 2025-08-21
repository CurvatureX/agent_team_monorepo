"""
Notion API exceptions for structured error handling.
"""

from typing import Any, Dict, Optional


class NotionAPIError(Exception):
    """Base exception for Notion API errors."""

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        response_data: Optional[Dict[str, Any]] = None,
        status_code: Optional[int] = None,
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.response_data = response_data or {}
        self.status_code = status_code


class NotionAuthError(NotionAPIError):
    """Raised when authentication with Notion fails."""

    def __init__(
        self,
        message: str = "Authentication failed",
        error_code: Optional[str] = None,
        response_data: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, error_code, response_data, 401)


class NotionRateLimitError(NotionAPIError):
    """Raised when Notion API rate limit is exceeded."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: Optional[int] = None,
        error_code: Optional[str] = None,
        response_data: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, error_code, response_data, 429)
        self.retry_after = retry_after


class NotionObjectNotFoundError(NotionAPIError):
    """Raised when a Notion object (page, database, etc.) is not found."""

    def __init__(
        self,
        message: str = "Object not found",
        error_code: Optional[str] = None,
        response_data: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, error_code, response_data, 404)


class NotionValidationError(NotionAPIError):
    """Raised when request parameters are invalid."""

    def __init__(
        self,
        message: str = "Invalid request parameters",
        error_code: Optional[str] = None,
        response_data: Optional[Dict[str, Any]] = None,
        status_code: Optional[int] = None,
    ):
        super().__init__(message, error_code, response_data, status_code or 400)


class NotionPermissionError(NotionAPIError):
    """Raised when insufficient permissions for the requested operation."""

    def __init__(
        self,
        message: str = "Insufficient permissions",
        error_code: Optional[str] = None,
        response_data: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, error_code, response_data, 403)


class NotionConflictError(NotionAPIError):
    """Raised when there's a conflict with the current state of the object."""

    def __init__(
        self,
        message: str = "Conflict with current state",
        error_code: Optional[str] = None,
        response_data: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, error_code, response_data, 409)


class NotionServiceUnavailableError(NotionAPIError):
    """Raised when Notion service is temporarily unavailable."""

    def __init__(
        self,
        message: str = "Service temporarily unavailable",
        error_code: Optional[str] = None,
        response_data: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, error_code, response_data, 503)
