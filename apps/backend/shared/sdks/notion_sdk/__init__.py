"""
Notion SDK for workflow integration.

This package provides Notion API integration with OAuth2 authentication support.
"""

from .client import NotionClient
from .exceptions import (
    NotionAPIError,
    NotionAuthError,
    NotionObjectNotFoundError,
    NotionRateLimitError,
    NotionValidationError,
)
from .models import NotionBlock, NotionDatabase, NotionPage, NotionProperty, NotionUser
from .oauth2_client import NotionOAuth2SDK

__all__ = [
    "NotionClient",
    "NotionOAuth2SDK",
    "NotionAPIError",
    "NotionAuthError",
    "NotionObjectNotFoundError",
    "NotionRateLimitError",
    "NotionValidationError",
    "NotionPage",
    "NotionDatabase",
    "NotionBlock",
    "NotionUser",
    "NotionProperty",
]
