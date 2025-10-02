"""
TELEGRAM_INTERACTION Human-in-the-Loop Node Specification

Telegram interaction node for messaging-based human feedback with built-in AI response analysis.
This HIL node automatically analyzes Telegram messages and routes execution based on AI classification.

Note: HIL nodes have built-in AI response analysis and multiple output ports.
Do NOT add separate AI_AGENT or IF nodes for response handling.
"""

from typing import Any, Dict, List

from ...models.node_enums import HumanLoopSubtype, NodeType
from ..base import COMMON_CONFIGS, BaseNodeSpec


class TelegramInteractionSpec(BaseNodeSpec):
    """Telegram interaction specification with built-in AI response analysis."""

    def __init__(self):
        super().__init__(
            type=NodeType.HUMAN_IN_THE_LOOP,
            subtype=HumanLoopSubtype.TELEGRAM_INTERACTION,
            name="Telegram_Interaction",
            description="Telegram-based human interaction with AI-powered response analysis and classification",
            # Configuration parameters
            configurations={
                "telegram_bot_token": {
                    "type": "string",
                    "default": "",
                    "description": "Telegram机器人令牌",
                    "required": True,
                    "sensitive": True,
                },
                "chat_id": {
                    "type": "string",
                    "default": "",
                    "description": "目标聊天ID",
                    "required": True,
                },
                "target_users": {
                    "type": "array",
                    "default": [],
                    "description": "目标用户ID列表（空为所有用户）",
                    "required": False,
                },
                "message_template": {
                    "type": "string",
                    "default": "",
                    "description": "Telegram消息模板",
                    "required": True,
                    "multiline": True,
                },
                "response_timeout": {
                    "type": "integer",
                    "default": 3600,
                    "min": 60,
                    "max": 604800,
                    "description": "响应超时时间（秒）",
                    "required": False,
                },
                "ai_analysis_model": {
                    "type": "string",
                    "default": "claude-3-5-haiku-20241022",
                    "description": "AI响应分析模型",
                    "required": False,
                    "options": [
                        "gpt-4",
                        "gpt-3.5-turbo",
                        "claude-3-5-haiku-20241022",
                        "claude-sonnet-4-20250514",
                    ],
                },
                "response_analysis_prompt": {
                    "type": "string",
                    "default": "Analyze this Telegram message and classify it as: CONFIRMED (user agrees/approves), REJECTED (user declines/disapproves), or UNRELATED (unclear/off-topic response). Only respond with one word: CONFIRMED, REJECTED, or UNRELATED.",
                    "description": "AI响应分析提示词",
                    "required": False,
                    "multiline": True,
                },
                "inline_keyboard": {
                    "type": "array",
                    "default": [
                        [{"text": "✅ Approve", "callback_data": "approve"}],
                        [{"text": "❌ Reject", "callback_data": "reject"}],
                        [{"text": "❓ Need More Info", "callback_data": "info"}],
                    ],
                    "description": "内联键盘按钮配置",
                    "required": False,
                },
                "enable_reply_keyboard": {
                    "type": "boolean",
                    "default": False,
                    "description": "是否启用回复键盘",
                    "required": False,
                },
                "reply_keyboard_buttons": {
                    "type": "array",
                    "default": ["Approve", "Reject", "Cancel"],
                    "description": "回复键盘按钮列表",
                    "required": False,
                },
                "allow_text_responses": {
                    "type": "boolean",
                    "default": True,
                    "description": "是否允许文本回复",
                    "required": False,
                },
                "require_specific_response": {
                    "type": "boolean",
                    "default": False,
                    "description": "是否要求特定响应格式",
                    "required": False,
                },
                "allowed_response_patterns": {
                    "type": "array",
                    "default": [],
                    "description": "允许的响应模式（正则表达式）",
                    "required": False,
                },
                "parse_mode": {
                    "type": "string",
                    "default": "Markdown",
                    "description": "消息解析模式",
                    "required": False,
                    "options": ["Markdown", "HTML", "MarkdownV2"],
                },
                "disable_notification": {
                    "type": "boolean",
                    "default": False,
                    "description": "是否禁用通知",
                    "required": False,
                },
                "confirmation_messages": {
                    "type": "object",
                    "default": {
                        "confirmed": "✅ **Confirmed** - Your approval has been recorded. Thank you!",
                        "rejected": "❌ **Rejected** - Your decision has been noted. Thank you!",
                        "unrelated": "❓ **Unclear Response** - Please provide a clear approval or rejection.",
                        "timeout": "⏰ **Timeout** - No response received within the specified timeframe.",
                    },
                    "description": "不同分类的确认消息",
                    "required": False,
                },
                **COMMON_CONFIGS,
            },
            # Parameter schemas (preferred over legacy defaults)
            input_params={
                "context": {
                    "type": "object",
                    "default": {},
                    "description": "Additional context for templating",
                    "required": False,
                },
                "variables": {
                    "type": "object",
                    "default": {},
                    "description": "Template variables",
                    "required": False,
                },
                "user_data": {
                    "type": "object",
                    "default": {},
                    "description": "Arbitrary user data to include",
                    "required": False,
                },
            },
            output_params={
                "response_received": {
                    "type": "boolean",
                    "default": False,
                    "description": "Whether a response was received",
                    "required": False,
                },
                "ai_classification": {
                    "type": "string",
                    "default": "",
                    "description": "AI classification of the response",
                    "required": False,
                    "options": ["confirmed", "rejected", "unrelated", "timeout"],
                },
                "original_response": {
                    "type": "string",
                    "default": "",
                    "description": "Original user response text",
                    "required": False,
                },
                "response_timestamp": {
                    "type": "string",
                    "default": "",
                    "description": "ISO-8601 timestamp when response received",
                    "required": False,
                },
                "execution_path": {
                    "type": "string",
                    "default": "",
                    "description": "Downstream execution path determined",
                    "required": False,
                },
                "timeout_occurred": {
                    "type": "boolean",
                    "default": False,
                    "description": "Whether the interaction timed out",
                    "required": False,
                },
                "telegram_message_id": {
                    "type": "string",
                    "default": "",
                    "description": "Telegram message ID of the interaction",
                    "required": False,
                },
                "responding_user": {
                    "type": "object",
                    "default": {},
                    "description": "Information about the responder",
                    "required": False,
                },
                "human_feedback": {
                    "type": "object",
                    "default": {},
                    "description": "Structured feedback extracted from the response",
                    "required": False,
                },
            },
            # Port definitions - HIL nodes have multiple output paths based on AI analysis            # Metadata
            tags=["human-in-the-loop", "telegram", "messaging", "approval", "ai-analysis", "bot"],
            # Examples
            examples=[
                {
                    "name": "Trading Alert Confirmation",
                    "description": "Request trading decision confirmation from financial team via Telegram",
                    "configurations": {
                        "telegram_bot_token": "1234567890:ABCDefGhIJKlmnOpQrStUvWxYz",
                        "chat_id": "-1001234567890",
                        "target_users": ["trader_001", "risk_manager_002"],
                        "message_template": "📊 **Trading Alert Confirmation**\\n\\n**Symbol:** {{symbol}}\\n**Action:** {{action}}\\n**Quantity:** {{quantity}}\\n**Price:** ${{price}}\\n**Risk Level:** {{risk_level}}\\n\\n**Market Analysis:**\\n{{market_analysis}}\\n\\n**Please confirm this trade:**",
                        "response_timeout": 1800,
                        "inline_keyboard": [
                            [{"text": "✅ Execute Trade", "callback_data": "execute"}],
                            [{"text": "❌ Cancel Trade", "callback_data": "cancel"}],
                            [{"text": "📊 Need Analysis", "callback_data": "analysis"}],
                        ],
                        "parse_mode": "Markdown",
                        "disable_notification": False,
                    },
                    "input_example": {
                        "context": {
                            "symbol": "AAPL",
                            "action": "BUY",
                            "quantity": "500 shares",
                            "price": "185.50",
                            "risk_level": "Medium",
                            "market_analysis": "Strong bullish momentum with positive earnings outlook. RSI indicates good entry point.",
                        },
                        "user_data": {
                            "strategy": "momentum_trading",
                            "portfolio_impact": "2.3%",
                            "stop_loss": "175.00",
                        },
                    },
                    "expected_outputs": {
                        "confirmed": {
                            "response_received": True,
                            "ai_classification": "CONFIRMED",
                            "original_response": "Execute - Good entry point based on technical analysis. Proceed with the trade.",
                            "response_timestamp": "2025-01-20T14:30:00Z",
                            "execution_path": "confirmed",
                            "telegram_message_id": "12345",
                            "responding_user": {
                                "id": "trader_001",
                                "username": "lead_trader_mike",
                                "first_name": "Mike",
                                "last_name": "Johnson",
                            },
                            "human_feedback": {
                                "decision": "approved",
                                "comments": "Good entry point based on technical analysis. Proceed with the trade.",
                                "response_method": "inline_button",
                                "callback_data": "execute",
                                "response_time_minutes": 5.2,
                            },
                        }
                    },
                },
                {
                    "name": "System Maintenance Approval",
                    "description": "IT maintenance window approval via Telegram with text responses",
                    "configurations": {
                        "telegram_bot_token": "1234567890:ABCDefGhIJKlmnOpQrStUvWxYz",
                        "chat_id": "it_operations_chat",
                        "message_template": "🔧 **Maintenance Window Approval Required**\\n\\n**System:** {{system_name}}\\n**Maintenance Type:** {{maintenance_type}}\\n**Scheduled Time:** {{scheduled_time}}\\n**Duration:** {{estimated_duration}}\\n**Impact:** {{service_impact}}\\n\\n**Details:**\\n{{maintenance_details}}\\n\\n**Ops Team, please respond with APPROVE or REJECT**",
                        "response_timeout": 7200,
                        "allow_text_responses": True,
                        "require_specific_response": True,
                        "allowed_response_patterns": ["^(APPROVE|REJECT|APPROVED|REJECTED).*$"],
                        "parse_mode": "Markdown",
                    },
                    "input_example": {
                        "context": {
                            "system_name": "Production Database Cluster",
                            "maintenance_type": "Security Patch Update",
                            "scheduled_time": "Saturday, January 25, 2025 02:00 AM UTC",
                            "estimated_duration": "2-3 hours",
                            "service_impact": "Brief 5-minute downtime during restart",
                            "maintenance_details": "Applying critical security patches for PostgreSQL 14.10. Rolling update planned with minimal downtime.",
                        }
                    },
                    "expected_outputs": {
                        "rejected": {
                            "response_received": True,
                            "ai_classification": "REJECTED",
                            "original_response": "REJECT - This conflicts with the weekend product launch. Can we reschedule to Sunday night instead?",
                            "response_timestamp": "2025-01-20T16:45:00Z",
                            "execution_path": "rejected",
                            "telegram_message_id": "67890",
                            "responding_user": {
                                "id": "ops_lead_003",
                                "username": "ops_sarah",
                                "first_name": "Sarah",
                                "last_name": "Chen",
                            },
                            "human_feedback": {
                                "decision": "rejected",
                                "comments": "This conflicts with the weekend product launch. Can we reschedule to Sunday night instead?",
                                "response_method": "text_message",
                                "conflict_reason": "product_launch_weekend",
                                "suggested_alternative": "Sunday_night",
                            },
                        }
                    },
                },
                {
                    "name": "Emergency Response Authorization",
                    "description": "Critical emergency response approval with timeout escalation",
                    "configurations": {
                        "telegram_bot_token": "1234567890:ABCDefGhIJKlmnOpQrStUvWxYz",
                        "chat_id": "emergency_response_team",
                        "target_users": ["incident_commander_001"],
                        "message_template": "🚨 **EMERGENCY RESPONSE AUTHORIZATION REQUIRED** 🚨\\n\\n**Incident ID:** {{incident_id}}\\n**Severity:** {{severity_level}}\\n**Affected Systems:** {{affected_systems}}\\n**Estimated Impact:** {{impact_assessment}}\\n\\n**Proposed Action:**\\n{{proposed_action}}\\n\\n**⚠️ URGENT: Response needed within 10 minutes**",
                        "response_timeout": 600,
                        "inline_keyboard": [
                            [
                                {
                                    "text": "🚨 AUTHORIZE EMERGENCY RESPONSE",
                                    "callback_data": "authorize",
                                }
                            ],
                            [{"text": "⏸️ HOLD - Need More Info", "callback_data": "hold"}],
                            [{"text": "❌ REJECT - Find Alternative", "callback_data": "reject"}],
                        ],
                        "parse_mode": "Markdown",
                        "disable_notification": False,
                    },
                    "input_example": {
                        "context": {
                            "incident_id": "INC-2025-0120-001",
                            "severity_level": "CRITICAL",
                            "affected_systems": "Primary payment processing, User authentication",
                            "impact_assessment": "100% service outage affecting all customers",
                            "proposed_action": "Immediate failover to backup datacenter in us-west-2 region",
                        }
                    },
                    "expected_outputs": {
                        "timeout": {
                            "response_received": False,
                            "ai_classification": "",
                            "original_response": "",
                            "response_timestamp": "",
                            "execution_path": "timeout",
                            "timeout_occurred": True,
                            "human_feedback": {
                                "timeout_reason": "no_response_from_incident_commander",
                                "escalation_required": True,
                                "escalation_recipients": ["cto_emergency", "vp_engineering"],
                                "automatic_action": "proceed_with_emergency_protocol",
                                "severity_impact": "critical_service_outage",
                            },
                        }
                    },
                },
            ],
        )


# Export the specification instance
TELEGRAM_INTERACTION_HIL_SPEC = TelegramInteractionSpec()
