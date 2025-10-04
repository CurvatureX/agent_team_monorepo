"""
NOTION External Action Node Specification

Notion action node for performing Notion API operations including database management,
page creation, content updates, and workspace automation.
"""

from typing import Any, Dict, List

from ...models.node_enums import ExternalActionSubtype, NodeType
from ..base import COMMON_CONFIGS, BaseNodeSpec


class NotionActionSpec(BaseNodeSpec):
    """Notion action specification for Notion API operations."""

    def __init__(self):
        super().__init__(
            type=NodeType.EXTERNAL_ACTION,
            subtype=ExternalActionSubtype.NOTION,
            name="Notion_Action",
            description="Perform Notion operations including database management, page creation, and content automation",
            # Configuration parameters
            configurations={
                "notion_token": {
                    "type": "string",
                    "default": "",
                    "description": "Notion集成令牌",
                    "required": True,
                    "sensitive": True,
                },
                "action_type": {
                    "type": "string",
                    "default": "create_page",
                    "description": "Notion操作类型",
                    "required": True,
                    "options": [
                        # Page Operations
                        "create_page",  # Create new page
                        "update_page",  # Update existing page
                        "delete_page",  # Archive/delete page
                        "retrieve_page",  # Get page content
                        "duplicate_page",  # Duplicate page
                        # Database Operations
                        "create_database",  # Create new database
                        "update_database",  # Update database properties
                        "query_database",  # Query database entries
                        "retrieve_database",  # Get database schema
                        # Database Entry Operations
                        "create_database_entry",  # Create database row
                        "update_database_entry",  # Update database row
                        "delete_database_entry",  # Delete database row
                        # Block Operations
                        "append_blocks",  # Add content blocks
                        "update_block",  # Update block content
                        "delete_block",  # Delete content block
                        "retrieve_block_children",  # Get child blocks
                        # Search Operations
                        "search_content",  # Search workspace
                        "filter_pages",  # Filter pages by criteria
                        # User Operations
                        "list_users",  # List workspace users
                        "retrieve_user",  # Get user information
                        # Comment Operations
                        "create_comment",  # Add comment to page
                        "retrieve_comments",  # Get page comments
                    ],
                },
                "database_config": {
                    "type": "object",
                    "default": {
                        "database_id": "",
                        "title": "",
                        "description": "",
                        "properties": {},
                        "parent": {},
                    },
                    "description": "数据库配置",
                    "required": False,
                },
                "page_config": {
                    "type": "object",
                    "default": {
                        "parent": {},
                        "properties": {},
                        "children": [],
                        "icon": {},
                        "cover": {},
                    },
                    "description": "页面配置",
                    "required": False,
                },
                "query_config": {
                    "type": "object",
                    "default": {"filter": {}, "sorts": [], "start_cursor": "", "page_size": 100},
                    "description": "查询配置",
                    "required": False,
                },
                "block_config": {
                    "type": "object",
                    "default": {"type": "paragraph", "content": {}, "children": []},
                    "description": "内容块配置",
                    "required": False,
                },
                "search_config": {
                    "type": "object",
                    "default": {
                        "query": "",
                        "sort": {"direction": "descending", "timestamp": "last_edited_time"},
                        "filter": {"value": "page", "property": "object"},
                        "page_size": 100,
                    },
                    "description": "搜索配置",
                    "required": False,
                },
                "user_config": {
                    "type": "object",
                    "default": {"user_id": "", "include_bots": False},
                    "description": "用户配置",
                    "required": False,
                },
                "comment_config": {
                    "type": "object",
                    "default": {
                        "parent": {},
                        "rich_text": [],
                        "start_cursor": "",
                        "page_size": 100,
                    },
                    "description": "评论配置",
                    "required": False,
                },
                "formatting_options": {
                    "type": "object",
                    "default": {
                        "enable_markdown": True,
                        "preserve_formatting": True,
                        "auto_link_detection": True,
                    },
                    "description": "格式化选项",
                    "required": False,
                },
                "retry_config": {
                    "type": "object",
                    "default": {
                        "max_retries": 3,
                        "retry_delay": 1,
                        "exponential_backoff": True,
                        "handle_rate_limits": True,
                    },
                    "description": "重试配置",
                    "required": False,
                },
                **COMMON_CONFIGS,
            },
            # Parameter schemas (preferred over legacy defaults)
            input_params={
                "action_type": {
                    "type": "string",
                    "default": "",
                    "description": "Dynamic action type (overrides configuration action_type)",
                    "required": False,
                    "options": [
                        # Page Operations
                        "create_page",
                        "update_page",
                        "delete_page",
                        "retrieve_page",
                        "duplicate_page",
                        # Database Operations
                        "create_database",
                        "update_database",
                        "query_database",
                        "retrieve_database",
                        # Database Entry Operations
                        "create_database_entry",
                        "update_database_entry",
                        "delete_database_entry",
                        # Block Operations
                        "append_blocks",
                        "update_block",
                        "delete_block",
                        "retrieve_block_children",
                        # Search Operations
                        "search_content",
                        "filter_pages",
                        # User Operations
                        "list_users",
                        "retrieve_user",
                        # Comment Operations
                        "create_comment",
                        "retrieve_comments",
                    ],
                },
                "data": {
                    "type": "object",
                    "default": {},
                    "description": "Primary input payload",
                    "required": False,
                },
            },
            output_params={
                "success": {
                    "type": "boolean",
                    "default": False,
                    "description": "Whether Notion API operation succeeded",
                    "required": False,
                },
                "notion_response": {
                    "type": "object",
                    "default": {},
                    "description": "Parsed Notion API response",
                    "required": False,
                },
                "resource_id": {
                    "type": "string",
                    "default": "",
                    "description": "Created/affected resource ID",
                    "required": False,
                },
                "resource_url": {
                    "type": "string",
                    "default": "",
                    "description": "URL to the resource",
                    "required": False,
                },
                "error_message": {
                    "type": "string",
                    "default": "",
                    "description": "Error message if operation failed",
                    "required": False,
                },
                "rate_limit_info": {
                    "type": "object",
                    "default": {},
                    "description": "Notion rate limit information",
                    "required": False,
                },
                "execution_metadata": {
                    "type": "object",
                    "default": {},
                    "description": "Execution metadata (timings, retries)",
                    "required": False,
                },
            },  # Metadata
            tags=[
                "external-action",
                "notion",
                "productivity",
                "database",
                "documentation",
                "knowledge-base",
            ],
            # Examples
            examples=[
                {
                    "name": "Create Project Task Database Entry",
                    "description": "Create a new task entry in project management database with properties",
                    "configurations": {
                        "notion_token": "secret_your_notion_token_here",
                        "action_type": "create_database_entry",
                        "database_config": {"database_id": "{{database_id}}"},
                        "page_config": {
                            "properties": {
                                "Name": {"title": [{"text": {"content": "{{task_name}}"}}]},
                                "Status": {"select": {"name": "{{task_status}}"}},
                                "Priority": {"select": {"name": "{{task_priority}}"}},
                                "Assignee": {"people": "{{assignees}}"},
                                "Due Date": {"date": {"start": "{{due_date}}"}},
                                "Description": {
                                    "rich_text": [{"text": {"content": "{{task_description}}"}}]
                                },
                            }
                        },
                        "formatting_options": {
                            "enable_markdown": True,
                            "auto_link_detection": True,
                        },
                    },
                    "input_example": {
                        "data": {
                            "database_id": "12345678-1234-5678-9012-123456789012",
                            "task_name": "Implement user authentication API",
                            "task_status": "In Progress",
                            "task_priority": "High",
                            "assignees": [{"id": "user-123"}, {"id": "user-456"}],
                            "due_date": "2025-01-30",
                            "task_description": "Design and implement JWT-based authentication for the API endpoints. Include proper error handling and rate limiting.",
                        }
                    },
                    "expected_outputs": {
                        "success": {
                            "success": True,
                            "notion_response": {
                                "object": "page",
                                "id": "87654321-8765-4321-8765-876543218765",
                                "url": "https://www.notion.so/Implement-user-authentication-API-87654321876543218765876543218765",
                                "properties": {
                                    "Name": {
                                        "title": [
                                            {
                                                "text": {
                                                    "content": "Implement user authentication API"
                                                }
                                            }
                                        ]
                                    },
                                    "Status": {"select": {"name": "In Progress"}},
                                    "Priority": {"select": {"name": "High"}},
                                },
                                "created_time": "2025-01-20T15:30:00.000Z",
                                "last_edited_time": "2025-01-20T15:30:00.000Z",
                            },
                            "resource_id": "87654321-8765-4321-8765-876543218765",
                            "resource_url": "https://www.notion.so/Implement-user-authentication-API-87654321876543218765876543218765",
                            "execution_metadata": {
                                "action_type": "create_database_entry",
                                "database_id": "12345678-1234-5678-9012-123456789012",
                                "properties_set": 6,
                                "assignees_count": 2,
                                "execution_time_ms": 750,
                            },
                        }
                    },
                },
                {
                    "name": "Create Meeting Notes Page",
                    "description": "Create detailed meeting notes page with structured content blocks",
                    "configurations": {
                        "notion_token": "secret_your_notion_token_here",
                        "action_type": "create_page",
                        "page_config": {
                            "parent": {"database_id": "{{meetings_database_id}}"},
                            "properties": {
                                "Meeting Title": {
                                    "title": [{"text": {"content": "{{meeting_title}}"}}]
                                },
                                "Date": {"date": {"start": "{{meeting_date}}"}},
                                "Attendees": {"multi_select": "{{attendee_tags}}"},
                            },
                            "children": [
                                {
                                    "object": "block",
                                    "type": "heading_2",
                                    "heading_2": {
                                        "rich_text": [{"text": {"content": "Meeting Agenda"}}]
                                    },
                                },
                                {
                                    "object": "block",
                                    "type": "bulleted_list_item",
                                    "bulleted_list_item": {
                                        "rich_text": [{"text": {"content": "{{agenda_item_1}}"}}]
                                    },
                                },
                                {
                                    "object": "block",
                                    "type": "heading_2",
                                    "heading_2": {
                                        "rich_text": [{"text": {"content": "Key Decisions"}}]
                                    },
                                },
                                {
                                    "object": "block",
                                    "type": "paragraph",
                                    "paragraph": {
                                        "rich_text": [{"text": {"content": "{{key_decisions}}"}}]
                                    },
                                },
                                {
                                    "object": "block",
                                    "type": "heading_2",
                                    "heading_2": {
                                        "rich_text": [{"text": {"content": "Action Items"}}]
                                    },
                                },
                                {
                                    "object": "block",
                                    "type": "to_do",
                                    "to_do": {
                                        "rich_text": [{"text": {"content": "{{action_item_1}}"}}],
                                        "checked": False,
                                    },
                                },
                            ],
                        },
                    },
                    "input_example": {
                        "data": {
                            "meetings_database_id": "98765432-9876-5432-1098-987654321098",
                            "meeting_title": "Q1 Sprint Planning - Engineering Team",
                            "meeting_date": "2025-01-20",
                            "attendee_tags": [
                                {"name": "Engineering"},
                                {"name": "Product"},
                                {"name": "Design"},
                            ],
                            "agenda_item_1": "Review Q1 objectives and key results",
                            "key_decisions": "Decided to prioritize authentication features and performance optimization for Q1. Timeline approved for 3-month sprint cycles.",
                            "action_item_1": "Create detailed user stories for authentication features by Jan 25",
                        }
                    },
                    "expected_outputs": {
                        "success": {
                            "success": True,
                            "notion_response": {
                                "object": "page",
                                "id": "11223344-1122-3344-5566-112233445566",
                                "url": "https://www.notion.so/Q1-Sprint-Planning-Engineering-Team-11223344112233445566112233445566",
                                "properties": {
                                    "Meeting Title": {
                                        "title": [
                                            {
                                                "text": {
                                                    "content": "Q1 Sprint Planning - Engineering Team"
                                                }
                                            }
                                        ]
                                    }
                                },
                                "created_time": "2025-01-20T16:00:00.000Z",
                            },
                            "resource_id": "11223344-1122-3344-5566-112233445566",
                            "resource_url": "https://www.notion.so/Q1-Sprint-Planning-Engineering-Team-11223344112233445566112233445566",
                            "execution_metadata": {
                                "action_type": "create_page",
                                "parent_database": "98765432-9876-5432-1098-987654321098",
                                "blocks_created": 6,
                                "properties_set": 3,
                                "execution_time_ms": 1200,
                            },
                        }
                    },
                },
                {
                    "name": "Query Project Database with Filters",
                    "description": "Query project database with complex filters and sorting",
                    "configurations": {
                        "notion_token": "secret_your_notion_token_here",
                        "action_type": "query_database",
                        "database_config": {"database_id": "{{projects_database_id}}"},
                        "query_config": {
                            "filter": {
                                "and": [
                                    {
                                        "property": "Status",
                                        "select": {"equals": "{{filter_status}}"},
                                    },
                                    {"property": "Priority", "select": {"does_not_equal": "Low"}},
                                    {
                                        "property": "Due Date",
                                        "date": {"on_or_before": "{{deadline_filter}}"},
                                    },
                                ]
                            },
                            "sorts": [
                                {"property": "Priority", "direction": "ascending"},
                                {"property": "Due Date", "direction": "ascending"},
                            ],
                            "page_size": 50,
                        },
                    },
                    "input_example": {
                        "data": {
                            "projects_database_id": "55667788-5566-7788-9900-556677889900",
                            "filter_status": "In Progress",
                            "deadline_filter": "2025-01-31",
                        }
                    },
                    "expected_outputs": {
                        "success": {
                            "success": True,
                            "notion_response": {
                                "object": "list",
                                "results": [
                                    {
                                        "object": "page",
                                        "id": "project-001",
                                        "properties": {
                                            "Name": {
                                                "title": [
                                                    {
                                                        "text": {
                                                            "content": "User Authentication System"
                                                        }
                                                    }
                                                ]
                                            },
                                            "Status": {"select": {"name": "In Progress"}},
                                            "Priority": {"select": {"name": "High"}},
                                            "Due Date": {"date": {"start": "2025-01-25"}},
                                        },
                                    },
                                    {
                                        "object": "page",
                                        "id": "project-002",
                                        "properties": {
                                            "Name": {
                                                "title": [
                                                    {
                                                        "text": {
                                                            "content": "API Performance Optimization"
                                                        }
                                                    }
                                                ]
                                            },
                                            "Status": {"select": {"name": "In Progress"}},
                                            "Priority": {"select": {"name": "Medium"}},
                                            "Due Date": {"date": {"start": "2025-01-30"}},
                                        },
                                    },
                                ],
                                "next_cursor": None,
                                "has_more": False,
                            },
                            "resource_id": "55667788-5566-7788-9900-556677889900",
                            "execution_metadata": {
                                "action_type": "query_database",
                                "database_id": "55667788-5566-7788-9900-556677889900",
                                "results_count": 2,
                                "filters_applied": 3,
                                "sorts_applied": 2,
                                "execution_time_ms": 650,
                            },
                        }
                    },
                },
                {
                    "name": "Update Page Content with Rich Blocks",
                    "description": "Append rich content blocks to existing page including tables and callouts",
                    "configurations": {
                        "notion_token": "secret_your_notion_token_here",
                        "action_type": "append_blocks",
                        "page_config": {"parent": {"page_id": "{{target_page_id}}"}},
                        "block_config": {
                            "children": [
                                {
                                    "object": "block",
                                    "type": "callout",
                                    "callout": {
                                        "rich_text": [{"text": {"content": "{{callout_message}}"}}],
                                        "icon": {"emoji": "💡"},
                                    },
                                },
                                {
                                    "object": "block",
                                    "type": "table",
                                    "table": {
                                        "table_width": 3,
                                        "has_column_header": True,
                                        "has_row_header": False,
                                        "children": "{{table_rows}}",
                                    },
                                },
                            ]
                        },
                    },
                    "input_example": {
                        "data": {
                            "target_page_id": "22334455-2233-4455-6677-223344556677",
                            "callout_message": "Performance metrics updated based on latest testing results",
                            "table_rows": [
                                {
                                    "type": "table_row",
                                    "table_row": {
                                        "cells": [
                                            [{"text": {"content": "Metric"}}],
                                            [{"text": {"content": "Before"}}],
                                            [{"text": {"content": "After"}}],
                                        ]
                                    },
                                },
                                {
                                    "type": "table_row",
                                    "table_row": {
                                        "cells": [
                                            [{"text": {"content": "Response Time"}}],
                                            [{"text": {"content": "250ms"}}],
                                            [{"text": {"content": "120ms"}}],
                                        ]
                                    },
                                },
                                {
                                    "type": "table_row",
                                    "table_row": {
                                        "cells": [
                                            [{"text": {"content": "Throughput"}}],
                                            [{"text": {"content": "1000 req/s"}}],
                                            [{"text": {"content": "2500 req/s"}}],
                                        ]
                                    },
                                },
                            ],
                        }
                    },
                    "expected_outputs": {
                        "success": {
                            "success": True,
                            "notion_response": {
                                "object": "list",
                                "results": [
                                    {
                                        "object": "block",
                                        "id": "block-callout-001",
                                        "type": "callout",
                                        "created_time": "2025-01-20T17:00:00.000Z",
                                    },
                                    {
                                        "object": "block",
                                        "id": "block-table-001",
                                        "type": "table",
                                        "created_time": "2025-01-20T17:00:01.000Z",
                                    },
                                ],
                            },
                            "resource_id": "22334455-2233-4455-6677-223344556677",
                            "execution_metadata": {
                                "action_type": "append_blocks",
                                "page_id": "22334455-2233-4455-6677-223344556677",
                                "blocks_added": 2,
                                "table_rows_created": 3,
                                "execution_time_ms": 950,
                            },
                        }
                    },
                },
            ],
            # System prompt appendix for AI guidance
            system_prompt_appendix="""Output `action_type` to dynamically control Notion operations. **If you don't know IDs (database_id, page_id, etc.), leave them blank or use descriptive names - the workflow may provide them.**

**All Action Types:**

**Pages:**
- `create_page`: Create new page in database/parent - needs parent_id (database UUID), title, content
- `update_page`: Modify page properties - needs page_id, properties dict
- `retrieve_page`: Get page details - needs page_id
- `delete_page`: Archive page - needs page_id
- `duplicate_page`: Copy existing page - needs page_id

**Databases:**
- `create_database`: New database - needs parent (page_id), title, properties schema
- `update_database`: Modify database schema - needs database_id, properties
- `query_database`: Search database with filters - needs database_id, optional filter/sorts
- `retrieve_database`: Get database schema - needs database_id

**Database Entries:**
- `create_database_entry`: Add row to database - needs database_id, properties with values
- `update_database_entry`: Update row - needs page_id (entry ID), properties
- `delete_database_entry`: Delete row - needs page_id

**Blocks:**
- `append_blocks`: Add content to page - needs page_id, children (blocks array)
- `update_block`: Modify block - needs block_id, content
- `delete_block`: Remove block - needs block_id
- `retrieve_block_children`: Get nested blocks - needs block_id

**Search:**
- `search_content`: Find pages/databases - optional query text, filter
- `filter_pages`: Advanced search - needs filter criteria

**Users/Comments:**
- `list_users`: Get workspace users
- `retrieve_user`: Get user info - needs user_id
- `create_comment`: Add comment - needs parent (page_id), rich_text
- `retrieve_comments`: Get comments - needs parent (page_id)

**Property Formats:**
- Title: `{"title": [{"text": {"content": "text here"}}]}`
- Select: `{"select": {"name": "option"}}`
- Date: `{"date": {"start": "2025-01-20"}}`
- Checkbox: `{"checkbox": true}`
- Number: `{"number": 42}`
- People: `{"people": [{"id": "user-uuid"}]}`

**Example:**
```json
{"action_type": "create_database_entry", "database_id": "", "properties": {"Name": {"title": [{"text": {"content": "New Task"}}]}, "Status": {"select": {"name": "In Progress"}}}}
```
""",
        )


# Export the specification instance
NOTION_EXTERNAL_ACTION_SPEC = NotionActionSpec()
