"""
SLACK External Action Node Specification

Slack integration for sending messages, creating channels, and managing workspace interactions.
Supports OAuth authentication and various Slack API operations.
"""

from typing import Any, Dict, List

from ...models.node_enums import ExternalActionSubtype, NodeType
from ..base import COMMON_CONFIGS, BaseNodeSpec


class SlackExternalActionSpec(BaseNodeSpec):
    """Slack external action specification following the new workflow architecture."""

    def __init__(self):
        super().__init__(
            type=NodeType.EXTERNAL_ACTION,
            subtype=ExternalActionSubtype.SLACK,
            name="Slack_Action",
            description="Send messages and interact with Slack workspace",
            # Configuration parameters
            configurations={
                "action_type": {
                    "type": "string",
                    "default": "send_message",
                    "description": "Slack操作类型",
                    "required": True,
                    "options": [
                        "send_message",
                        "send_file",
                        "create_channel",
                        "invite_users",
                        "get_user_info",
                        "get_channel_info",
                        "update_message",
                        "delete_message",
                        "set_channel_topic",
                        "archive_channel",
                    ],
                },
                "channel": {
                    "type": "string",
                    "default": "#general",
                    "description": "目标频道（#channel 或 @user 或 channel_id）",
                    "required": True,
                },
                "bot_token": {
                    "type": "string",
                    "default": "",
                    "description": "Slack Bot Token (xoxb-...)",
                    "required": True,
                    "sensitive": True,
                },
                "use_oauth": {
                    "type": "boolean",
                    "default": True,
                    "description": "使用OAuth认证（推荐）",
                    "required": False,
                },
                "message_format": {
                    "type": "string",
                    "default": "text",
                    "description": "消息格式",
                    "required": False,
                    "options": ["text", "mrkdwn", "blocks"],
                },
                "thread_ts": {
                    "type": "string",
                    "default": "",
                    "description": "回复线程时间戳（可选）",
                    "required": False,
                },
                "unfurl_links": {
                    "type": "boolean",
                    "default": True,
                    "description": "自动展开链接预览",
                    "required": False,
                },
                "unfurl_media": {
                    "type": "boolean",
                    "default": True,
                    "description": "自动展开媒体预览",
                    "required": False,
                },
                **COMMON_CONFIGS,
            },
            # Parameter schemas (preferred over legacy defaults)
            input_params={
                "message": {
                    "type": "string",
                    "default": "",
                    "description": "Message text to send",
                    "required": False,
                    "multiline": True,
                },
                "blocks": {
                    "type": "array",
                    "default": [],
                    "description": "Slack block kit elements for rich messages",
                    "required": False,
                },
                "attachments": {
                    "type": "array",
                    "default": [],
                    "description": "Legacy attachments array",
                    "required": False,
                },
                "channel_override": {
                    "type": "string",
                    "default": "",
                    "description": "Optional override for target channel",
                    "required": False,
                },
                "user_mentions": {
                    "type": "array",
                    "default": [],
                    "description": "List of user IDs to mention",
                    "required": False,
                },
                "metadata": {
                    "type": "object",
                    "default": {},
                    "description": "Arbitrary metadata to include with message",
                    "required": False,
                },
            },
            output_params={
                "success": {
                    "type": "boolean",
                    "default": False,
                    "description": "Whether Slack API operation succeeded",
                    "required": False,
                },
                "message_ts": {
                    "type": "string",
                    "default": "",
                    "description": "Slack message timestamp",
                    "required": False,
                },
                "channel_id": {
                    "type": "string",
                    "default": "",
                    "description": "Channel ID where the message was sent",
                    "required": False,
                },
                "response_data": {
                    "type": "object",
                    "default": {},
                    "description": "Parsed response payload from Slack API",
                    "required": False,
                },
                "error_message": {
                    "type": "string",
                    "default": "",
                    "description": "Error message if operation failed",
                    "required": False,
                },
                "api_response": {
                    "type": "object",
                    "default": {},
                    "description": "Raw response payload from Slack API",
                    "required": False,
                },
            },
            # Port definitions
            input_ports=[
                {
                    "id": "main",
                    "name": "main",
                    "data_type": "dict",
                    "description": "Message content and Slack operation parameters",
                    "required": True,
                    "max_connections": 1,
                }
            ],
            output_ports=[
                {
                    "id": "main",
                    "name": "main",
                    "data_type": "dict",
                    "description": "Slack operation result and response data",
                    "required": False,
                    "max_connections": -1,
                },
                {
                    "id": "error",
                    "name": "error",
                    "data_type": "dict",
                    "description": "Error output when Slack operation fails",
                    "required": False,
                    "max_connections": -1,
                },
            ],
            # Metadata
            tags=["slack", "messaging", "collaboration", "external", "oauth"],
            # Examples
            examples=[
                {
                    "name": "Simple Message",
                    "description": "Send a text message to a Slack channel",
                    "configurations": {
                        "action_type": "send_message",
                        "channel": "#general",
                        "message_format": "text",
                        "use_oauth": True,
                    },
                    "input_example": {
                        "message": "Hello from the workflow system! 👋",
                        "metadata": {"source": "workflow_automation"},
                    },
                    "expected_output": {
                        "success": True,
                        "message_ts": "1706441400.123456",
                        "channel_id": "C1234567890",
                        "response_data": {
                            "ok": True,
                            "channel": "C1234567890",
                            "ts": "1706441400.123456",
                        },
                    },
                },
                {
                    "name": "Rich Message with Blocks",
                    "description": "Send a formatted message using Slack blocks",
                    "configurations": {
                        "action_type": "send_message",
                        "channel": "#alerts",
                        "message_format": "blocks",
                    },
                    "input_example": {
                        "message": "System Alert",
                        "blocks": [
                            {
                                "type": "section",
                                "text": {
                                    "type": "mrkdwn",
                                    "text": "*Alert:* System CPU usage is high",
                                },
                            },
                            {
                                "type": "section",
                                "fields": [
                                    {"type": "mrkdwn", "text": "*Server:*\nweb-01"},
                                    {"type": "mrkdwn", "text": "*CPU Usage:*\n95%"},
                                ],
                            },
                        ],
                    },
                    "expected_output": {
                        "success": True,
                        "message_ts": "1706441500.789012",
                        "channel_id": "C9876543210",
                        "response_data": {
                            "ok": True,
                            "channel": "C9876543210",
                            "ts": "1706441500.789012",
                        },
                    },
                },
                {
                    "name": "Thread Reply",
                    "description": "Reply to an existing message thread",
                    "configurations": {
                        "action_type": "send_message",
                        "channel": "#development",
                        "thread_ts": "1706441000.111222",
                    },
                    "input_example": {
                        "message": "Build completed successfully! ✅",
                        "metadata": {"build_id": "build_789"},
                    },
                    "expected_output": {
                        "success": True,
                        "message_ts": "1706441600.333444",
                        "channel_id": "C5555666677",
                        "response_data": {
                            "ok": True,
                            "channel": "C5555666677",
                            "ts": "1706441600.333444",
                            "thread_ts": "1706441000.111222",
                        },
                    },
                },
            ],
        )


# Export the specification instance
SLACK_EXTERNAL_ACTION_SPEC = SlackExternalActionSpec()
