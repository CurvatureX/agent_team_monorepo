"""
Exception classes for Notion SDK.
"""

from typing import Optional, Dict, Any


class NotionError(Exception):
    """Base exception for all Notion SDK errors."""
    
    def __init__(self, message: str, error_code: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.error_code = error_code
        self.details = details or {}


class NotionAuthError(NotionError):
    """Raised when authentication fails."""
    pass


class NotionPermissionError(NotionError):
    """Raised when user lacks required permissions."""
    pass


class NotionNotFoundError(NotionError):
    """Raised when a resource is not found."""
    pass


class NotionValidationError(NotionError):
    """Raised when request validation fails."""
    pass


class NotionRateLimitError(NotionError):
    """Raised when rate limit is exceeded."""
    
    def __init__(self, message: str, retry_after: Optional[int] = None, **kwargs):
        super().__init__(message, **kwargs)
        self.retry_after = retry_after


class NotionConflictError(NotionError):
    """Raised when there's a conflict (e.g., duplicate resource)."""
    pass


class NotionServerError(NotionError):
    """Raised when Notion server returns 5xx error."""
    pass


class NotionConnectionError(NotionError):
    """Raised when connection to Notion fails."""
    pass