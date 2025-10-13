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
                    "default": "{{$placeholder}}",
                    "description": "Notion集成令牌",
                    "required": True,
                    "sensitive": True,
                },
                "operation_type": {
                    "type": "string",
                    "default": "database",
                    "description": "操作类型：database (数据库操作) 或 page (页面操作)",
                    "required": False,
                    "options": ["database", "page", "both"],
                },
                "database_id": {
                    "type": "string",
                    "default": "",
                    "description": "目标数据库ID（当operation_type为database或both时使用）",
                    "required": False,
                    "api_endpoint": "/api/proxy/v1/app/integrations/notion/databases",
                },
                "page_id": {
                    "type": "string",
                    "default": "",
                    "description": "目标页面ID（当operation_type为page或both时使用）",
                    "required": False,
                    "search_endpoint": "/api/proxy/v1/app/integrations/notion/search",
                },
                **COMMON_CONFIGS,
            },
            # Parameter schemas (preferred over legacy defaults)
            input_params={
                "instruction": {
                    "type": "string",
                    "default": "",
                    "description": "Natural language instruction for AI-powered multi-step Notion operations",
                    "required": True,
                },
                "context": {
                    "type": "object",
                    "default": {},
                    "description": "Context data for AI decision-making: database_id, page_id, content, metadata, etc.",
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
                "ai_execution": {
                    "type": "object",
                    "default": {},
                    "description": "AI execution telemetry: rounds_executed, completed, plan, rounds[], discovered_resources",
                    "required": False,
                },
                "discovered_resources": {
                    "type": "object",
                    "default": {},
                    "description": "Resources discovered during execution: databases, pages, block_ids, schemas",
                    "required": False,
                },
            },  # Metadata
            # Examples
            examples=[
                {
                    "name": "Create Task with Known Database ID",
                    "description": "Create a new task entry in a known database with AI-powered automation",
                    "input_example": {
                        "instruction": "Create a new task page for implementing user authentication API",
                        "context": {
                            "database_id": "12345678-1234-5678-9012-123456789012",
                            "task_name": "Implement user authentication API",
                            "status": "In Progress",
                            "priority": "High",
                            "due_date": "2025-01-30",
                            "description": "Design and implement JWT-based authentication for the API endpoints. Include proper error handling and rate limiting.",
                        },
                    },
                    "expected_outputs": {
                        "success": True,
                        "resource_id": "87654321-8765-4321-8765-876543218765",
                        "resource_url": "https://www.notion.so/Implement-user-authentication-API-87654321876543218765876543218765",
                        "ai_execution": {
                            "rounds_executed": 2,
                            "completed": True,
                            "plan": None,
                        },
                        "discovered_resources": {
                            "created_page": ["87654321-8765-4321-8765-876543218765"]
                        },
                    },
                },
                {
                    "name": "Create Meeting Notes (Search Database First)",
                    "description": "Create meeting notes page by first searching for the meetings database",
                    "input_example": {
                        "instruction": "Create a meeting notes page in the Team Meetings database",
                        "context": {
                            "meeting_title": "Q1 Sprint Planning - Engineering Team",
                            "meeting_date": "2025-01-20",
                            "attendees": ["Engineering", "Product", "Design"],
                            "agenda": "Review Q1 objectives and key results",
                            "key_decisions": "Prioritize authentication features and performance optimization",
                            "action_items": [
                                "Create detailed user stories for auth features by Jan 25",
                                "Schedule performance testing sprint",
                            ],
                        },
                    },
                    "expected_outputs": {
                        "success": True,
                        "resource_id": "11223344-1122-3344-5566-112233445566",
                        "resource_url": "https://www.notion.so/Q1-Sprint-Planning-Engineering-Team-11223344112233445566112233445566",
                        "ai_execution": {
                            "rounds_executed": 3,
                            "completed": True,
                            "plan": [
                                {"step": 1, "action_type": "search"},
                                {"step": 2, "action_type": "create_page"},
                            ],
                        },
                        "discovered_resources": {
                            "databases": {"Team Meetings": "98765432-9876-5432-1098-987654321098"},
                            "created_page": ["11223344-1122-3344-5566-112233445566"],
                        },
                    },
                },
                {
                    "name": "Log Slack Message to Notion",
                    "description": "Log a Slack message to Notion database using workflow trigger data",
                    "input_example": {
                        "instruction": "Log this Slack message to the team updates database",
                        "context": {
                            "database_id": "updates-db-123",
                            "slack_user": "U123456",
                            "slack_channel": "C789012",
                            "message_text": "Deployment completed successfully at 3pm",
                            "timestamp": "2025-01-20T15:00:00Z",
                        },
                    },
                    "expected_outputs": {
                        "success": True,
                        "resource_id": "page-id-456",
                        "ai_execution": {
                            "rounds_executed": 2,
                            "completed": True,
                        },
                    },
                },
                {
                    "name": "Create Task with Custom Property",
                    "description": "Create task with a custom Urgency property, creating the property if it doesn't exist",
                    "input_example": {
                        "instruction": "Create a new task with Urgency set to High",
                        "context": {
                            "database_id": "tasks-db-789",
                            "task_name": "Fix critical security vulnerability",
                            "urgency": "High",
                            "description": "Address reported XSS vulnerability in user input forms",
                        },
                    },
                    "expected_outputs": {
                        "success": True,
                        "resource_id": "task-page-999",
                        "ai_execution": {
                            "rounds_executed": 4,
                            "completed": True,
                            "plan": [
                                {"step": 1, "action_type": "retrieve_database"},
                                {"step": 2, "action_type": "update_database"},
                                {"step": 3, "action_type": "create_page"},
                            ],
                        },
                        "discovered_resources": {
                            "schemas_cache": {
                                "tasks-db-789": {
                                    "properties": ["Name", "Status", "Urgency", "Description"]
                                }
                            },
                            "created_page": ["task-page-999"],
                        },
                    },
                },
            ],
        )


# Export the specification instance
NOTION_EXTERNAL_ACTION_SPEC = NotionActionSpec()
