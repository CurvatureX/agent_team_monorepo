"""
NOTION_MCP_TOOL Tool Node Specification

Ultra-simple Notion MCP tool designed for maximum AI usability.
This tool is attached to AI_AGENT nodes and provides read-only access to
Notion databases and pages through the MCP protocol.

Only 3 tools with minimal parameters:
1. notion_database() - List all database items (zero parameters needed!)
2. notion_page(page_id) - Get page content
3. notion_search(query) - Search for databases/pages by keywords

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
            description="Ultra-simple Notion MCP tool for reading database/page content - Only 3 tools, minimal parameters, maximum AI usability",
            # Configuration parameters
            configurations={
                "access_token": {
                    "type": "string",
                    "default": "{{$placeholder}}",
                    "description": "Notion OAuth access token (optional - auto-fetched from oauth_tokens table by user_id if not provided)",
                    "required": False,
                    "sensitive": True,
                },
                "operation_type": {
                    "type": "string",
                    "default": "database",
                    "description": "操作类型：database (数据库操作) 或 page (页面操作)",
                    "required": False,
                    "options": ["database", "page", "both"],
                },
                "default_database_id": {
                    "type": "string",
                    "default": "",
                    "description": "默认数据库ID（当operation_type为database或both时使用）",
                    "required": False,
                    "api_endpoint": "/api/proxy/v1/app/integrations/notion/databases",
                },
                "default_page_id": {
                    "type": "string",
                    "default": "",
                    "description": "默认页面ID（当operation_type为page或both时使用）",
                    "required": False,
                    "search_endpoint": "/api/proxy/v1/app/integrations/notion/search",
                },
                "available_tools": {
                    "type": "array",
                    "default": [
                        "notion_database",
                        "notion_page",
                        "notion_search",
                    ],
                    "description": "Only 3 ultra-simple read-only tools: notion_database (list database items), notion_page (get page content), notion_search (find databases/pages by keywords)",
                    "required": False,
                    "options": [
                        "notion_database",
                        "notion_page",
                        "notion_search",
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
                    "description": "是否自动创建缺失的属性 (Read-only mode: unused)",
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
                    "name": "List Database Items (Most Common)",
                    "description": "List all items in a Notion database - just one call with zero parameters!",
                    "configurations": {
                        "access_token": "{{$placeholder}}",  # Auto-fetched from oauth_tokens
                        "operation_type": "database",
                        "default_database_id": "240784b4-8366-8084-81c7-eac647e2bbc4",
                        "available_tools": ["notion_database"],
                        "page_size_limit": 100,
                    },
                    "usage_example": {
                        "attached_to": "task_management_ai",
                        "ai_instruction": "Just call notion_database() - that's it! The database_id is auto-injected.",
                        "function_call": {
                            "tool_name": "notion_database",
                            "function_args": {},  # No parameters needed!
                        },
                        "expected_result": {
                            "result": {
                                "action": "query",
                                "database_id": "240784b4-8366-8084-81c7-eac647e2bbc4",
                                "pages": [
                                    {
                                        "id": "page_123",
                                        "title": "Task 1: Implement feature",
                                        "properties": {
                                            "Status": {"select": {"name": "In Progress"}},
                                            "Priority": {"select": {"name": "High"}},
                                        },
                                        "url": "https://notion.so/page_123",
                                    }
                                ],
                                "total_count": 15,
                                "has_more": False,
                            },
                            "success": True,
                            "execution_time": 0.8,
                        },
                    },
                },
                {
                    "name": "Get Page Content",
                    "description": "Read full content of a Notion page including all text blocks",
                    "configurations": {
                        "access_token": "{{$placeholder}}",
                        "operation_type": "page",
                        "default_page_id": "27f0b1df-411b-80ac-aa54-c4cba158a1f9",
                        "available_tools": ["notion_page"],
                        "enable_rich_text": True,
                    },
                    "usage_example": {
                        "attached_to": "content_reader_ai",
                        "ai_instruction": "Call notion_page(page_id='...') to get full page content",
                        "function_call": {
                            "tool_name": "notion_page",
                            "function_args": {
                                "page_id": "27f0b1df-411b-80ac-aa54-c4cba158a1f9",
                            },
                        },
                        "expected_result": {
                            "result": {
                                "action": "get",
                                "page_id": "27f0b1df-411b-80ac-aa54-c4cba158a1f9",
                                "title": "Project Documentation",
                                "url": "https://www.notion.so/Project-Documentation-27f0b1df411b80acaa54c4cba158a1f9",
                                "content": [
                                    {
                                        "id": "block_1",
                                        "type": "paragraph",
                                        "content": "This is the main documentation page...",
                                    }
                                ],
                            },
                            "success": True,
                            "execution_time": 0.6,
                        },
                    },
                },
                {
                    "name": "Search for Databases/Pages",
                    "description": "Search Notion workspace to find databases or pages by keywords",
                    "configurations": {
                        "access_token": "{{$placeholder}}",
                        "operation_type": "both",
                        "available_tools": ["notion_search"],
                        "page_size_limit": 50,
                    },
                    "usage_example": {
                        "attached_to": "notion_discovery_ai",
                        "ai_instruction": "Use notion_search to find databases/pages when you don't have the ID",
                        "function_call": {
                            "tool_name": "notion_search",
                            "function_args": {
                                "query": "TODO List",
                                "filter": {"object_type": "database"},
                                "limit": 10,
                            },
                        },
                        "expected_result": {
                            "result": {
                                "query": "TODO List",
                                "results": [
                                    {
                                        "id": "240784b4-8366-8084-81c7-eac647e2bbc4",
                                        "object": "database",
                                        "title": "TODO List",
                                        "url": "https://notion.so/240784b4836680....",
                                    }
                                ],
                                "total_count": 1,
                            },
                            "success": True,
                            "execution_time": 1.2,
                        },
                    },
                },
            ],
        )


# Export the specification instance
NOTION_MCP_TOOL_SPEC = NotionMCPToolSpec()
