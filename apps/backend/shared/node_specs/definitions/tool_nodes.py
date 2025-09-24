"""
Tool node specifications.

This module defines specifications for TOOL_NODE subtypes that provide
various tool integrations like HTTP, code execution, and MCP tools.
"""

from ...models.node_enums import NodeType, ToolSubtype
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
    node_type=NodeType.TOOL,
    subtype=ToolSubtype.HTTP_CLIENT,
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
    node_type=NodeType.TOOL,
    subtype=ToolSubtype.CODE_TOOL,
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

# Generic MCP Tool Node - connects to MCP API Gateway
MCP_TOOL_SPEC = NodeSpec(
    node_type=NodeType.TOOL,
    subtype=ToolSubtype.MCP_TOOL.value if hasattr(ToolSubtype, "MCP_TOOL") else "MCP_TOOL",
    description="Generic MCP tool node that provides access to Model Context Protocol functions",
    display_name="MCP Tool",
    category="tools",
    template_id="tool_mcp",
    parameters=[
        ParameterDef(
            name="mcp_server_url",
            type=ParameterType.STRING,
            required=False,
            description="MCP server URL (defaults to API Gateway MCP endpoint)",
        ),
        ParameterDef(
            name="api_key",
            type=ParameterType.STRING,
            required=False,
            description="API key for MCP authentication (optional)",
        ),
        ParameterDef(
            name="tool_categories",
            type=ParameterType.JSON,
            required=False,
            default_value=[],
            description="Filter tools by categories (empty = all tools)",
        ),
        ParameterDef(
            name="timeout_seconds",
            type=ParameterType.INTEGER,
            required=False,
            default_value=30,
            description="MCP operation timeout",
        ),
    ],
    input_ports=[
        InputPortSpec(
            name="main",
            type=ConnectionType.MAIN,
            required=False,
            description="MCP tool execution parameters",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"tool_name": "string", "tool_args": "object", "operation": "string"}',
                examples=[
                    '{"operation": "discover"}',
                    '{"operation": "execute", "tool_name": "get_weather", "tool_args": {"location": "New York"}}',
                ],
            ),
        ),
        InputPortSpec(
            name="mcp_tools",
            type=ConnectionType.MCP_TOOLS,
            required=False,
            max_connections=-1,  # Allow multiple AI connections
            description="Receive function calls from connected AI nodes",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"operation": "string", "function_name": "string", "function_args": "object", "request_id": "string"}',
                examples=[
                    '{"operation": "discover", "request_id": "req_123"}',
                    '{"operation": "execute", "function_name": "get_weather", "function_args": {"location": "New York"}, "request_id": "req_124"}',
                ],
            ),
        ),
    ],
    output_ports=[
        OutputPortSpec(
            name="main",
            type=ConnectionType.MAIN,
            description="MCP tool execution result",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"result": "object", "tool_name": "string", "operation": "string", "execution_time": "number", "available_functions": "array"}',
                examples=[
                    '{"operation": "discover", "available_functions": [{"name": "get_weather", "description": "Get weather info"}], "execution_time": 0.1}',
                    '{"operation": "execute", "tool_name": "get_weather", "result": {"temperature": 25, "condition": "sunny"}, "execution_time": 1.2}',
                ],
            ),
        ),
        OutputPortSpec(
            name="error",
            type=ConnectionType.ERROR,
            description="MCP tool execution error",
        ),
    ],
    examples=[
        {
            "name": "Weather Tool Access",
            "description": "Connect AI agent to weather MCP tools",
            "parameters": {"tool_categories": ["weather", "location"]},
            "workflow_usage": "Connect AI node output 'mcp_tools' to this node's input 'mcp_tools'",
        },
        {
            "name": "General MCP Access",
            "description": "Provide access to all available MCP tools",
            "parameters": {},
            "workflow_usage": "Use for AI agents that need access to multiple tool categories",
        },
    ],
)

