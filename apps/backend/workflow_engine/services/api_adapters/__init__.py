"""
API adapters for external service integrations.
"""

from .base import (
    APIAdapter,
    APIError,
    AuthenticationError,
    AuthorizationError,
    OAuth2Config,
    PermanentError,
    RateLimitError,
    TemporaryError,
    ValidationError,
    get_adapter,
    list_adapters,
    register_adapter,
)

try:
    from .google_calendar import GoogleCalendarAdapter
except ImportError as e:
    print(f"Warning: Could not import GoogleCalendarAdapter: {e}")

__all__ = [
    "APIAdapter",
    "OAuth2Config",
    "APIError",
    "ValidationError",
    "AuthenticationError",
    "AuthorizationError",
    "RateLimitError",
    "TemporaryError",
    "PermanentError",
    "register_adapter",
    "get_adapter",
    "list_adapters",
]
