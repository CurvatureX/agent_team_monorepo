"""
Tool node specifications.

This module defines specifications for TOOL_NODE subtypes that provide
various tool integrations like MCP tools, calendar, email, and HTTP operations.
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

# MCP Tool Node
GOOGLE_CALENDAR_MCP_TOOL_SPEC = NodeSpec(
    node_type="TOOL_NODE",
    subtype="TOOL_GOOGLE_CALENDAR_MCP",
    description="Manages calendar operations through MCP",
    parameters=[
        ParameterDef(
            name="tool_name",
            type=ParameterType.STRING,
            required=True,
            description="Name of the MCP tool to execute",
        ),
        ParameterDef(
            name="operation",
            type=ParameterType.STRING,
            required=True,
            description="Specific operation or method to call on the tool",
        ),
        ParameterDef(
            name="server_url",
            type=ParameterType.STRING,
            required=False,
            description="MCP server URL (uses default if not specified)",
        ),
        ParameterDef(
            name="timeout_seconds",
            type=ParameterType.INTEGER,
            required=False,
            default_value="30",
            description="Request timeout in seconds",
        ),
        ParameterDef(
            name="retry_attempts",
            type=ParameterType.INTEGER,
            required=False,
            default_value="3",
            description="Number of retry attempts on failure",
        ),
    ],
    input_ports=[
        InputPortSpec(
            name="main",
            type=ConnectionType.MAIN,
            required=True,
            description="Tool parameters and execution context",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"parameters": "object", "context": "object", "metadata": "object"}',
                examples=[
                    '{"parameters": {"query": "weather in NYC"}, "context": {"user_id": "123"}}',
                ],
            ),
        )
    ],
    output_ports=[
        OutputPortSpec(
            name="main",
            type=ConnectionType.MAIN,
            description="Tool execution result",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"result": "object", "tool_name": "string", "execution_time": "number", "metadata": "object"}',
            ),
        ),
        OutputPortSpec(
            name="error",
            type=ConnectionType.ERROR,
            description="Tool execution error",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"error": "string", "error_code": "string", "tool_name": "string", "retry_count": "number"}',
            ),
        ),
    ],
    examples=[
        {
            "name": "Weather Tool",
            "description": "Get weather information using MCP weather tool",
            "parameters": {
                "tool_name": "weather",
                "operation": "get_current",
            },
        }
    ],
)


# CALENDAR Tool Node
CALENDAR_TOOL_SPEC = NodeSpec(
    node_type="TOOL_NODE",
    subtype="CALENDAR",
    description="Perform calendar operations like listing, creating, or managing events",
    parameters=[
        ParameterDef(
            name="calendar_id",
            type=ParameterType.STRING,
            required=True,
            description="Calendar identifier or email address",
        ),
        ParameterDef(
            name="operation",
            type=ParameterType.ENUM,
            required=True,
            enum_values=["list_events", "create_event", "update_event", "delete_event"],
            description="Calendar operation to perform",
        ),
        ParameterDef(
            name="provider",
            type=ParameterType.ENUM,
            required=False,
            default_value="google",
            enum_values=["google", "outlook", "apple", "generic"],
            description="Calendar service provider",
        ),
        ParameterDef(
            name="timezone",
            type=ParameterType.STRING,
            required=False,
            default_value="UTC",
            description="Timezone for calendar operations",
        ),
    ],
    input_ports=[
        InputPortSpec(
            name="main",
            type=ConnectionType.MAIN,
            required=True,
            description="Calendar operation parameters",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"event_data": "object", "date_range": "object", "filters": "object"}',
                examples=[
                    '{"event_data": {"title": "Meeting", "start": "2025-01-30T10:00:00Z", "end": "2025-01-30T11:00:00Z"}}',
                    '{"date_range": {"start": "2025-01-30", "end": "2025-01-31"}, "filters": {"attendee": "user@example.com"}}',
                ],
            ),
        )
    ],
    output_ports=[
        OutputPortSpec(
            name="main",
            type=ConnectionType.MAIN,
            description="Calendar operation result",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"events": "array", "operation": "string", "calendar_id": "string", "count": "number"}',
            ),
        ),
        OutputPortSpec(
            name="error",
            type=ConnectionType.ERROR,
            description="Calendar operation error",
        ),
    ],
)


# EMAIL Tool Node
EMAIL_TOOL_SPEC = NodeSpec(
    node_type="TOOL_NODE",
    subtype="EMAIL",
    description="Perform email operations like sending, reading, searching, or managing emails",
    parameters=[
        ParameterDef(
            name="operation",
            type=ParameterType.ENUM,
            required=True,
            enum_values=["send", "read", "search", "delete"],
            description="Email operation to perform",
        ),
        ParameterDef(
            name="provider",
            type=ParameterType.ENUM,
            required=False,
            default_value="gmail",
            enum_values=["gmail", "outlook", "smtp", "imap"],
            description="Email service provider",
        ),
        ParameterDef(
            name="account",
            type=ParameterType.STRING,
            required=False,
            description="Email account identifier (uses default if not specified)",
        ),
        ParameterDef(
            name="folder",
            type=ParameterType.STRING,
            required=False,
            default_value="INBOX",
            description="Email folder for read/search operations",
        ),
    ],
    input_ports=[
        InputPortSpec(
            name="main",
            type=ConnectionType.MAIN,
            required=True,
            description="Email operation parameters",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"email_data": "object", "search_criteria": "object", "message_ids": "array"}',
                examples=[
                    '{"email_data": {"to": ["user@example.com"], "subject": "Test", "body": "Hello"}}',
                    '{"search_criteria": {"from": "sender@example.com", "subject_contains": "urgent"}}',
                ],
            ),
        )
    ],
    output_ports=[
        OutputPortSpec(
            name="main",
            type=ConnectionType.MAIN,
            description="Email operation result",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"emails": "array", "operation": "string", "count": "number", "status": "string"}',
            ),
        ),
        OutputPortSpec(
            name="error",
            type=ConnectionType.ERROR,
            description="Email operation error",
        ),
    ],
)


# HTTP Tool Node
HTTP_TOOL_SPEC = NodeSpec(
    node_type="TOOL_NODE",
    subtype="HTTP",
    description="Make HTTP requests to external APIs and services",
    parameters=[
        ParameterDef(
            name="method",
            type=ParameterType.ENUM,
            required=True,
            enum_values=["GET", "POST", "PUT", "DELETE", "PATCH"],
            description="HTTP method to use",
        ),
        ParameterDef(
            name="url",
            type=ParameterType.STRING,
            required=True,
            description="Target URL for the HTTP request",
        ),
        ParameterDef(
            name="headers",
            type=ParameterType.JSON,
            required=False,
            description="HTTP headers as key-value pairs",
        ),
        ParameterDef(
            name="timeout_seconds",
            type=ParameterType.INTEGER,
            required=False,
            default_value="30",
            description="Request timeout in seconds",
        ),
        ParameterDef(
            name="follow_redirects",
            type=ParameterType.BOOLEAN,
            required=False,
            default_value="true",
            description="Whether to follow HTTP redirects",
        ),
        ParameterDef(
            name="verify_ssl",
            type=ParameterType.BOOLEAN,
            required=False,
            default_value="true",
            description="Whether to verify SSL certificates",
        ),
    ],
    input_ports=[
        InputPortSpec(
            name="main",
            type=ConnectionType.MAIN,
            required=True,
            description="HTTP request data and parameters",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"body": "object", "query_params": "object", "auth": "object"}',
                examples=[
                    '{"body": {"key": "value"}, "query_params": {"page": 1}, "auth": {"type": "bearer", "token": "..."}}',
                ],
            ),
        )
    ],
    output_ports=[
        OutputPortSpec(
            name="main",
            type=ConnectionType.MAIN,
            description="HTTP response data",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"status_code": "number", "body": "object", "headers": "object", "url": "string", "response_time": "number"}',
            ),
        ),
        OutputPortSpec(
            name="error",
            type=ConnectionType.ERROR,
            description="HTTP request error",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"error": "string", "status_code": "number", "url": "string", "response_time": "number"}',
            ),
        ),
    ],
    examples=[
        {
            "name": "API Request",
            "description": "Make a GET request to retrieve data from an API",
            "parameters": {
                "method": "GET",
                "url": "https://api.example.com/data",
                "headers": {"Authorization": "Bearer token123"},
            },
        },
        {
            "name": "Webhook Call",
            "description": "Send data to a webhook endpoint",
            "parameters": {
                "method": "POST",
                "url": "https://webhook.example.com/endpoint",
            },
        },
    ],
)
