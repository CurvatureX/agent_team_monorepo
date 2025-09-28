"""
DISCORD_ACTION External Action Node Specification

Discord action node for performing Discord bot operations including sending messages,
managing channels, roles, and server interactions through Discord API.
"""

from typing import Any, Dict, List

from ...models.node_enums import ExternalActionSubtype, NodeType
from ..base import COMMON_CONFIGS, BaseNodeSpec, create_port


class DiscordActionSpec(BaseNodeSpec):
    """Discord action specification for Discord bot operations."""

    def __init__(self):
        super().__init__(
            type=NodeType.EXTERNAL_ACTION,
            subtype=ExternalActionSubtype.DISCORD_ACTION,
            name="Discord_Action",
            description="Perform Discord bot operations including messaging, channel management, and server interactions",
            # Configuration parameters
            configurations={
                "discord_bot_token": {
                    "type": "string",
                    "default": "",
                    "description": "Discord机器人令牌",
                    "required": True,
                    "sensitive": True,
                },
                "action_type": {
                    "type": "string",
                    "default": "send_message",
                    "description": "Discord操作类型",
                    "required": True,
                    "options": [
                        "send_message",  # Send text/embed message
                        "send_file",  # Upload and send file
                        "create_channel",  # Create new channel
                        "delete_channel",  # Delete channel
                        "manage_roles",  # Add/remove roles
                        "kick_member",  # Kick server member
                        "ban_member",  # Ban server member
                        "create_invite",  # Create server invite
                        "send_dm",  # Send direct message
                        "react_to_message",  # Add reaction to message
                        "pin_message",  # Pin/unpin message
                        "create_thread",  # Create thread
                        "manage_permissions",  # Modify channel permissions
                        "send_webhook",  # Send webhook message
                    ],
                },
                "server_id": {
                    "type": "string",
                    "default": "",
                    "description": "Discord服务器ID",
                    "required": True,
                },
                "channel_id": {
                    "type": "string",
                    "default": "",
                    "description": "目标频道ID",
                    "required": False,
                },
                "message_content": {
                    "type": "string",
                    "default": "",
                    "description": "消息内容",
                    "required": False,
                    "multiline": True,
                },
                "embed_config": {
                    "type": "object",
                    "default": {},
                    "description": "Embed消息配置",
                    "required": False,
                },
                "file_config": {
                    "type": "object",
                    "default": {"file_path": "", "filename": "", "description": ""},
                    "description": "文件上传配置",
                    "required": False,
                },
                "target_user_id": {
                    "type": "string",
                    "default": "",
                    "description": "目标用户ID",
                    "required": False,
                },
                "role_config": {
                    "type": "object",
                    "default": {"role_id": "", "action": "add", "reason": ""},
                    "description": "角色管理配置",
                    "required": False,
                },
                "channel_config": {
                    "type": "object",
                    "default": {
                        "name": "",
                        "type": "text",
                        "category_id": "",
                        "topic": "",
                        "permissions": {},
                    },
                    "description": "频道配置",
                    "required": False,
                },
                "moderation_config": {
                    "type": "object",
                    "default": {
                        "reason": "",
                        "delete_message_days": 0,
                        "send_dm": True,
                        "dm_message": "",
                    },
                    "description": "管理操作配置",
                    "required": False,
                },
                "reaction_emoji": {
                    "type": "string",
                    "default": "👍",
                    "description": "反应表情符号",
                    "required": False,
                },
                "message_id": {
                    "type": "string",
                    "default": "",
                    "description": "目标消息ID",
                    "required": False,
                },
                "thread_config": {
                    "type": "object",
                    "default": {"name": "", "auto_archive_duration": 1440, "type": "public"},
                    "description": "线程配置",
                    "required": False,
                },
                "webhook_config": {
                    "type": "object",
                    "default": {"webhook_url": "", "username": "", "avatar_url": ""},
                    "description": "Webhook配置",
                    "required": False,
                },
                "retry_config": {
                    "type": "object",
                    "default": {"max_retries": 3, "retry_delay": 1, "exponential_backoff": True},
                    "description": "重试配置",
                    "required": False,
                },
                "rate_limit_handling": {
                    "type": "boolean",
                    "default": True,
                    "description": "是否处理速率限制",
                    "required": False,
                },
                **COMMON_CONFIGS,
            },
            # Default runtime parameters
            default_input_params={"data": {}, "context": {}, "variables": {}},
            default_output_params={
                "success": False,
                "discord_response": {},
                "message_id": "",
                "channel_id": "",
                "error_message": "",
                "rate_limit_info": {},
                "execution_metadata": {},
            },
            # Port definitions
            input_ports=[
                create_port(
                    port_id="main",
                    name="main",
                    data_type="dict",
                    description="Input data for Discord action",
                    required=True,
                    max_connections=1,
                )
            ],
            output_ports=[
                create_port(
                    port_id="success",
                    name="success",
                    data_type="dict",
                    description="Output when Discord action succeeds",
                    required=True,
                    max_connections=-1,
                ),
                create_port(
                    port_id="error",
                    name="error",
                    data_type="dict",
                    description="Output when Discord action fails",
                    required=False,
                    max_connections=-1,
                ),
            ],
            # Metadata
            tags=["external-action", "discord", "messaging", "bot", "community", "gaming"],
            # Examples
            examples=[
                {
                    "name": "Send Rich Embed Message",
                    "description": "Send a rich embed message to Discord channel with image and fields",
                    "configurations": {
                        "discord_bot_token": "your_bot_token_here",
                        "action_type": "send_message",
                        "server_id": "123456789012345678",
                        "channel_id": "987654321098765432",
                        "embed_config": {
                            "title": "System Alert",
                            "description": "{{alert_description}}",
                            "color": 16711680,
                            "fields": [
                                {"name": "Severity", "value": "{{severity}}", "inline": True},
                                {"name": "Time", "value": "{{timestamp}}", "inline": True},
                            ],
                            "footer": {"text": "Monitoring System"},
                            "thumbnail": {"url": "https://example.com/alert-icon.png"},
                        },
                        "rate_limit_handling": True,
                    },
                    "input_example": {
                        "data": {
                            "alert_description": "High CPU usage detected on server-01",
                            "severity": "HIGH",
                            "timestamp": "2025-01-20T14:30:00Z",
                            "cpu_usage": "87%",
                            "server_name": "server-01",
                        }
                    },
                    "expected_outputs": {
                        "success": {
                            "success": True,
                            "discord_response": {
                                "id": "1234567890123456789",
                                "channel_id": "987654321098765432",
                                "guild_id": "123456789012345678",
                                "timestamp": "2025-01-20T14:30:05Z",
                            },
                            "message_id": "1234567890123456789",
                            "channel_id": "987654321098765432",
                            "execution_metadata": {
                                "action_type": "send_message",
                                "embed_sent": True,
                                "rate_limited": False,
                                "execution_time_ms": 245,
                            },
                        }
                    },
                },
                {
                    "name": "Role Management",
                    "description": "Add or remove roles from Discord server members",
                    "configurations": {
                        "discord_bot_token": "your_bot_token_here",
                        "action_type": "manage_roles",
                        "server_id": "123456789012345678",
                        "target_user_id": "{{user_id}}",
                        "role_config": {
                            "role_id": "{{role_id}}",
                            "action": "add",
                            "reason": "Automatic role assignment based on user activity",
                        },
                        "retry_config": {
                            "max_retries": 3,
                            "retry_delay": 2,
                            "exponential_backoff": True,
                        },
                    },
                    "input_example": {
                        "data": {
                            "user_id": "555666777888999000",
                            "role_id": "111222333444555666",
                            "user_activity_score": 850,
                            "qualification_met": True,
                        }
                    },
                    "expected_outputs": {
                        "success": {
                            "success": True,
                            "discord_response": {
                                "user_id": "555666777888999000",
                                "roles_updated": ["111222333444555666"],
                                "action_performed": "add",
                            },
                            "execution_metadata": {
                                "action_type": "manage_roles",
                                "role_action": "add",
                                "reason": "Automatic role assignment based on user activity",
                                "execution_time_ms": 180,
                            },
                        }
                    },
                },
                {
                    "name": "Create Dynamic Channel",
                    "description": "Create a new Discord channel with specific permissions and settings",
                    "configurations": {
                        "discord_bot_token": "your_bot_token_here",
                        "action_type": "create_channel",
                        "server_id": "123456789012345678",
                        "channel_config": {
                            "name": "{{channel_name}}",
                            "type": "text",
                            "category_id": "{{category_id}}",
                            "topic": "{{channel_topic}}",
                            "permissions": {
                                "everyone": {"view_channel": False, "send_messages": False},
                                "role:moderators": {
                                    "view_channel": True,
                                    "send_messages": True,
                                    "manage_messages": True,
                                },
                            },
                        },
                    },
                    "input_example": {
                        "data": {
                            "channel_name": "incident-2025-001",
                            "category_id": "777888999000111222",
                            "channel_topic": "Emergency incident response coordination",
                            "incident_severity": "high",
                            "created_by": "ops-team",
                        }
                    },
                    "expected_outputs": {
                        "success": {
                            "success": True,
                            "discord_response": {
                                "id": "333444555666777888",
                                "name": "incident-2025-001",
                                "type": 0,
                                "guild_id": "123456789012345678",
                                "parent_id": "777888999000111222",
                                "topic": "Emergency incident response coordination",
                            },
                            "channel_id": "333444555666777888",
                            "execution_metadata": {
                                "action_type": "create_channel",
                                "channel_type": "text",
                                "permissions_applied": True,
                                "execution_time_ms": 520,
                            },
                        }
                    },
                },
                {
                    "name": "Send File with Progress Report",
                    "description": "Upload and send file to Discord channel with accompanying message",
                    "configurations": {
                        "discord_bot_token": "your_bot_token_here",
                        "action_type": "send_file",
                        "server_id": "123456789012345678",
                        "channel_id": "987654321098765432",
                        "message_content": "📊 **{{report_type}} Report** - {{report_date}}\\n\\nPlease find the attached {{report_type}} report for your review.\\n\\n**Summary:**\\n- Total Records: {{total_records}}\\n- Status: {{status}}\\n- Generated: {{generation_time}}",
                        "file_config": {
                            "file_path": "{{file_path}}",
                            "filename": "{{custom_filename}}",
                            "description": "{{report_type}} report generated automatically",
                        },
                    },
                    "input_example": {
                        "data": {
                            "report_type": "Daily Sales",
                            "report_date": "January 20, 2025",
                            "file_path": "/reports/sales_2025_01_20.xlsx",
                            "custom_filename": "Daily_Sales_Report_2025-01-20.xlsx",
                            "total_records": 1247,
                            "status": "Complete",
                            "generation_time": "2025-01-20T06:00:00Z",
                        }
                    },
                    "expected_outputs": {
                        "success": {
                            "success": True,
                            "discord_response": {
                                "id": "999000111222333444",
                                "channel_id": "987654321098765432",
                                "attachments": [
                                    {
                                        "id": "444555666777888999",
                                        "filename": "Daily_Sales_Report_2025-01-20.xlsx",
                                        "size": 52428,
                                        "url": "https://cdn.discordapp.com/attachments/...",
                                    }
                                ],
                            },
                            "message_id": "999000111222333444",
                            "channel_id": "987654321098765432",
                            "execution_metadata": {
                                "action_type": "send_file",
                                "file_uploaded": True,
                                "file_size_bytes": 52428,
                                "upload_time_ms": 2150,
                                "execution_time_ms": 2380,
                            },
                        }
                    },
                },
            ],
        )


# Export the specification instance
DISCORD_ACTION_SPEC = DiscordActionSpec()
