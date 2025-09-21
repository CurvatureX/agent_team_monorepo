"""
External actions for workflow engine nodes.

This package contains modular external action handlers for different external services.
Each external action is implemented as a separate module for better maintainability.
"""

from .base_external_action import BaseExternalAction
from .github_external_action import GitHubExternalAction
from .google_calendar_external_action import GoogleCalendarExternalAction
from .notion_external_action import NotionExternalAction
from .slack_external_action import SlackExternalAction

__all__ = [
    "BaseExternalAction",
    "SlackExternalAction",
    "GitHubExternalAction",
    "GoogleCalendarExternalAction",
    "NotionExternalAction",
]
