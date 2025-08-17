"""
Slack SDK for workflow automation.

This SDK provides comprehensive Slack integration for both trigger and action nodes
in the workflow system, including OAuth handling, message sending, and event processing.
"""

from .block_builder import SlackBlockBuilder
from .client import SlackWebClient
from .oauth2_client import SlackOAuth2SDK
from .exceptions import SlackAPIError, SlackAuthError, SlackRateLimitError
from .installation import SlackInstallationManager

# Export OAuth2SDK as the default SlackSDK for workflow integration
SlackSDK = SlackOAuth2SDK

__all__ = [
    "SlackWebClient",
    "SlackSDK",
    "SlackOAuth2SDK",
    "SlackInstallationManager",
    "SlackBlockBuilder",
    "SlackAPIError",
    "SlackAuthError",
    "SlackRateLimitError",
]
