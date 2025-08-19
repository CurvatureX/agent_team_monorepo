"""
External action node specifications.

This module defines specifications for all EXTERNAL_ACTION_NODE subtypes including
GitHub, Email, Slack, and API call integrations.
"""

from ...models.node_enums import ExternalActionSubtype, NodeType
from ..base import (
    ConnectionType,
    DataFormat,
    InputPortSpec,
    NodeSpec,
    OutputPortSpec,
    ParameterDef,
    ParameterType,
)

# GitHub - GitHub operations
GITHUB_SPEC = NodeSpec(
    node_type=NodeType.EXTERNAL_ACTION,
    subtype=ExternalActionSubtype.GITHUB,
    description="Execute GitHub operations via GitHub API",
    display_name="GitHub Integration",
    category="integrations",
    template_id="external_github",
    parameters=[
        ParameterDef(
            name="action",
            type=ParameterType.ENUM,
            required=True,
            enum_values=[
                "create_issue",
                "create_pull_request",
                "add_comment",
                "close_issue",
                "merge_pr",
                "list_issues",
                "get_issue",
            ],
            description="GitHub action type",
        ),
        ParameterDef(
            name="repository",
            type=ParameterType.STRING,
            required=True,
            description="Repository name (owner/repo format)",
        ),
        ParameterDef(
            name="auth_token",
            type=ParameterType.STRING,
            required=True,
            description="GitHub access token (sensitive)",
        ),
        ParameterDef(
            name="branch",
            type=ParameterType.STRING,
            required=False,
            default_value="main",
            description="Branch name",
        ),
        ParameterDef(
            name="title",
            type=ParameterType.STRING,
            required=False,
            description="Title for issues or pull requests",
        ),
        ParameterDef(
            name="body",
            type=ParameterType.STRING,
            required=False,
            description="Body content for issues or pull requests",
        ),
        ParameterDef(
            name="issue_number",
            type=ParameterType.INTEGER,
            required=False,
            description="Issue or PR number for operations",
        ),
        ParameterDef(
            name="labels",
            type=ParameterType.JSON,
            required=False,
            default_value=[],
            description="Labels to apply (array of strings)",
        ),
        ParameterDef(
            name="assignees",
            type=ParameterType.JSON,
            required=False,
            default_value=[],
            description="Assignees (array of usernames)",
        ),
        ParameterDef(
            name="milestone",
            type=ParameterType.INTEGER,
            required=False,
            description="Milestone number",
        ),
    ],
    input_ports=[
        InputPortSpec(
            name="main",
            type=ConnectionType.MAIN,
            required=False,
            description="GitHub operation parameters",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"action_params": "object", "metadata": "object"}',
                examples=[
                    '{"action_params": {"labels": ["bug", "urgent"]}, "metadata": {"assignees": ["user1"]}}'
                ],
            ),
        )
    ],
    output_ports=[
        OutputPortSpec(
            name="main",
            type=ConnectionType.MAIN,
            description="GitHub operation result",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"result": "object", "status": "string", "url": "string"}',
                examples=[
                    '{"result": {"id": 123, "number": 456}, "status": "created", "url": "https://github.com/owner/repo/issues/456"}'
                ],
            ),
        ),
        OutputPortSpec(
            name="error",
            type=ConnectionType.ERROR,
            description="Error output when GitHub operation fails",
        ),
    ],
)

