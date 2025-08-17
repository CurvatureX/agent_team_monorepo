"""
Exception classes for Google Calendar SDK.
"""


class GoogleCalendarError(Exception):
    """Base exception for Google Calendar SDK."""
    pass


class GoogleCalendarAuthError(GoogleCalendarError):
    """Raised when authentication fails."""
    pass


class GoogleCalendarRateLimitError(GoogleCalendarError):
    """Raised when rate limit is exceeded."""
    pass


class GoogleCalendarNotFoundError(GoogleCalendarError):
    """Raised when a resource is not found."""
    pass


class GoogleCalendarPermissionError(GoogleCalendarError):
    """Raised when permission is denied."""
    pass


class GoogleCalendarValidationError(GoogleCalendarError):
    """Raised when validation fails."""
    pass