# Notion MCP Tool Node
NOTION_MCP_TOOL_SPEC = NodeSpec(
    node_type=NodeType.TOOL,
    subtype=ToolSubtype.MCP_TOOL,
    description="Access Notion workspace through MCP protocol for real-time TODO and content queries",
    display_name="Notion MCP Tool",
    category="tools",
    template_id="tool_notion_mcp",
    parameters=[
        ParameterDef(
            name="mcp_server_url",
            type=ParameterType.STRING,
            required=False,
            description="MCP server URL (defaults to API Gateway MCP endpoint)",
        ),
        ParameterDef(
            name="notion_integration_token",
            type=ParameterType.STRING,
            required=False,
            description="Notion integration token (handled via OAuth if not provided)",
        ),
        ParameterDef(
            name="default_database_ids",
            type=ParameterType.JSON,
            required=False,
            default_value={},
            description="Default database IDs for common operations (todo_db, weekly_plan_db, etc.)",
        ),
        ParameterDef(
            name="timeout_seconds",
            type=ParameterType.INTEGER,
            required=False,
            default_value=30,
            description="MCP operation timeout",
        ),
        ParameterDef(
            name="include_content",
            type=ParameterType.BOOLEAN,
            required=False,
            default_value=True,
            description="Include page content in search results for AI context",
        ),
    ],
    input_ports=[
        InputPortSpec(
            name="main",
            type=ConnectionType.MAIN,
            required=False,
            description="Direct MCP operation parameters",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"operation": "string", "tool_args": "object", "database_id": "string", "query": "string"}',
                examples=[
                    '{"operation": "query_database", "tool_args": {"database_id": "todo_db", "filter": {"property": "Status", "select": {"equals": "In Progress"}}}}',
                    '{"operation": "search", "tool_args": {"query": "weekly plan", "filter": {"property": "object_type", "value": "page"}}}',
                ],
            ),
        ),
        InputPortSpec(
            name="mcp_tools",
            type=ConnectionType.MCP_TOOLS,
            required=False,
            max_connections=-1,
            description="Receive function calls from connected AI nodes for real-time Notion queries",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"operation": "string", "function_name": "string", "function_args": "object", "request_id": "string"}',
                examples=[
                    '{"operation": "execute", "function_name": "notion_query_todos", "function_args": {"status": "In Progress", "priority": "High"}, "request_id": "req_125"}',
                    '{"operation": "execute", "function_name": "notion_get_weekly_plan", "function_args": {"week_start": "2025-01-27"}, "request_id": "req_126"}',
                ],
            ),
        ),
    ],
    output_ports=[
        OutputPortSpec(
            name="main",
            type=ConnectionType.MAIN,
            description="Notion MCP operation result with structured data",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"result": "object", "operation": "string", "execution_time": "number", "available_functions": "array", "context_summary": "string"}',
                examples=[
                    '{"operation": "query_database", "result": {"results": [{"properties": {"Name": {"title": [{"text": {"content": "Complete quarterly report"}}]}, "Status": {"select": {"name": "In Progress"}}, "Priority": {"select": {"name": "High"}}}}]}, "context_summary": "Found 1 high-priority in-progress task", "execution_time": 0.8}',
                    '{"operation": "search", "result": {"results": [{"properties": {"title": {"title": [{"text": {"content": "Weekly Plan - Week of Jan 27"}}]}}}]}, "context_summary": "Found current weekly plan document", "execution_time": 0.6}',
                ],
            ),
        ),
        OutputPortSpec(
            name="error",
            type=ConnectionType.ERROR,
            description="Notion MCP operation error",
        ),
    ],
    examples=[
        {
            "name": "AI Assistant TODO Access",
            "description": "Connect AI agent to real-time Notion TODO database queries",
            "parameters": {
                "default_database_ids": {
                    "todo_db": "your-todo-database-id",
                    "weekly_plan_db": "your-weekly-plan-database-id",
                },
                "include_content": True,
            },
            "workflow_usage": "Connect AI node output 'mcp_tools' to this node's input 'mcp_tools' for real-time TODO queries during conversations",
        },
        {
            "name": "Weekly Plan Monitoring",
            "description": "Enable AI to access and understand weekly planning documents",
            "parameters": {
                "default_database_ids": {"weekly_plan_db": "your-weekly-plan-database-id"},
                "timeout_seconds": 45,
            },
            "workflow_usage": "AI can query current week's plans to provide context-aware scheduling suggestions",
        },
    ],
)

