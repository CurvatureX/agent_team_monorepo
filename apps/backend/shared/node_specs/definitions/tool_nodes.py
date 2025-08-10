"""
Tool node specifications.

This module defines specifications for TOOL_NODE subtypes that provide
various tool integrations like HTTP, code execution, and MCP tools.
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

# HTTP Tool Node
HTTP_TOOL_SPEC = NodeSpec(
    node_type="TOOL",
    subtype="TOOL_HTTP",
    description="HTTP request tool",
    parameters=[
        ParameterDef(
            name="method",
            type=ParameterType.ENUM,
            required=True,
            enum_values=["GET", "POST", "PUT", "DELETE", "PATCH"],
            description="HTTP method",
        ),
        ParameterDef(
            name="url",
            type=ParameterType.URL,
            required=True,
            description="Target URL",
        ),
        ParameterDef(
            name="headers",
            type=ParameterType.JSON,
            required=False,
            default_value={},
            description="HTTP headers",
        ),
        ParameterDef(
            name="timeout_seconds",
            type=ParameterType.INTEGER,
            required=False,
            default_value=30,
            description="Timeout time",
        ),
        ParameterDef(
            name="follow_redirects",
            type=ParameterType.BOOLEAN,
            required=False,
            default_value=True,
            description="Whether to follow redirects",
        ),
        ParameterDef(
            name="verify_ssl",
            type=ParameterType.BOOLEAN,
            required=False,
            default_value=True,
            description="Whether to verify SSL certificate",
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
                    '{"body": {"key": "value"}, "query_params": {"page": 1}, "auth": {"type": "bearer", "token": "..."}}'
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
                schema='{"status_code": "number", "body": "object", "headers": "object", "response_time": "number"}',
                examples=[
                    '{"status_code": 200, "body": {"result": "success"}, "headers": {"content-type": "application/json"}, "response_time": 0.25}'
                ],
            ),
        ),
        OutputPortSpec(
            name="error",
            type=ConnectionType.ERROR,
            description="HTTP request error",
        ),
    ],
)

# Code Execution Tool Node
CODE_EXECUTION_TOOL_SPEC = NodeSpec(
    node_type="TOOL",
    subtype="TOOL_CODE_EXECUTION",
    description="Safe code execution environment",
    parameters=[
        ParameterDef(
            name="language",
            type=ParameterType.ENUM,
            required=True,
            enum_values=["python", "javascript", "bash"],
            description="Language",
        ),
        ParameterDef(
            name="code",
            type=ParameterType.STRING,
            required=True,
            description="Code to execute",
        ),
        ParameterDef(
            name="packages",
            type=ParameterType.JSON,
            required=False,
            default_value=[],
            description="Required packages/libraries",
        ),
        ParameterDef(
            name="timeout_seconds",
            type=ParameterType.INTEGER,
            required=False,
            default_value=30,
            description="Execution timeout",
        ),
        ParameterDef(
            name="memory_limit_mb",
            type=ParameterType.INTEGER,
            required=False,
            default_value=512,
            description="Memory limit (MB)",
        ),
    ],
    input_ports=[
        InputPortSpec(
            name="main",
            type=ConnectionType.MAIN,
            required=True,
            description="Code execution parameters",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"variables": "object", "stdin": "string"}',
                examples=['{"variables": {"x": 10, "y": 20}, "stdin": "input data"}'],
            ),
        )
    ],
    output_ports=[
        OutputPortSpec(
            name="main",
            type=ConnectionType.MAIN,
            description="Code execution result",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"stdout": "string", "stderr": "string", "return_code": "number", "result": "object", "execution_time": "number"}',
                examples=[
                    '{"stdout": "Hello World", "stderr": "", "return_code": 0, "result": {"output": 30}, "execution_time": 0.5}'
                ],
            ),
        ),
        OutputPortSpec(
            name="error",
            type=ConnectionType.ERROR,
            description="Code execution error",
        ),
    ],
)

# Google Calendar MCP Tool Node
GOOGLE_CALENDAR_MCP_TOOL_SPEC = NodeSpec(
    node_type="TOOL",
    subtype="TOOL_GOOGLE_CALENDAR_MCP",
    description="Access Google Calendar through MCP protocol",
    parameters=[
        ParameterDef(
            name="tool_name",
            type=ParameterType.STRING,
            required=True,
            description="MCP tool name",
        ),
        ParameterDef(
            name="operation",
            type=ParameterType.STRING,
            required=True,
            description="Specific operation or method",
        ),
        ParameterDef(
            name="parameters",
            type=ParameterType.JSON,
            required=False,
            default_value={},
            description="Operation parameters",
        ),
        ParameterDef(
            name="server_url",
            type=ParameterType.STRING,
            required=False,
            description="MCP server URL",
        ),
        ParameterDef(
            name="timeout_seconds",
            type=ParameterType.INTEGER,
            required=False,
            default_value=30,
            description="Timeout time",
        ),
        ParameterDef(
            name="retry_attempts",
            type=ParameterType.INTEGER,
            required=False,
            default_value=3,
            description="Retry count",
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
                schema='{"tool_params": "object", "context": "object"}',
                examples=[
                    '{"tool_params": {"calendar_id": "primary", "event_id": "123"}, "context": {"user_id": "user123"}}'
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
                schema='{"result": "object", "tool_name": "string", "operation": "string", "execution_time": "number"}',
                examples=[
                    '{"result": {"events": []}, "tool_name": "google_calendar", "operation": "list_events", "execution_time": 1.2}'
                ],
            ),
        ),
        OutputPortSpec(
            name="error",
            type=ConnectionType.ERROR,
            description="Tool execution error",
        ),
    ],
)
