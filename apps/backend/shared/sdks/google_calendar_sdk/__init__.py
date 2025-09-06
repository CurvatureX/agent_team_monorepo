"""
Google Calendar SDK for workflow automation.

This SDK provides comprehensive Google Calendar integration including:
- Event management (create, update, delete, list)
- Calendar management (create, get, list)
- Event search and filtering
- OAuth2 authentication and token management
- Webhook notifications (watch/stop)
"""

from .client import GoogleCalendarSDK
from .exceptions import (
    GoogleCalendarAuthError,
    GoogleCalendarError,
    GoogleCalendarNotFoundError,
    GoogleCalendarPermissionError,
    GoogleCalendarRateLimitError,
)
from .models import Calendar, Event

__version__ = "1.0.0"
__all__ = [
    "GoogleCalendarSDK",
    "GoogleCalendarError",
    "GoogleCalendarAuthError",
    "GoogleCalendarRateLimitError",
    "GoogleCalendarNotFoundError",
    "GoogleCalendarPermissionError",
    "Calendar",
    "Event",
]
