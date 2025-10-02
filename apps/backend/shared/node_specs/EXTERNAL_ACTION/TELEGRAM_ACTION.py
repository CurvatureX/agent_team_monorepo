"""
TELEGRAM_ACTION External Action Node Specification

Telegram action node for performing Telegram bot operations including sending messages,
managing chats, inline keyboards, and bot interactions through Telegram Bot API.
"""

from typing import Any, Dict, List

from ...models.node_enums import ExternalActionSubtype, NodeType
from ..base import COMMON_CONFIGS, BaseNodeSpec


class TelegramActionSpec(BaseNodeSpec):
    """Telegram action specification for Telegram bot operations."""

    def __init__(self):
        super().__init__(
            type=NodeType.EXTERNAL_ACTION,
            subtype=ExternalActionSubtype.TELEGRAM_ACTION,
            name="Telegram_Action",
            description="Perform Telegram bot operations including messaging, media sharing, and chat management",
            # Configuration parameters
            configurations={
                "telegram_bot_token": {
                    "type": "string",
                    "default": "",
                    "description": "Telegram机器人令牌",
                    "required": True,
                    "sensitive": True,
                },
                "action_type": {
                    "type": "string",
                    "default": "send_message",
                    "description": "Telegram操作类型",
                    "required": True,
                    "options": [
                        "send_message",  # Send text message
                        "send_photo",  # Send photo/image
                        "send_document",  # Send document/file
                        "send_video",  # Send video file
                        "send_audio",  # Send audio file
                        "send_voice",  # Send voice message
                        "send_location",  # Send location
                        "send_contact",  # Send contact info
                        "send_poll",  # Create poll
                        "send_sticker",  # Send sticker
                        "edit_message",  # Edit existing message
                        "delete_message",  # Delete message
                        "forward_message",  # Forward message
                        "pin_message",  # Pin chat message
                        "unpin_message",  # Unpin chat message
                        "ban_user",  # Ban user from group
                        "unban_user",  # Unban user
                        "kick_user",  # Kick user from group
                        "promote_user",  # Promote to admin
                        "restrict_user",  # Restrict user permissions
                        "set_chat_title",  # Change chat title
                        "set_chat_description",  # Change chat description
                        "export_chat_invite",  # Create invite link
                    ],
                },
                "chat_id": {
                    "type": "string",
                    "default": "",
                    "description": "目标聊天ID",
                    "required": True,
                },
                "message_text": {
                    "type": "string",
                    "default": "",
                    "description": "消息文本内容",
                    "required": False,
                    "multiline": True,
                },
                "parse_mode": {
                    "type": "string",
                    "default": "Markdown",
                    "description": "消息解析模式",
                    "required": False,
                    "options": ["Markdown", "HTML", "MarkdownV2"],
                },
                "media_config": {
                    "type": "object",
                    "default": {"file_path": "", "caption": "", "supports_streaming": False},
                    "description": "媒体文件配置",
                    "required": False,
                },
                "keyboard_config": {
                    "type": "object",
                    "default": {
                        "type": "inline",
                        "buttons": [],
                        "resize_keyboard": True,
                        "one_time_keyboard": False,
                    },
                    "description": "键盘配置",
                    "required": False,
                },
                "location_config": {
                    "type": "object",
                    "default": {"latitude": 0.0, "longitude": 0.0, "live_period": 0},
                    "description": "位置信息配置",
                    "required": False,
                },
                "contact_config": {
                    "type": "object",
                    "default": {"phone_number": "", "first_name": "", "last_name": ""},
                    "description": "联系人配置",
                    "required": False,
                },
                "poll_config": {
                    "type": "object",
                    "default": {
                        "question": "",
                        "options": [],
                        "is_anonymous": True,
                        "type": "regular",
                        "allows_multiple_answers": False,
                    },
                    "description": "投票配置",
                    "required": False,
                },
                "user_management": {
                    "type": "object",
                    "default": {
                        "user_id": "",
                        "until_date": 0,
                        "revoke_messages": False,
                        "permissions": {},
                    },
                    "description": "用户管理配置",
                    "required": False,
                },
                "message_options": {
                    "type": "object",
                    "default": {
                        "disable_notification": False,
                        "protect_content": False,
                        "allow_sending_without_reply": True,
                        "reply_to_message_id": "",
                    },
                    "description": "消息选项",
                    "required": False,
                },
                "edit_config": {
                    "type": "object",
                    "default": {"message_id": "", "inline_message_id": ""},
                    "description": "编辑消息配置",
                    "required": False,
                },
                "forward_config": {
                    "type": "object",
                    "default": {
                        "from_chat_id": "",
                        "message_id": "",
                        "disable_notification": False,
                    },
                    "description": "转发消息配置",
                    "required": False,
                },
                "retry_config": {
                    "type": "object",
                    "default": {"max_retries": 3, "retry_delay": 1, "exponential_backoff": True},
                    "description": "重试配置",
                    "required": False,
                },
                **COMMON_CONFIGS,
            },
            # Parameter schemas (preferred over legacy defaults)
            input_params={
                "data": {
                    "type": "object",
                    "default": {},
                    "description": "Primary input payload",
                    "required": False,
                },
                "context": {
                    "type": "object",
                    "default": {},
                    "description": "Context for templating or logic",
                    "required": False,
                },
                "variables": {
                    "type": "object",
                    "default": {},
                    "description": "Template variables",
                    "required": False,
                },
            },
            output_params={
                "success": {
                    "type": "boolean",
                    "default": False,
                    "description": "Whether Telegram API operation succeeded",
                    "required": False,
                },
                "telegram_response": {
                    "type": "object",
                    "default": {},
                    "description": "Parsed Telegram API response",
                    "required": False,
                },
                "message_id": {
                    "type": "string",
                    "default": "",
                    "description": "Message ID (if sent)",
                    "required": False,
                },
                "chat_id": {
                    "type": "string",
                    "default": "",
                    "description": "Chat ID the message was sent to",
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
                    "description": "Telegram rate limit info if available",
                    "required": False,
                },
                "execution_metadata": {
                    "type": "object",
                    "default": {},
                    "description": "Execution metadata (timings, retries)",
                    "required": False,
                },
            },  # Metadata
            tags=["external-action", "telegram", "messaging", "bot", "communication"],
            # Examples
            examples=[
                {
                    "name": "Send Trading Alert with Inline Keyboard",
                    "description": "Send trading alert to Telegram channel with action buttons",
                    "configurations": {
                        "telegram_bot_token": "1234567890:ABCDefGhIJKlmnOpQrStUvWxYz",
                        "action_type": "send_message",
                        "chat_id": "-1001234567890",
                        "message_text": "🚨 **Trading Alert** 🚨\\n\\n**Symbol:** {{symbol}}\\n**Signal:** {{signal_type}}\\n**Price:** ${{current_price}}\\n**Target:** ${{target_price}}\\n**Stop Loss:** ${{stop_loss}}\\n\\n**Analysis:**\\n{{analysis}}\\n\\n**Risk Level:** {{risk_level}}",
                        "parse_mode": "Markdown",
                        "keyboard_config": {
                            "type": "inline",
                            "buttons": [
                                [
                                    {
                                        "text": "✅ Execute Trade",
                                        "callback_data": "execute_{{trade_id}}",
                                    },
                                    {
                                        "text": "❌ Ignore Signal",
                                        "callback_data": "ignore_{{trade_id}}",
                                    },
                                ],
                                [
                                    {"text": "📊 View Chart", "url": "{{chart_url}}"},
                                    {
                                        "text": "📈 Analysis",
                                        "callback_data": "analysis_{{trade_id}}",
                                    },
                                ],
                            ],
                        },
                        "message_options": {
                            "disable_notification": False,
                            "protect_content": False,
                        },
                    },
                    "input_example": {
                        "data": {
                            "symbol": "BTCUSDT",
                            "signal_type": "BUY",
                            "current_price": "42,500",
                            "target_price": "45,000",
                            "stop_loss": "40,000",
                            "analysis": "Strong bullish momentum with RSI oversold bounce. Breaking resistance at 42,300.",
                            "risk_level": "Medium",
                            "trade_id": "TRD_001",
                            "chart_url": "https://tradingview.com/chart/BTCUSDT",
                        }
                    },
                    "expected_outputs": {
                        "success": {
                            "success": True,
                            "telegram_response": {
                                "message_id": 12345,
                                "from": {
                                    "id": 1234567890,
                                    "is_bot": True,
                                    "first_name": "Trading Bot",
                                },
                                "chat": {
                                    "id": -1001234567890,
                                    "type": "supergroup",
                                    "title": "Crypto Trading Signals",
                                },
                                "date": 1705756800,
                                "text": "🚨 **Trading Alert** 🚨...",
                            },
                            "message_id": "12345",
                            "chat_id": "-1001234567890",
                            "execution_metadata": {
                                "action_type": "send_message",
                                "inline_keyboard_sent": True,
                                "message_length": 187,
                                "execution_time_ms": 340,
                            },
                        }
                    },
                },
                {
                    "name": "Send Document Report",
                    "description": "Send document file with caption to Telegram chat",
                    "configurations": {
                        "telegram_bot_token": "1234567890:ABCDefGhIJKlmnOpQrStUvWxYz",
                        "action_type": "send_document",
                        "chat_id": "{{recipient_chat_id}}",
                        "media_config": {
                            "file_path": "{{document_path}}",
                            "caption": "📋 **{{report_title}}**\\n\\n**Generated:** {{generation_date}}\\n**Records:** {{record_count}}\\n**Status:** {{report_status}}\\n\\nPlease review the attached {{report_type}} report.",
                            "supports_streaming": False,
                        },
                        "parse_mode": "Markdown",
                        "message_options": {"disable_notification": False},
                    },
                    "input_example": {
                        "data": {
                            "recipient_chat_id": "123456789",
                            "document_path": "/reports/monthly_sales_2025_01.pdf",
                            "report_title": "Monthly Sales Report - January 2025",
                            "generation_date": "January 20, 2025",
                            "record_count": "2,847",
                            "report_status": "Complete",
                            "report_type": "sales analytics",
                        }
                    },
                    "expected_outputs": {
                        "success": {
                            "success": True,
                            "telegram_response": {
                                "message_id": 67890,
                                "document": {
                                    "file_name": "monthly_sales_2025_01.pdf",
                                    "mime_type": "application/pdf",
                                    "file_id": "BAADBAADrwADBREAAWi8bBG8uUCKFgQ",
                                    "file_size": 524288,
                                },
                                "caption": "📋 **Monthly Sales Report - January 2025**...",
                            },
                            "message_id": "67890",
                            "chat_id": "123456789",
                            "execution_metadata": {
                                "action_type": "send_document",
                                "file_uploaded": True,
                                "file_size_bytes": 524288,
                                "upload_time_ms": 2500,
                                "execution_time_ms": 2750,
                            },
                        }
                    },
                },
                {
                    "name": "Create Poll for Team Decision",
                    "description": "Create interactive poll for team decision making",
                    "configurations": {
                        "telegram_bot_token": "1234567890:ABCDefGhIJKlmnOpQrStUvWxYz",
                        "action_type": "send_poll",
                        "chat_id": "{{team_chat_id}}",
                        "poll_config": {
                            "question": "{{poll_question}}",
                            "options": "{{poll_options}}",
                            "is_anonymous": False,
                            "type": "regular",
                            "allows_multiple_answers": "{{multiple_choice}}",
                        },
                        "message_options": {"disable_notification": False},
                    },
                    "input_example": {
                        "data": {
                            "team_chat_id": "-1001987654321",
                            "poll_question": "Which deployment strategy should we use for the next release?",
                            "poll_options": [
                                "Blue-Green Deployment",
                                "Rolling Deployment",
                                "Canary Deployment",
                                "All-at-once Deployment",
                            ],
                            "multiple_choice": False,
                        }
                    },
                    "expected_outputs": {
                        "success": {
                            "success": True,
                            "telegram_response": {
                                "message_id": 13579,
                                "poll": {
                                    "id": "5432109876543210987",
                                    "question": "Which deployment strategy should we use for the next release?",
                                    "options": [
                                        {"text": "Blue-Green Deployment", "voter_count": 0},
                                        {"text": "Rolling Deployment", "voter_count": 0},
                                        {"text": "Canary Deployment", "voter_count": 0},
                                        {"text": "All-at-once Deployment", "voter_count": 0},
                                    ],
                                    "is_anonymous": False,
                                    "allows_multiple_answers": False,
                                    "type": "regular",
                                },
                            },
                            "message_id": "13579",
                            "chat_id": "-1001987654321",
                            "execution_metadata": {
                                "action_type": "send_poll",
                                "poll_id": "5432109876543210987",
                                "options_count": 4,
                                "is_anonymous": False,
                                "execution_time_ms": 180,
                            },
                        }
                    },
                },
                {
                    "name": "Send Location with Live Tracking",
                    "description": "Share location with live tracking for delivery/service updates",
                    "configurations": {
                        "telegram_bot_token": "1234567890:ABCDefGhIJKlmnOpQrStUvWxYz",
                        "action_type": "send_location",
                        "chat_id": "{{customer_chat_id}}",
                        "location_config": {
                            "latitude": "{{current_latitude}}",
                            "longitude": "{{current_longitude}}",
                            "live_period": 3600,
                        },
                        "message_options": {
                            "disable_notification": False,
                            "reply_to_message_id": "{{order_message_id}}",
                        },
                    },
                    "input_example": {
                        "data": {
                            "customer_chat_id": "987654321",
                            "current_latitude": 40.7589,
                            "current_longitude": -73.9851,
                            "delivery_id": "DEL_2025_001",
                            "order_message_id": "11111",
                            "eta_minutes": 15,
                        }
                    },
                    "expected_outputs": {
                        "success": {
                            "success": True,
                            "telegram_response": {
                                "message_id": 24680,
                                "location": {
                                    "longitude": -73.9851,
                                    "latitude": 40.7589,
                                    "live_period": 3600,
                                },
                                "reply_to_message": {"message_id": 11111},
                            },
                            "message_id": "24680",
                            "chat_id": "987654321",
                            "execution_metadata": {
                                "action_type": "send_location",
                                "live_tracking_enabled": True,
                                "live_period_seconds": 3600,
                                "coordinates": {"latitude": 40.7589, "longitude": -73.9851},
                                "execution_time_ms": 220,
                            },
                        }
                    },
                },
            ],
        )


# Export the specification instance
TELEGRAM_ACTION_SPEC = TelegramActionSpec()
