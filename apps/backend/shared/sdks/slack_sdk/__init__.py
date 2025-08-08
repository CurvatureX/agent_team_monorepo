"""
Slack SDK for workflow automation.

This SDK provides comprehensive Slack integration for both trigger and action nodes
in the workflow system, including OAuth handling, message sending, and event processing.
"""

from .block_builder import SlackBlockBuilder
from .client import SlackWebClient
from .exceptions import SlackAPIError, SlackAuthError, SlackRateLimitError
from .installation import SlackInstallationManager

__all__ = [
    "SlackWebClient",
    "SlackInstallationManager",
    "SlackBlockBuilder",
    "SlackAPIError",
    "SlackAuthError",
    "SlackRateLimitError",
]
