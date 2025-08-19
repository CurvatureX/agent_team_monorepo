"""
External Action Node Models

This module defines Pydantic models for all external action nodes including
GitHub, Slack, Notion, and other third-party integrations.
"""

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class NotionActionType(str, Enum):
    """Notion action types mapping to streamlined MCP API."""

    SEARCH = "search"
    PAGE_GET = "page_get"
    PAGE_CREATE = "page_create"
    PAGE_UPDATE = "page_update"
    DATABASE_GET = "database_get"
    DATABASE_QUERY = "database_query"


class NotionSearchFilter(BaseModel):
    """Notion search filtering configuration."""

    object_type: Optional[str] = Field(None, description="Filter by object type (page/database)")
    property: Optional[str] = Field(None, description="Property name for filtering")
    value: Optional[str] = Field(None, description="Property value for filtering")


class NotionPageContent(BaseModel):
    """Notion page content configuration."""

    blocks: List[Dict[str, Any]] = Field(default_factory=list, description="Content blocks")
    mode: Optional[str] = Field("append", description="Content mode (append/replace)")


class NotionBlockOperation(BaseModel):
    """Notion block operation configuration."""

    operation: str = Field(..., description="Operation type (update/insert/delete/append)")
    block_id: Optional[str] = Field(None, description="Target block ID")
    position: Optional[str] = Field(None, description="Insert position (before/after)")
    block_data: Optional[Dict[str, Any]] = Field(None, description="Block content data")


class NotionDatabaseQuery(BaseModel):
    """Notion database query configuration."""

    filter: Optional[Dict[str, Any]] = Field(None, description="Advanced filter object")
    sorts: Optional[List[Dict[str, Any]]] = Field(None, description="Sort configuration")
    limit: Optional[int] = Field(10, description="Maximum results")
    simple_filter: Optional[Dict[str, Any]] = Field(
        None, description="Simple property-based filter"
    )


class NotionExternalActionParams(BaseModel):
    """Notion external action parameters model."""

    # Core parameters
    action_type: NotionActionType = Field(..., description="Notion operation type")
    access_token: str = Field(..., description="Notion integration access token")

    # Operation-specific parameters
    query: Optional[str] = Field(None, description="Search query text")
    page_id: Optional[str] = Field(None, description="Notion page ID")
    database_id: Optional[str] = Field(None, description="Notion database ID")
    parent_id: Optional[str] = Field(None, description="Parent page/database ID")
    parent_type: Optional[str] = Field("page", description="Parent type (page/database)")

    # Content parameters
    properties: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Page properties"
    )
    content: Optional[NotionPageContent] = Field(None, description="Page content configuration")
    block_operations: Optional[List[NotionBlockOperation]] = Field(
        default_factory=list, description="Advanced block operations"
    )

    # Query parameters
    search_filter: Optional[NotionSearchFilter] = Field(
        None, description="Search filtering options"
    )
    database_query: Optional[NotionDatabaseQuery] = Field(
        None, description="Database query configuration"
    )

    # Options
    include_content: Optional[bool] = Field(
        False, description="Include page/block content in results"
    )
    limit: Optional[int] = Field(10, description="Maximum results to return")


class NotionExternalActionResult(BaseModel):
    """Notion external action result model."""

    action: str = Field(..., description="Action that was performed")
    status: str = Field(..., description="Operation status (success/error)")
    result: Dict[str, Any] = Field(..., description="Operation result data")
    operations_performed: List[str] = Field(
        default_factory=list, description="List of operations that were performed"
    )
    errors: List[str] = Field(default_factory=list, description="Any errors encountered")

    # Additional metadata
    execution_time_ms: Optional[float] = Field(None, description="Execution time in milliseconds")
    page_url: Optional[str] = Field(None, description="URL of the created/updated page")
    total_count: Optional[int] = Field(None, description="Total count for search/query operations")
    has_more: Optional[bool] = Field(None, description="Whether more results are available")


class GitHubActionType(str, Enum):
    """GitHub action types."""

    CREATE_ISSUE = "create_issue"
    CREATE_PULL_REQUEST = "create_pull_request"
    ADD_COMMENT = "add_comment"
    CLOSE_ISSUE = "close_issue"
    MERGE_PR = "merge_pr"
    LIST_ISSUES = "list_issues"
    GET_ISSUE = "get_issue"