# Google Calendar MCP Tool Node
GOOGLE_CALENDAR_MCP_TOOL_SPEC = NodeSpec(
    node_type=NodeType.TOOL,
    subtype=ToolSubtype.GOOGLE_CALENDAR,
    description="Access Google Calendar through MCP protocol for real-time schedule queries and availability checks",
    display_name="Google Calendar MCP Tool",
    category="tools",
    template_id="tool_google_calendar_mcp",
    parameters=[
        ParameterDef(
            name="mcp_server_url",
            type=ParameterType.STRING,
            required=False,
            description="MCP server URL (defaults to API Gateway MCP endpoint)",
        ),
        ParameterDef(
            name="access_token",
            type=ParameterType.STRING,
            required=True,
            description="Google Calendar OAuth access token (required for MCP authentication)",
        ),
        ParameterDef(
            name="calendar_id",
            type=ParameterType.STRING,
            required=False,
            default_value="primary",
            description="Default calendar ID to query",
        ),
        ParameterDef(
            name="default_time_range_days",
            type=ParameterType.INTEGER,
            required=False,
            default_value=14,
            description="Default number of days to look ahead for events",
        ),
        ParameterDef(
            name="include_declined_events",
            type=ParameterType.BOOLEAN,
            required=False,
            default_value=False,
            description="Include declined events in results",
        ),
        ParameterDef(
            name="timeout_seconds",
            type=ParameterType.INTEGER,
            required=False,
            default_value=30,
            description="MCP operation timeout",
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
            required=False,
            description="Direct calendar operation parameters",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"operation": "string", "tool_args": "object", "time_min": "string", "time_max": "string"}',
                examples=[
                    '{"operation": "list_events", "tool_args": {"calendar_id": "primary", "time_min": "2025-01-27T00:00:00Z", "time_max": "2025-02-03T23:59:59Z"}}',
                    '{"operation": "check_availability", "tool_args": {"start_time": "2025-01-30T14:00:00Z", "end_time": "2025-01-30T16:00:00Z"}}',
                ],
            ),
        ),
        InputPortSpec(
            name="mcp_tools",
            type=ConnectionType.MCP_TOOLS,
            required=False,
            max_connections=-1,
            description="Receive function calls from connected AI nodes for real-time calendar queries",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"operation": "string", "function_name": "string", "function_args": "object", "request_id": "string"}',
                examples=[
                    '{"operation": "execute", "function_name": "calendar_check_availability", "function_args": {"date": "2025-01-30", "duration_hours": 2}, "request_id": "req_127"}',
                    '{"operation": "execute", "function_name": "calendar_list_week_events", "function_args": {"week_start": "2025-01-27"}, "request_id": "req_128"}',
                ],
            ),
        ),
    ],
    output_ports=[
        OutputPortSpec(
            name="main",
            type=ConnectionType.MAIN,
            description="Google Calendar MCP operation result with schedule data",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"result": "object", "operation": "string", "execution_time": "number", "available_functions": "array", "schedule_summary": "string"}',
                examples=[
                    '{"operation": "list_events", "result": {"items": [{"summary": "Team Meeting", "start": {"dateTime": "2025-01-30T10:00:00Z"}, "end": {"dateTime": "2025-01-30T11:00:00Z"}}]}, "schedule_summary": "Found 3 events this week", "execution_time": 0.9}',
                    '{"operation": "check_availability", "result": {"available": true, "conflicting_events": [], "suggested_times": ["2025-01-30T14:00:00Z", "2025-01-30T15:30:00Z"]}, "schedule_summary": "Time slot available with no conflicts", "execution_time": 0.5}',
                ],
            ),
        ),
        OutputPortSpec(
            name="error",
            type=ConnectionType.ERROR,
            description="Google Calendar MCP operation error",
        ),
    ],
    examples=[
        {
            "name": "AI Assistant Calendar Access",
            "description": "Connect AI agent to real-time Google Calendar queries for intelligent scheduling",
            "parameters": {
                "calendar_id": "primary",
                "default_time_range_days": 14,
                "include_declined_events": False,
            },
            "workflow_usage": "Connect AI node output 'mcp_tools' to this node's input 'mcp_tools' for real-time availability checks during conversations",
        },
        {
            "name": "Weekly Schedule Overview",
            "description": "Enable AI to understand current and upcoming week schedules",
            "parameters": {"default_time_range_days": 7, "timezone": "America/New_York"},
            "workflow_usage": "AI can provide weekly schedule summaries and identify optimal meeting times",
        },
    ],
)