# Email - email operations
EMAIL_SPEC = NodeSpec(
    node_type=NodeType.EXTERNAL_ACTION,
    subtype=ExternalActionSubtype.EMAIL,
    description="Send emails via SMTP server",
    display_name="Email SMTP",
    category="integrations",
    template_id="external_email_smtp",
    parameters=[
        ParameterDef(
            name="to",
            type=ParameterType.JSON,
            required=True,
            description="Recipient email addresses (array of strings)",
        ),
        ParameterDef(
            name="subject",
            type=ParameterType.STRING,
            required=True,
            description="Email subject",
        ),
        ParameterDef(
            name="body",
            type=ParameterType.STRING,
            required=True,
            description="Email body content",
        ),
        ParameterDef(
            name="smtp_server",
            type=ParameterType.STRING,
            required=True,
            description="SMTP server hostname",
        ),
        ParameterDef(
            name="port",
            type=ParameterType.INTEGER,
            required=False,
            default_value=587,
            description="SMTP server port",
        ),
        ParameterDef(
            name="username",
            type=ParameterType.STRING,
            required=True,
            description="SMTP username",
        ),
        ParameterDef(
            name="password",
            type=ParameterType.STRING,
            required=True,
            description="SMTP password (sensitive)",
        ),
        ParameterDef(
            name="use_tls",
            type=ParameterType.BOOLEAN,
            required=False,
            default_value=True,
            description="Use TLS encryption",
        ),
        ParameterDef(
            name="cc",
            type=ParameterType.JSON,
            required=False,
            default_value=[],
            description="CC email addresses (array of strings)",
        ),
        ParameterDef(
            name="bcc",
            type=ParameterType.JSON,
            required=False,
            default_value=[],
            description="BCC email addresses (array of strings)",
        ),
        ParameterDef(
            name="content_type",
            type=ParameterType.ENUM,
            required=False,
            default_value="text/html",
            enum_values=["text/plain", "text/html"],
            description="Email content type",
        ),
        ParameterDef(
            name="attachments",
            type=ParameterType.JSON,
            required=False,
            default_value=[],
            description="Email attachments (array of file objects)",
        ),
    ],
    input_ports=[
        InputPortSpec(
            name="main",
            type=ConnectionType.MAIN,
            required=False,
            description="Email data and template variables",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"template_vars": "object", "attachments": "array"}',
                examples=[
                    '{"template_vars": {"name": "John", "order_id": "12345"}, "attachments": []}'
                ],
            ),
        )
    ],
    output_ports=[
        OutputPortSpec(
            name="main",
            type=ConnectionType.MAIN,
            description="Email send result",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"message_id": "string", "status": "string", "timestamp": "string"}',
                examples=[
                    '{"message_id": "msg_123", "status": "sent", "timestamp": "2025-01-28T10:30:00Z"}'
                ],
            ),
        ),
        OutputPortSpec(
            name="error",
            type=ConnectionType.ERROR,
            description="Error output when email send fails",
        ),
    ],
)

# Slack - Slack operations
SLACK_SPEC = NodeSpec(
    node_type=NodeType.EXTERNAL_ACTION,
    subtype=ExternalActionSubtype.SLACK,
    description="Send messages and interact with Slack",
    display_name="Slack Integration",
    category="integrations",
    template_id="external_slack",
    parameters=[
        ParameterDef(
            name="channel",
            type=ParameterType.STRING,
            required=True,
            description="Channel ID or name",
        ),
        ParameterDef(
            name="message",
            type=ParameterType.STRING,
            required=True,
            description="Message content",
        ),
        ParameterDef(
            name="bot_token",
            type=ParameterType.STRING,
            required=True,
            description="Slack Bot token (sensitive)",
        ),
        ParameterDef(
            name="attachments",
            type=ParameterType.JSON,
            required=False,
            default_value=[],
            description="Message attachments",
        ),
        ParameterDef(
            name="thread_ts",
            type=ParameterType.STRING,
            required=False,
            description="Thread timestamp for reply",
        ),
        ParameterDef(
            name="username",
            type=ParameterType.STRING,
            required=False,
            description="Custom username for bot message",
        ),
        ParameterDef(
            name="icon_emoji",
            type=ParameterType.STRING,
            required=False,
            description="Emoji icon for bot message",
        ),
        ParameterDef(
            name="icon_url",
            type=ParameterType.STRING,
            required=False,
            description="URL icon for bot message",
        ),
        ParameterDef(
            name="blocks",
            type=ParameterType.JSON,
            required=False,
            default_value=[],
            description="Slack Block Kit blocks",
        ),
    ],
    input_ports=[
        InputPortSpec(
            name="main",
            type=ConnectionType.MAIN,
            required=False,
            description="Dynamic message content and formatting",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"blocks": "array", "mentions": "array", "metadata": "object"}',
                examples=[
                    '{"blocks": [{"type": "section", "text": {"type": "mrkdwn", "text": "Hello!"}}], "mentions": ["@user123"], "metadata": {}}'
                ],
            ),
        )
    ],
    output_ports=[
        OutputPortSpec(
            name="main",
            type=ConnectionType.MAIN,
            description="Slack message result",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"ts": "string", "channel": "string", "message": "object"}',
                examples=[
                    '{"ts": "1234567890.123456", "channel": "C123456", "message": {"text": "Hello!"}}'
                ],
            ),
        ),
        OutputPortSpec(
            name="error",
            type=ConnectionType.ERROR,
            description="Error output when Slack operation fails",
        ),
    ],
)

