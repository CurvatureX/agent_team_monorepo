"""
SLACK_MCP_TOOL Tool Node Specification

MCP tool for Slack integration capabilities.
This tool is attached to AI_AGENT nodes and provides Slack messaging
and workspace operations through the MCP protocol.

Note: TOOL nodes are attached to AI_AGENT nodes via attached_nodes,
not connected through input/output ports.
"""

from typing import Any, Dict, List

from ...models.node_enums import NodeType, ToolSubtype
from ..base import COMMON_CONFIGS, BaseNodeSpec


class SlackMCPToolSpec(BaseNodeSpec):
    """Slack MCP Tool specification for AI_AGENT attached functionality."""

    def __init__(self):
        super().__init__(
            type=NodeType.TOOL,
            subtype=ToolSubtype.SLACK_MCP_TOOL,
            name="Slack_MCP_Tool",
            description="Slack MCP tool for messaging and workspace operations through MCP protocol",
            # Configuration parameters
            configurations={
                "mcp_server_url": {
                    "type": "string",
                    "default": "http://localhost:8000/api/v1/mcp",
                    "description": "MCP服务器URL",
                    "required": True,
                },
                "access_token": {
                    "type": "string",
                    "default": "{{$placeholder}}",
                    "description": "Slack OAuth access token (bot token: xoxb-...)",
                    "required": True,
                    "sensitive": True,
                },
                "workspace_id": {
                    "type": "string",
                    "default": "",
                    "description": "Slack工作区ID",
                    "required": False,
                },
                "available_tools": {
                    "type": "array",
                    "default": ["slack_send_message", "slack_list_channels", "slack_get_user_info"],
                    "description": "可用的Slack工具列表",
                    "required": False,
                    "options": [
                        "slack_send_message",
                        "slack_list_channels",
                        "slack_get_user_info",
                        "slack_create_channel",
                        "slack_invite_user",
                        "slack_get_channel_history",
                        "slack_add_reaction",
                        "slack_remove_reaction",
                        "slack_upload_file",
                    ],
                },
                "default_channel": {
                    "type": "string",
                    "default": "",
                    "description": "默认频道ID或名称",
                    "required": False,
                },
                "message_limit": {
                    "type": "integer",
                    "default": 100,
                    "min": 1,
                    "max": 1000,
                    "description": "消息获取限制",
                    "required": False,
                },
                "enable_threading": {
                    "type": "boolean",
                    "default": True,
                    "description": "是否启用线程回复",
                    "required": False,
                },
                "auto_mention_users": {
                    "type": "boolean",
                    "default": False,
                    "description": "是否自动提及用户",
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
                "channel_id": {
                    "type": "string",
                    "default": "",
                    "description": "Slack channel ID relevant to the operation",
                    "required": False,
                },
                "message_ts": {
                    "type": "string",
                    "default": "",
                    "description": "Slack message timestamp if a message was sent",
                    "required": False,
                },
                "user_id": {
                    "type": "string",
                    "default": "",
                    "description": "Slack user ID relevant to the operation",
                    "required": False,
                },
            },
            # TOOL nodes have no ports - they are attached to AI_AGENT nodes            # Tools don't have attached_nodes (only AI_AGENT has this)
            attached_nodes=None,
            # Metadata
            tags=["tool", "mcp", "slack", "messaging", "collaboration", "attached"],
            # Examples
            examples=[
                {
                    "name": "Send Message to Channel",
                    "description": "Send messages to Slack channels or direct messages",
                    "configurations": {
                        "mcp_server_url": "http://localhost:8000/api/v1/mcp",
                        "slack_oauth_token": "xoxb-slack-token-123",
                        "workspace_id": "T1234567890",
                        "available_tools": ["slack_send_message"],
                        "default_channel": "general",
                        "enable_threading": True,
                    },
                    "usage_example": {
                        "attached_to": "slack_bot_ai",
                        "function_call": {
                            "tool_name": "slack_send_message",
                            "function_args": {
                                "access_token": "xoxb-slack-token-123",
                                "channel": "C1234567890",
                                "text": "Hello team! The deployment has been completed successfully. 🚀",
                                "thread_ts": None,
                            },
                            "context": {
                                "deployment_status": "completed",
                                "notification_type": "success",
                            },
                        },
                        "expected_result": {
                            "result": {
                                "ok": True,
                                "channel": "C1234567890",
                                "ts": "1642681800.123456",
                                "message": {
                                    "type": "message",
                                    "text": "Hello team! The deployment has been completed successfully. 🚀",
                                    "user": "U0123456789",
                                    "ts": "1642681800.123456",
                                },
                            },
                            "success": True,
                            "execution_time": 0.8,
                            "channel_id": "C1234567890",
                            "message_ts": "1642681800.123456",
                        },
                    },
                },
                {
                    "name": "List Workspace Channels",
                    "description": "Get list of channels in the Slack workspace",
                    "configurations": {
                        "mcp_server_url": "http://localhost:8000/api/v1/mcp",
                        "slack_oauth_token": "xoxb-slack-token-456",
                        "available_tools": ["slack_list_channels"],
                    },
                    "usage_example": {
                        "attached_to": "workspace_manager_ai",
                        "function_call": {
                            "tool_name": "slack_list_channels",
                            "function_args": {
                                "access_token": "xoxb-slack-token-456",
                                "types": "public_channel,private_channel",
                                "limit": 50,
                            },
                            "context": {"operation": "channel_discovery"},
                        },
                        "expected_result": {
                            "result": {
                                "ok": True,
                                "channels": [
                                    {
                                        "id": "C1234567890",
                                        "name": "general",
                                        "is_channel": True,
                                        "is_group": False,
                                        "is_im": False,
                                        "is_member": True,
                                        "is_private": False,
                                        "is_archived": False,
                                        "topic": {
                                            "value": "Company general discussion",
                                            "creator": "U1111111111",
                                            "last_set": 1642600000,
                                        },
                                        "purpose": {
                                            "value": "General company communications",
                                            "creator": "U1111111111",
                                            "last_set": 1642600000,
                                        },
                                        "num_members": 25,
                                    },
                                    {
                                        "id": "C2345678901",
                                        "name": "dev-team",
                                        "is_channel": True,
                                        "is_private": True,
                                        "is_member": True,
                                        "num_members": 8,
                                    },
                                ],
                                "response_metadata": {"next_cursor": ""},
                            },
                            "success": True,
                            "execution_time": 1.1,
                        },
                    },
                },
                {
                    "name": "Get User Information",
                    "description": "Retrieve detailed information about Slack users",
                    "configurations": {
                        "mcp_server_url": "http://localhost:8000/api/v1/mcp",
                        "slack_oauth_token": "xoxb-slack-token-789",
                        "available_tools": ["slack_get_user_info"],
                    },
                    "usage_example": {
                        "attached_to": "user_directory_ai",
                        "function_call": {
                            "tool_name": "slack_get_user_info",
                            "function_args": {
                                "access_token": "xoxb-slack-token-789",
                                "user": "U9876543210",
                            },
                            "context": {"lookup_reason": "team_member_info"},
                        },
                        "expected_result": {
                            "result": {
                                "ok": True,
                                "user": {
                                    "id": "U9876543210",
                                    "team_id": "T1234567890",
                                    "name": "john.doe",
                                    "deleted": False,
                                    "profile": {
                                        "title": "Senior Developer",
                                        "phone": "",
                                        "skype": "",
                                        "real_name": "John Doe",
                                        "real_name_normalized": "John Doe",
                                        "display_name": "John",
                                        "display_name_normalized": "John",
                                        "email": "john.doe@company.com",
                                        "image_24": "https://avatars.slack.com/john_24.jpg",
                                        "image_32": "https://avatars.slack.com/john_32.jpg",
                                        "image_48": "https://avatars.slack.com/john_48.jpg",
                                        "image_72": "https://avatars.slack.com/john_72.jpg",
                                        "status_text": "Working on the new feature",
                                        "status_emoji": ":computer:",
                                    },
                                    "is_admin": False,
                                    "is_owner": False,
                                    "is_primary_owner": False,
                                    "is_restricted": False,
                                    "is_ultra_restricted": False,
                                    "is_bot": False,
                                    "updated": 1642681800,
                                    "has_2fa": True,
                                },
                            },
                            "success": True,
                            "execution_time": 0.6,
                            "user_id": "U9876543210",
                        },
                    },
                },
            ],
        )


# Export the specification instance
SLACK_MCP_TOOL_SPEC = SlackMCPToolSpec()
