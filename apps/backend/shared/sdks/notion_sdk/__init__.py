"""
Notion SDK for workflow automation.

This SDK provides comprehensive Notion integration including:
- Database management (list, query, create)
- Page management (create, get, update, archive)
- Block management (get, append, update, delete)
- Search functionality
- User management
- OAuth2 authentication support
"""

from .client import NotionSDK
from .exceptions import (
    NotionError,
    NotionAuthError,
    NotionPermissionError,
    NotionNotFoundError,
    NotionValidationError,
    NotionRateLimitError,
    NotionConflictError,
    NotionServerError,
    NotionConnectionError,
)
from .models import (
    Database,
    Page,
    Block,
    User,
    RichText,
    SearchResult,
    QueryResult,
)

__version__ = "1.0.0"
__all__ = [
    "NotionSDK",
    "NotionError",
    "NotionAuthError",
    "NotionPermissionError",
    "NotionNotFoundError",
    "NotionValidationError",
    "NotionRateLimitError",
    "NotionConflictError",
    "NotionServerError",
    "NotionConnectionError",
    "Database",
    "Page",
    "Block",
    "User",
    "RichText",
    "SearchResult",
    "QueryResult",
]