class GitHubExternalActionParams(BaseModel):
    """GitHub external action parameters model."""

    action: GitHubActionType = Field(..., description="GitHub action type")
    repository: str = Field(..., description="Repository name (owner/repo format)")
    auth_token: str = Field(..., description="GitHub access token")
    branch: Optional[str] = Field("main", description="Branch name")
    title: Optional[str] = Field(None, description="Title for issues or pull requests")
    body: Optional[str] = Field(None, description="Body content")
    issue_number: Optional[int] = Field(None, description="Issue or PR number")
    labels: Optional[List[str]] = Field(default_factory=list, description="Labels to apply")
    assignees: Optional[List[str]] = Field(default_factory=list, description="Assignees")
    milestone: Optional[int] = Field(None, description="Milestone number")


class SlackExternalActionParams(BaseModel):
    """Slack external action parameters model."""

    channel: str = Field(..., description="Channel ID or name")
    message: str = Field(..., description="Message content")
    bot_token: str = Field(..., description="Slack Bot token")
    attachments: Optional[List[Dict[str, Any]]] = Field(
        default_factory=list, description="Message attachments"
    )
    thread_ts: Optional[str] = Field(None, description="Thread timestamp for reply")
    username: Optional[str] = Field(None, description="Custom username")
    icon_emoji: Optional[str] = Field(None, description="Emoji icon")
    icon_url: Optional[str] = Field(None, description="URL icon")
    blocks: Optional[List[Dict[str, Any]]] = Field(
        default_factory=list, description="Slack Block Kit blocks"
    )


class EmailExternalActionParams(BaseModel):
    """Email external action parameters model."""

    to: List[str] = Field(..., description="Recipient email addresses")
    subject: str = Field(..., description="Email subject")
    body: str = Field(..., description="Email body content")
    smtp_server: str = Field(..., description="SMTP server hostname")
    port: Optional[int] = Field(587, description="SMTP server port")
    username: str = Field(..., description="SMTP username")
    password: str = Field(..., description="SMTP password")
    use_tls: Optional[bool] = Field(True, description="Use TLS encryption")
    cc: Optional[List[str]] = Field(default_factory=list, description="CC addresses")
    bcc: Optional[List[str]] = Field(default_factory=list, description="BCC addresses")
    content_type: Optional[str] = Field("text/html", description="Content type")
    attachments: Optional[List[Dict[str, Any]]] = Field(
        default_factory=list, description="Email attachments"
    )


class ExternalActionInputData(BaseModel):
    """Input data for external action nodes."""

    # Dynamic parameters from upstream nodes
    dynamic_properties: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Dynamic properties from input"
    )
    dynamic_content: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Dynamic content from input"
    )
    template_vars: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Template variables for substitution"
    )

    # Common dynamic fields
    dynamic_headers: Optional[Dict[str, str]] = Field(
        default_factory=dict, description="Dynamic HTTP headers"
    )
    dynamic_params: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Dynamic parameters"
    )
    payload: Optional[Dict[str, Any]] = Field(None, description="Dynamic payload data")
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Additional metadata"
    )


class ExternalActionOutputData(BaseModel):
    """Output data for external action nodes."""

    status: str = Field(..., description="Operation status")
    result: Dict[str, Any] = Field(..., description="Operation result")

    # Common response fields
    status_code: Optional[int] = Field(None, description="HTTP status code")
    headers: Optional[Dict[str, str]] = Field(None, description="Response headers")
    response_time: Optional[float] = Field(None, description="Response time in seconds")

    # Service-specific fields
    url: Optional[str] = Field(None, description="URL of created resource")
    id: Optional[str] = Field(None, description="ID of created/updated resource")
    message_id: Optional[str] = Field(None, description="Message ID for messaging services")
    timestamp: Optional[str] = Field(None, description="Operation timestamp")

    # Error handling
    error: Optional[str] = Field(None, description="Error message if operation failed")
    error_type: Optional[str] = Field(None, description="Error type classification")


# Export commonly used models
__all__ = [
    "NotionActionType",
    "NotionSearchFilter",
    "NotionPageContent",
    "NotionBlockOperation",
    "NotionDatabaseQuery",
    "NotionExternalActionParams",
    "NotionExternalActionResult",
    "GitHubActionType",
    "GitHubExternalActionParams",
    "SlackExternalActionParams",
    "EmailExternalActionParams",
    "ExternalActionInputData",
    "ExternalActionOutputData",
]
