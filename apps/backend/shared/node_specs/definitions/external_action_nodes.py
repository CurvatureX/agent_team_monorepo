"""
External action node specifications.

This module defines specifications for all EXTERNAL_ACTION_NODE subtypes including
GitHub, Email, Slack, and API call integrations.
"""

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
    node_type="EXTERNAL_ACTION_NODE",
    subtype="GITHUB",
    description="Execute GitHub operations via GitHub API",
    parameters=[
        ParameterDef(
            name="action",
            type=ParameterType.STRING,
            required=True,
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
            description="Branch name",
        ),
        ParameterDef(
            name="title",
            type=ParameterType.STRING,
            required=False,
            description="Title (issues or PR)",
        ),
        ParameterDef(
            name="body",
            type=ParameterType.STRING,
            required=False,
            description="Content (issues or PR)",
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
    node_type="EXTERNAL_ACTION_NODE",
    subtype="EMAIL",
    description="Send emails through various providers",
    parameters=[
        ParameterDef(
            name="to",
            type=ParameterType.JSON,
            required=True,
            description="Recipient list",
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
            description="Email body",
        ),
        ParameterDef(
            name="cc",
            type=ParameterType.JSON,
            required=False,
            default_value=[],
            description="CC list",
        ),
        ParameterDef(
            name="bcc",
            type=ParameterType.JSON,
            required=False,
            default_value=[],
            description="BCC list",
        ),
        ParameterDef(
            name="attachments",
            type=ParameterType.JSON,
            required=False,
            default_value=[],
            description="Attachment list",
        ),
        ParameterDef(
            name="html_body",
            type=ParameterType.BOOLEAN,
            required=False,
            default_value=False,
            description="Whether body is HTML format",
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
    node_type="EXTERNAL_ACTION_NODE",
    subtype="SLACK",
    description="Send messages and interact with Slack",
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
            description="Thread timestamp",
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

# API Call - generic API calls
API_CALL_SPEC = NodeSpec(
    node_type="EXTERNAL_ACTION_NODE",
    subtype="API_CALL",
    description="Make generic HTTP API calls",
    parameters=[
        ParameterDef(
            name="method",
            type=ParameterType.ENUM,
            required=True,
            default_value="GET",
            enum_values=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"],
            description="HTTP method",
        ),
        ParameterDef(
            name="url",
            type=ParameterType.URL,
            required=True,
            description="API endpoint URL",
        ),
        ParameterDef(
            name="headers",
            type=ParameterType.JSON,
            required=False,
            default_value={},
            description="HTTP headers",
        ),
        ParameterDef(
            name="query_params",
            type=ParameterType.JSON,
            required=False,
            default_value={},
            description="Query parameters",
        ),
        ParameterDef(
            name="body",
            type=ParameterType.JSON,
            required=False,
            description="Request body data",
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
    ],
    input_ports=[
        InputPortSpec(
            name="main",
            type=ConnectionType.MAIN,
            required=False,
            description="Dynamic API request data",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"dynamic_params": "object", "dynamic_headers": "object"}',
                examples=[
                    '{"dynamic_params": {"user_id": "123"}, "dynamic_headers": {"X-Custom": "value"}}'
                ],
            ),
        )
    ],
    output_ports=[
        OutputPortSpec(
            name="main",
            type=ConnectionType.MAIN,
            description="API response",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"status_code": "number", "headers": "object", "body": "object", "response_time": "number"}',
                examples=[
                    '{"status_code": 200, "headers": {"content-type": "application/json"}, "body": {"result": "success"}, "response_time": 0.25}'
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
