"""
Shared SDKs for external API integrations.

This module provides unified SDKs for external API integrations used across
the workflow engine. All external API calls are centralized here for better
maintainability and consistency.
"""

from .base import BaseSDK, SDKError, AuthenticationError, RateLimitError

# Import new folder-based SDKs with error handling
try:
    from .google_calendar_sdk import GoogleCalendarSDK
except ImportError as e:
    GoogleCalendarSDK = None
    print(f"Warning: Failed to import GoogleCalendarSDK: {e}")

try:
    from .github_sdk import GitHubSDK
except ImportError as e:
    GitHubSDK = None
    print(f"Warning: Failed to import GitHubSDK: {e}")

try:
    from .slack_sdk import SlackSDK
except ImportError as e:
    SlackSDK = None
    print(f"Warning: Failed to import SlackSDK: {e}")

try:
    from .email_sdk import EmailSDK
except ImportError as e:
    EmailSDK = None
    print(f"Warning: Failed to import EmailSDK: {e}")

try:
    from .api_call_sdk import ApiCallSDK
except ImportError as e:
    ApiCallSDK = None
    print(f"Warning: Failed to import ApiCallSDK: {e}")

__all__ = [
    "BaseSDK",
    "SDKError", 
    "AuthenticationError",
    "RateLimitError",
    "GoogleCalendarSDK",
    "GitHubSDK", 
    "SlackSDK",
    "EmailSDK",
    "ApiCallSDK"
]