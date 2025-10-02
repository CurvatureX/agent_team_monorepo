"""
NOTION_MCP_TOOL Tool Node Specification

MCP tool for Notion integration capabilities.
This tool is attached to AI_AGENT nodes and provides Notion database
and page manipulation through the MCP protocol.

Note: TOOL nodes are attached to AI_AGENT nodes via attached_nodes,
not connected through input/output ports.
"""

from typing import Any, Dict, List

from ...models.node_enums import NodeType, ToolSubtype
from ..base import COMMON_CONFIGS, BaseNodeSpec


class NotionMCPToolSpec(BaseNodeSpec):
    """Notion MCP Tool specification for AI_AGENT attached functionality."""

    def __init__(self):
        super().__init__(
            type=NodeType.TOOL,
            subtype=ToolSubtype.NOTION_MCP_TOOL,
            name="Notion_MCP_Tool",
            description="Notion MCP tool for database and page operations through MCP protocol",
            # Configuration parameters
            configurations={
                "mcp_server_url": {
                    "type": "string",
                    "default": "http://localhost:8000/api/v1/mcp",
                    "description": "MCP服务器URL",
                    "required": True,
                },
                "notion_integration_token": {
                    "type": "string",
                    "default": "",
                    "description": "Notion集成令牌",
                    "required": True,
                    "sensitive": True,
                },
                "default_database_id": {
                    "type": "string",
                    "default": "",
                    "description": "默认数据库ID",
                    "required": False,
                },
                "available_tools": {
                    "type": "array",
                    "default": [
                        "notion_search",
                        "notion_create_page",
                        "notion_update_page",
                        "notion_get_page",
                        "notion_query_database",
                        "notion_create_database_item",
                    ],
                    "description": "可用的Notion工具列表",
                    "required": False,
                    "options": [
                        "notion_search",
                        "notion_create_page",
                        "notion_update_page",
                        "notion_get_page",
                        "notion_delete_page",
                        "notion_query_database",
                        "notion_create_database_item",
                        "notion_update_database_item",
                        "notion_get_database",
                        "notion_list_databases",
                    ],
                },
                "page_size_limit": {
                    "type": "integer",
                    "default": 100,
                    "min": 1,
                    "max": 1000,
                    "description": "页面大小限制",
                    "required": False,
                },
                "enable_rich_text": {
                    "type": "boolean",
                    "default": True,
                    "description": "是否启用富文本处理",
                    "required": False,
                },
                "auto_create_missing_props": {
                    "type": "boolean",
                    "default": False,
                    "description": "是否自动创建缺失的属性",
                    "required": False,
                },
                **COMMON_CONFIGS,
            },
            # Schema-style runtime parameters for tool execution
            input_params={
                "tool_name": {
                    "type": "string",
                    "default": "",
                    "description": "MCP tool function name to invoke",
                    "required": True,
                },
                "function_args": {
                    "type": "object",
                    "default": {},
                    "description": "Arguments for the selected tool function",
                    "required": False,
                },
                "context": {
                    "type": "object",
                    "default": {},
                    "description": "Optional context to pass along with the tool call",
                    "required": False,
                },
                "call_id": {
                    "type": "string",
                    "default": "",
                    "description": "Optional correlation ID for tracing",
                    "required": False,
                },
            },
            output_params={
                "result": {
                    "type": "object",
                    "default": {},
                    "description": "Result payload returned by the MCP tool",
                    "required": False,
                },
                "success": {
                    "type": "boolean",
                    "default": False,
                    "description": "Whether the MCP tool invocation succeeded",
                    "required": False,
                },
                "error_message": {
                    "type": "string",
                    "default": "",
                    "description": "Error details if invocation failed",
                    "required": False,
                },
                "execution_time": {
                    "type": "number",
                    "default": 0.0,
                    "description": "Execution time in seconds",
                    "required": False,
                },
                "cached": {
                    "type": "boolean",
                    "default": False,
                    "description": "Whether the result was served from cache",
                    "required": False,
                },
                "notion_object_id": {
                    "type": "string",
                    "default": "",
                    "description": "The Notion object ID created or retrieved",
                    "required": False,
                },
                "notion_object_type": {
                    "type": "string",
                    "default": "",
                    "description": "Type of the Notion object (page, database, etc.)",
                    "required": False,
                },
            },
            # TOOL nodes have no ports - they are attached to AI_AGENT nodes            # Tools don't have attached_nodes (only AI_AGENT has this)
            attached_nodes=None,
            # Metadata
            tags=["tool", "mcp", "notion", "database", "pages", "attached"],
            # Examples
            examples=[
                {
                    "name": "Search Notion Pages",
                    "description": "Search for pages and databases in Notion workspace",
                    "configurations": {
                        "mcp_server_url": "http://localhost:8000/api/v1/mcp",
                        "notion_integration_token": "secret_notion_token_123",
                        "available_tools": ["notion_search"],
                        "page_size_limit": 50,
                        "enable_rich_text": True,
                    },
                    "usage_example": {
                        "attached_to": "notion_assistant_ai",
                        "function_call": {
                            "tool_name": "notion_search",
                            "function_args": {
                                "integration_token": "secret_notion_token_123",
                                "query": "project management",
                                "filter": {"value": "page", "property": "object"},
                                "sort": {
                                    "direction": "descending",
                                    "timestamp": "last_edited_time",
                                },
                                "start_cursor": None,
                                "page_size": 20,
                            },
                            "context": {
                                "user_request": "Find all project management related pages"
                            },
                        },
                        "expected_result": {
                            "result": {
                                "results": [
                                    {
                                        "id": "page_123",
                                        "title": "Project Management Best Practices",
                                        "object": "page",
                                        "last_edited_time": "2025-01-20T10:30:00Z",
                                        "url": "https://notion.so/page_123",
                                    }
                                ],
                                "total_count": 15,
                                "has_more": True,
                                "next_cursor": "cursor_456",
                            },
                            "success": True,
                            "execution_time": 1.2,
                            "cached": False,
                            "notion_object_type": "search_results",
                        },
                    },
                },
                {
                    "name": "Create Notion Database Entry",
                    "description": "Create new items in Notion databases with properties",
                    "configurations": {
                        "mcp_server_url": "http://localhost:8000/api/v1/mcp",
                        "notion_integration_token": "secret_notion_token_456",
                        "default_database_id": "db_789",
                        "available_tools": ["notion_create_database_item"],
                        "auto_create_missing_props": True,
                    },
                    "usage_example": {
                        "attached_to": "task_management_ai",
                        "function_call": {
                            "tool_name": "notion_create_database_item",
                            "function_args": {
                                "integration_token": "secret_notion_token_456",
                                "database_id": "db_789",
                                "properties": {
                                    "Task Name": {
                                        "title": [
                                            {"text": {"content": "Implement user authentication"}}
                                        ]
                                    },
                                    "Status": {"select": {"name": "In Progress"}},
                                    "Priority": {"select": {"name": "High"}},
                                    "Due Date": {"date": {"start": "2025-01-25"}},
                                    "Assignee": {"people": [{"id": "user_123"}]},
                                },
                            },
                            "context": {"user_id": "user_123", "project": "web_app"},
                        },
                        "expected_result": {
                            "result": {
                                "id": "page_new_456",
                                "object": "page",
                                "parent": {"database_id": "db_789"},
                                "properties": {
                                    "Task Name": {
                                        "title": [
                                            {"text": {"content": "Implement user authentication"}}
                                        ]
                                    },
                                    "Status": {"select": {"name": "In Progress"}},
                                },
                                "url": "https://notion.so/page_new_456",
                            },
                            "success": True,
                            "execution_time": 0.8,
                            "notion_object_id": "page_new_456",
                            "notion_object_type": "page",
                        },
                    },
                },
                {
                    "name": "Query Notion Database",
                    "description": "Query database with filters and sorting options",
                    "configurations": {
                        "mcp_server_url": "http://localhost:8000/api/v1/mcp",
                        "notion_integration_token": "secret_notion_token_789",
                        "available_tools": ["notion_query_database"],
                        "page_size_limit": 25,
                    },
                    "usage_example": {
                        "attached_to": "analytics_ai",
                        "function_call": {
                            "tool_name": "notion_query_database",
                            "function_args": {
                                "integration_token": "secret_notion_token_789",
                                "database_id": "db_analytics_101",
                                "filter": {
                                    "and": [
                                        {"property": "Status", "select": {"equals": "Completed"}},
                                        {"property": "Priority", "select": {"equals": "High"}},
                                    ]
                                },
                                "sorts": [{"property": "Due Date", "direction": "descending"}],
                                "page_size": 25,
                            },
                            "context": {"report_type": "completed_high_priority_tasks"},
                        },
                        "expected_result": {
                            "result": {
                                "results": [
                                    {
                                        "id": "page_completed_1",
                                        "properties": {
                                            "Task Name": {
                                                "title": [
                                                    {"text": {"content": "Database optimization"}}
                                                ]
                                            },
                                            "Status": {"select": {"name": "Completed"}},
                                            "Priority": {"select": {"name": "High"}},
                                            "Due Date": {"date": {"start": "2025-01-18"}},
                                        },
                                    }
                                ],
                                "total_count": 12,
                                "has_more": False,
                            },
                            "success": True,
                            "execution_time": 1.1,
                            "notion_object_type": "database_query_results",
                        },
                    },
                },
            ],
        )


# Export the specification instance
NOTION_MCP_TOOL_SPEC = NotionMCPToolSpec()
