"""
DISCORD_MCP_TOOL Tool Node Specification

MCP tool for Discord integration capabilities.
This tool is attached to AI_AGENT nodes and provides Discord server
management and messaging through the MCP protocol.

Note: TOOL nodes are attached to AI_AGENT nodes via attached_nodes,
not connected through input/output ports.
"""

from typing import Any, Dict, List

from ...models.node_enums import NodeType, ToolSubtype
from ..base import COMMON_CONFIGS, BaseNodeSpec, create_port


class DiscordMCPToolSpec(BaseNodeSpec):
    """Discord MCP Tool specification for AI_AGENT attached functionality."""

    def __init__(self):
        super().__init__(
            type=NodeType.TOOL,
            subtype=ToolSubtype.MCP_TOOL,
            name="Discord_MCP_Tool",
            description="Discord MCP tool for server management and messaging through MCP protocol",
            # Configuration parameters
            configurations={
                "mcp_server_url": {
                    "type": "string",
                    "default": "http://localhost:8000/api/v1/mcp",
                    "description": "MCP服务器URL",
                    "required": True,
                },
                "discord_bot_token": {
                    "type": "string",
                    "default": "",
                    "description": "Discord机器人令牌",
                    "required": True,
                    "sensitive": True,
                },
                "default_server_id": {
                    "type": "string",
                    "default": "",
                    "description": "默认服务器(Guild)ID",
                    "required": False,
                },
                "available_tools": {
                    "type": "array",
                    "default": [
                        "discord_send_message",
                        "discord_get_server_info",
                        "discord_list_members",
                        "discord_create_text_channel",
                    ],
                    "description": "可用的Discord工具列表",
                    "required": False,
                    "options": [
                        "discord_get_server_info",
                        "discord_list_members",
                        "discord_create_text_channel",
                        "discord_send_message",
                        "discord_read_messages",
                        "discord_add_reaction",
                        "discord_create_invite",
                        "discord_manage_roles",
                        "discord_kick_member",
                        "discord_ban_member",
                    ],
                },
                "default_channel_id": {
                    "type": "string",
                    "default": "",
                    "description": "默认频道ID",
                    "required": False,
                },
                "message_limit": {
                    "type": "integer",
                    "default": 50,
                    "min": 1,
                    "max": 500,
                    "description": "消息获取限制",
                    "required": False,
                },
                "enable_embeds": {
                    "type": "boolean",
                    "default": True,
                    "description": "是否启用嵌入式消息",
                    "required": False,
                },
                "auto_react": {
                    "type": "boolean",
                    "default": False,
                    "description": "是否自动添加反应",
                    "required": False,
                },
                "manage_permissions": {
                    "type": "boolean",
                    "default": False,
                    "description": "是否管理权限",
                    "required": False,
                },
                **COMMON_CONFIGS,
            },
            # Default runtime parameters for tool execution
            default_input_params={
                "tool_name": "",
                "function_args": {},
                "context": {},
                "call_id": "",
            },
            default_output_params={
                "result": None,
                "success": False,
                "error_message": "",
                "execution_time": 0,
                "cached": False,
                "server_id": "",
                "channel_id": "",
                "message_id": "",
            },
            # TOOL nodes have no ports - they are attached to AI_AGENT nodes
            input_ports=[],
            output_ports=[],
            # Tools don't have attached_nodes (only AI_AGENT has this)
            attached_nodes=None,
            # Metadata
            tags=["tool", "mcp", "discord", "gaming", "community", "messaging", "attached"],
            # Examples
            examples=[
                {
                    "name": "Send Discord Message",
                    "description": "Send messages to Discord channels with rich formatting",
                    "configurations": {
                        "mcp_server_url": "http://localhost:8000/api/v1/mcp",
                        "discord_bot_token": "discord_bot_token_123",
                        "default_server_id": "123456789012345678",
                        "available_tools": ["discord_send_message"],
                        "enable_embeds": True,
                        "default_channel_id": "987654321098765432",
                    },
                    "usage_example": {
                        "attached_to": "discord_community_ai",
                        "function_call": {
                            "tool_name": "discord_send_message",
                            "function_args": {
                                "bot_token": "discord_bot_token_123",
                                "channel_id": "987654321098765432",
                                "content": "🎉 Welcome to our Discord server! Here are some helpful tips to get started.",
                            },
                            "context": {
                                "message_type": "welcome",
                                "target_audience": "new_members",
                            },
                        },
                        "expected_result": {
                            "result": {
                                "id": "1234567890123456789",
                                "type": 0,
                                "content": "🎉 Welcome to our Discord server! Here are some helpful tips to get started.",
                                "channel_id": "987654321098765432",
                                "author": {
                                    "id": "bot_user_id_123",
                                    "username": "Community Bot",
                                    "discriminator": "0000",
                                    "bot": True,
                                },
                                "timestamp": "2025-01-20T14:30:00.123000+00:00",
                                "edited_timestamp": None,
                                "tts": False,
                                "mention_everyone": False,
                            },
                            "success": True,
                            "execution_time": 0.9,
                            "channel_id": "987654321098765432",
                            "message_id": "1234567890123456789",
                        },
                    },
                },
                {
                    "name": "Get Server Information",
                    "description": "Retrieve detailed information about a Discord server",
                    "configurations": {
                        "mcp_server_url": "http://localhost:8000/api/v1/mcp",
                        "discord_bot_token": "discord_bot_token_456",
                        "available_tools": ["discord_get_server_info"],
                    },
                    "usage_example": {
                        "attached_to": "server_analytics_ai",
                        "function_call": {
                            "tool_name": "discord_get_server_info",
                            "function_args": {
                                "bot_token": "discord_bot_token_456",
                                "server_id": "123456789012345678",
                            },
                            "context": {"analysis_purpose": "server_health_check"},
                        },
                        "expected_result": {
                            "result": {
                                "id": "123456789012345678",
                                "name": "Awesome Gaming Community",
                                "icon": "server_icon_hash_123",
                                "description": "A friendly gaming community for all ages",
                                "splash": None,
                                "discovery_splash": None,
                                "approximate_member_count": 1247,
                                "approximate_presence_count": 89,
                                "features": ["COMMUNITY", "WELCOME_SCREEN_ENABLED", "NEWS"],
                                "verification_level": 2,
                                "vanity_url_code": "awesome-gaming",
                                "nsfw_level": 0,
                                "premium_tier": 2,
                                "premium_subscription_count": 15,
                                "preferred_locale": "en-US",
                            },
                            "success": True,
                            "execution_time": 1.2,
                            "server_id": "123456789012345678",
                        },
                    },
                },
                {
                    "name": "Create Text Channel",
                    "description": "Create new text channels in Discord servers",
                    "configurations": {
                        "mcp_server_url": "http://localhost:8000/api/v1/mcp",
                        "discord_bot_token": "discord_bot_token_789",
                        "available_tools": ["discord_create_text_channel"],
                        "manage_permissions": True,
                    },
                    "usage_example": {
                        "attached_to": "channel_manager_ai",
                        "function_call": {
                            "tool_name": "discord_create_text_channel",
                            "function_args": {
                                "bot_token": "discord_bot_token_789",
                                "server_id": "123456789012345678",
                                "name": "project-alpha-discussion",
                                "category_id": "456789012345678901",
                                "topic": "Discussion channel for Project Alpha development and updates",
                            },
                            "context": {"project_name": "Project Alpha", "team_size": 8},
                        },
                        "expected_result": {
                            "result": {
                                "id": "789012345678901234",
                                "type": 0,
                                "name": "project-alpha-discussion",
                                "topic": "Discussion channel for Project Alpha development and updates",
                                "guild_id": "123456789012345678",
                                "parent_id": "456789012345678901",
                                "position": 5,
                                "permission_overwrites": [],
                                "nsfw": False,
                                "rate_limit_per_user": 0,
                            },
                            "success": True,
                            "execution_time": 1.5,
                            "server_id": "123456789012345678",
                            "channel_id": "789012345678901234",
                        },
                    },
                },
                {
                    "name": "List Server Members",
                    "description": "Get list of members in the Discord server",
                    "configurations": {
                        "mcp_server_url": "http://localhost:8000/api/v1/mcp",
                        "discord_bot_token": "discord_bot_token_101",
                        "available_tools": ["discord_list_members"],
                        "message_limit": 100,
                    },
                    "usage_example": {
                        "attached_to": "member_management_ai",
                        "function_call": {
                            "tool_name": "discord_list_members",
                            "function_args": {
                                "bot_token": "discord_bot_token_101",
                                "server_id": "123456789012345678",
                                "limit": 25,
                            },
                            "context": {"operation": "member_audit"},
                        },
                        "expected_result": {
                            "result": {
                                "members": [
                                    {
                                        "user": {
                                            "id": "user_id_001",
                                            "username": "gaming_enthusiast",
                                            "discriminator": "1234",
                                            "avatar": "avatar_hash_001",
                                            "bot": False,
                                            "system": False,
                                        },
                                        "nick": "GamerGuru",
                                        "roles": ["role_id_moderator", "role_id_member"],
                                        "joined_at": "2024-12-15T10:30:00.123000+00:00",
                                        "premium_since": None,
                                        "deaf": False,
                                        "mute": False,
                                        "pending": False,
                                    },
                                    {
                                        "user": {
                                            "id": "user_id_002",
                                            "username": "code_wizard",
                                            "discriminator": "5678",
                                            "avatar": "avatar_hash_002",
                                            "bot": False,
                                        },
                                        "nick": None,
                                        "roles": ["role_id_developer", "role_id_member"],
                                        "joined_at": "2025-01-05T14:20:00.456000+00:00",
                                    },
                                ],
                                "total_count": 25,
                                "has_more": True,
                            },
                            "success": True,
                            "execution_time": 2.1,
                            "server_id": "123456789012345678",
                        },
                    },
                },
            ],
        )


# Export the specification instance
DISCORD_MCP_TOOL_SPEC = DiscordMCPToolSpec()