# Notion - Notion workspace operations
NOTION_SPEC = NodeSpec(
    node_type=NodeType.EXTERNAL_ACTION,
    subtype=ExternalActionSubtype.NOTION,
    description="Search Notion content, create and update pages with rich blocks, query databases with advanced filtering, and manage workspace content using Notion API directly",
    display_name="Notion Workspace",
    category="productivity",
    template_id="external_notion",
    parameters=[
        ParameterDef(
            name="action_type",
            type=ParameterType.ENUM,
            required=True,
            enum_values=[
                "search",
                "page_get",
                "page_create",
                "page_update",
                "database_get",
                "database_query",
            ],
            description="Notion operation type",
        ),
        ParameterDef(
            name="access_token",
            type=ParameterType.STRING,
            required=True,
            description="Notion integration access token (sensitive)",
        ),
        ParameterDef(
            name="query",
            type=ParameterType.STRING,
            required=False,
            description="Search query text (for search operations)",
        ),
        ParameterDef(
            name="page_id",
            type=ParameterType.STRING,
            required=False,
            description="Notion page ID (for page operations)",
        ),
        ParameterDef(
            name="database_id",
            type=ParameterType.STRING,
            required=False,
            description="Notion database ID (for database operations)",
        ),
        ParameterDef(
            name="parent_id",
            type=ParameterType.STRING,
            required=False,
            description="Parent page/database ID (for page creation)",
        ),
        ParameterDef(
            name="parent_type",
            type=ParameterType.ENUM,
            required=False,
            default_value="page",
            enum_values=["page", "database"],
            description="Type of parent for page creation",
        ),
        ParameterDef(
            name="properties",
            type=ParameterType.JSON,
            required=False,
            default_value={},
            description="Page properties (title, status, tags, etc.)",
        ),
        ParameterDef(
            name="content",
            type=ParameterType.JSON,
            required=False,
            default_value={},
            description="Page content configuration (blocks and mode)",
        ),
        ParameterDef(
            name="block_operations",
            type=ParameterType.JSON,
            required=False,
            default_value=[],
            description="Advanced block operations for precise page editing",
        ),
        ParameterDef(
            name="search_filter",
            type=ParameterType.JSON,
            required=False,
            default_value={},
            description="Search filtering options (object_type, property, value)",
        ),
        ParameterDef(
            name="database_query",
            type=ParameterType.JSON,
            required=False,
            default_value={},
            description="Database query configuration (filter, sorts, limit)",
        ),
        ParameterDef(
            name="include_content",
            type=ParameterType.BOOLEAN,
            required=False,
            default_value=False,
            description="Include page/block content in results",
        ),
        ParameterDef(
            name="limit",
            type=ParameterType.INTEGER,
            required=False,
            default_value=10,
            description="Maximum results to return (1-100)",
        ),
    ],
    input_ports=[
        InputPortSpec(
            name="main",
            type=ConnectionType.MAIN,
            required=False,
            description="Dynamic Notion operation data and parameters",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"dynamic_properties": "object", "dynamic_content": "object", "template_vars": "object"}',
                examples=[
                    '{"dynamic_properties": {"Name": {"title": [{"text": {"content": "Generated Title"}}]}}, "dynamic_content": {"blocks": [...]}, "template_vars": {"user_name": "John"}}'
                ],
            ),
        )
    ],
    output_ports=[
        OutputPortSpec(
            name="main",
            type=ConnectionType.MAIN,
            description="Notion operation result",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"action": "string", "result": "object", "status": "string", "operations_performed": "array"}',
                examples=[
                    '{"action": "page_create", "result": {"id": "page-123", "url": "https://notion.so/page-123"}, "status": "success", "operations_performed": ["created_page"]}'
                ],
            ),
        ),
        OutputPortSpec(
            name="error",
            type=ConnectionType.ERROR,
            description="Error output when Notion operation fails",
        ),
    ],
)