# Code Interpreter Tool - sandboxed code execution
CODE_INTERPRETER_SPEC = NodeSpec(
    node_type=NodeType.TOOL,
    subtype=ToolSubtype.CODE_TOOL,
    description="Execute Python code in sandboxed environment",
    display_name="Code Interpreter",
    category="tools",
    template_id="tool_code_interpreter",
    parameters=[
        ParameterDef(
            name="code",
            type=ParameterType.STRING,
            required=True,
            description="Python code to execute",
        ),
        ParameterDef(
            name="timeout_seconds",
            type=ParameterType.INTEGER,
            required=False,
            default_value=30,
            description="Execution timeout",
        ),
        ParameterDef(
            name="allowed_imports",
            type=ParameterType.JSON,
            required=False,
            default_value=["numpy", "pandas", "matplotlib", "requests", "json"],
            description="Allowed Python imports",
        ),
        ParameterDef(
            name="max_memory_mb",
            type=ParameterType.INTEGER,
            required=False,
            default_value=512,
            description="Maximum memory usage in MB",
        ),
    ],
    input_ports=[
        InputPortSpec(
            name="main",
            type=ConnectionType.MAIN,
            required=False,
            description="Input data and variables for code",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"variables": "object", "files": "object", "context": "object"}',
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
                schema='{"output": "string", "result": "object", "stdout": "string", "stderr": "string", "execution_time": "number"}',
            ),
        ),
        OutputPortSpec(
            name="error",
            type=ConnectionType.ERROR,
            description="Code execution error",
        ),
    ],
)

# Web Scraper Tool - extract data from web pages
WEB_SCRAPER_SPEC = NodeSpec(
    node_type=NodeType.TOOL,
    subtype="WEB_SCRAPER",  # Using string as it might not be in enum yet
    description="Extract data from web pages",
    display_name="Web Scraper",
    category="tools",
    template_id="tool_web_scraper",
    parameters=[
        ParameterDef(
            name="url",
            type=ParameterType.URL,
            required=True,
            description="URL to scrape",
        ),
        ParameterDef(
            name="selector",
            type=ParameterType.STRING,
            required=False,
            description="CSS selector to extract specific content",
        ),
        ParameterDef(
            name="extract_type",
            type=ParameterType.ENUM,
            required=False,
            default_value="text",
            enum_values=["text", "html", "links", "images", "tables"],
            description="Type of content to extract",
        ),
        ParameterDef(
            name="follow_links",
            type=ParameterType.BOOLEAN,
            required=False,
            default_value=False,
            description="Follow and scrape linked pages",
        ),
        ParameterDef(
            name="max_pages",
            type=ParameterType.INTEGER,
            required=False,
            default_value=1,
            description="Maximum number of pages to scrape",
        ),
        ParameterDef(
            name="wait_seconds",
            type=ParameterType.INTEGER,
            required=False,
            default_value=2,
            description="Wait time between requests",
        ),
    ],
    input_ports=[
        InputPortSpec(
            name="main",
            type=ConnectionType.MAIN,
            required=False,
            description="Additional scraping configuration",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"headers": "object", "cookies": "object", "filters": "array"}',
            ),
        )
    ],
    output_ports=[
        OutputPortSpec(
            name="main",
            type=ConnectionType.MAIN,
            description="Scraped data",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"content": "string", "data": "array", "metadata": "object", "url": "string"}',
            ),
        ),
        OutputPortSpec(
            name="error",
            type=ConnectionType.ERROR,
            description="Scraping error",
        ),
    ],
)