# Google Calendar - Google Calendar operations
GOOGLE_CALENDAR_SPEC = NodeSpec(
    node_type=NodeType.EXTERNAL_ACTION,
    subtype="GOOGLE_CALENDAR",
    description="Interact with Google Calendar API",
    display_name="Google Calendar",
    category="integrations",
    template_id="external_google_calendar",
    parameters=[
        ParameterDef(
            name="action",
            type=ParameterType.ENUM,
            required=True,
            enum_values=[
                "list_events",
                "create_event",
                "update_event",
                "delete_event",
                "get_event",
            ],
            description="Google Calendar action type",
        ),
        ParameterDef(
            name="calendar_id",
            type=ParameterType.STRING,
            required=False,
            default_value="primary",
            description="Calendar ID",
        ),
        ParameterDef(
            name="summary",
            type=ParameterType.STRING,
            required=False,
            description="Event title/summary",
        ),
        ParameterDef(
            name="description",
            type=ParameterType.STRING,
            required=False,
            description="Event description",
        ),
        ParameterDef(
            name="location",
            type=ParameterType.STRING,
            required=False,
            description="Event location",
        ),
        ParameterDef(
            name="start_datetime",
            type=ParameterType.STRING,
            required=False,
            description="Event start datetime (ISO format)",
        ),
        ParameterDef(
            name="end_datetime",
            type=ParameterType.STRING,
            required=False,
            description="Event end datetime (ISO format)",
        ),
        ParameterDef(
            name="event_id",
            type=ParameterType.STRING,
            required=False,
            description="Event ID for update/delete operations",
        ),
        ParameterDef(
            name="max_results",
            type=ParameterType.STRING,
            required=False,
            default_value="10",
            description="Maximum number of events to return",
        ),
    ],
    input_ports=[
        InputPortSpec(
            name="main",
            type=ConnectionType.MAIN,
            required=False,
            description="Dynamic calendar event data",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"event_data": "object", "filter_params": "object"}',
                examples=[
                    '{"event_data": {"attendees": ["user@example.com"]}, "filter_params": {"time_min": "2025-01-01T00:00:00Z"}}'
                ],
            ),
        )
    ],
    output_ports=[
        OutputPortSpec(
            name="main",
            type=ConnectionType.MAIN,
            description="Google Calendar operation result",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"success": "boolean", "event": "object", "events": "array", "event_id": "string"}',
                examples=[
                    '{"success": true, "event": {"id": "event123", "summary": "Meeting"}, "event_id": "event123"}'
                ],
            ),
        ),
        OutputPortSpec(
            name="error",
            type=ConnectionType.ERROR,
            description="Error output when Google Calendar operation fails",
        ),
    ],
)

# Generic API Call - flexible HTTP API integration
API_CALL_SPEC = NodeSpec(
    node_type=NodeType.EXTERNAL_ACTION,
    subtype=ExternalActionSubtype.API_CALL,
    description="Make generic HTTP API calls to any endpoint",
    display_name="Generic API Call",
    category="integrations",
    template_id="external_api_call_generic",
    parameters=[
        ParameterDef(
            name="url",
            type=ParameterType.URL,
            required=True,
            description="API endpoint URL",
        ),
        ParameterDef(
            name="method",
            type=ParameterType.ENUM,
            required=True,
            default_value="GET",
            enum_values=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"],
            description="HTTP method",
        ),
        ParameterDef(
            name="headers",
            type=ParameterType.JSON,
            required=False,
            default_value={},
            description="HTTP headers",
        ),
        ParameterDef(
            name="body",
            type=ParameterType.JSON,
            required=False,
            description="Request body data",
        ),
        ParameterDef(
            name="query_params",
            type=ParameterType.JSON,
            required=False,
            default_value={},
            description="Query parameters",
        ),
        ParameterDef(
            name="timeout",
            type=ParameterType.INTEGER,
            required=False,
            default_value=30,
            description="Timeout in seconds",
        ),
        ParameterDef(
            name="authentication",
            type=ParameterType.ENUM,
            required=False,
            default_value="none",
            enum_values=["none", "bearer", "basic", "api_key"],
            description="Authentication method",
        ),
        ParameterDef(
            name="auth_token",
            type=ParameterType.STRING,
            required=False,
            description="Authentication token (when needed)",
        ),
        ParameterDef(
            name="api_key_header",
            type=ParameterType.STRING,
            required=False,
            description="API key header name (for api_key auth)",
        ),
    ],
    input_ports=[
        InputPortSpec(
            name="main",
            type=ConnectionType.MAIN,
            required=False,
            description="Dynamic API call data",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"dynamic_headers": "object", "dynamic_params": "object", "payload": "object"}',
                examples=[
                    '{"dynamic_headers": {"X-Custom": "value"}, "dynamic_params": {"filter": "active"}, "payload": {"data": "value"}}'
                ],
            ),
        )
    ],
    output_ports=[
        OutputPortSpec(
            name="main",
            type=ConnectionType.MAIN,
            description="API response data",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"status_code": "number", "headers": "object", "body": "object", "response_time": "number"}',
                examples=[
                    '{"status_code": 200, "headers": {"Content-Type": "application/json"}, "body": {"result": "success"}, "response_time": 1.2}'
                ],
            ),
        ),
        OutputPortSpec(
            name="error",
            type=ConnectionType.ERROR,
            description="Error output when API call fails",
        ),
    ],
)
