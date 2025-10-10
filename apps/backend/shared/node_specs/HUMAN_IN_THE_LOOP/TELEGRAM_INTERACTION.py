"""
TELEGRAM_INTERACTION Human-in-the-Loop Node Specification

Telegram interaction node for messaging-based human feedback with built-in AI response analysis.
This HIL node automatically analyzes Telegram messages and routes execution based on AI classification.

Note: HIL nodes have built-in AI response analysis and multiple output ports.
Do NOT add separate AI_AGENT or IF nodes for response handling.
"""

from typing import Any, Dict, List

from shared.models.node_enums import HumanLoopSubtype, NodeType, OpenAIModel
from shared.node_specs.base import COMMON_CONFIGS, BaseNodeSpec


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
                    "default": OpenAIModel.GPT_5_MINI.value,
                    "description": "AI响应分析模型",
                    "required": False,
                    "options": [OpenAIModel.GPT_5_MINI.value, OpenAIModel.GPT_5_NANO.value],
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
                "content": {
                    "type": "object",
                    "default": "",
                    "description": "The content that need to be reviewed",
                    "required": False,
                    "multiline": True,
                },
                "user_mention": {
                    "type": "string",
                    "default": "",
                    "description": "User to mention (e.g., @john)",
                    "required": False,
                },
            },
            output_params={
                "content": {
                    "type": "object",
                    "default": {},
                    "description": "Pass-through content from input_params (unchanged)",
                    "required": False,
                },
                "ai_classification": {
                    "type": "string",
                    "default": "",
                    "description": "AI classification of the response",
                    "required": False,
                    "options": ["confirmed", "rejected", "unrelated", "timeout"],
                },
                "user_response": {
                    "type": "string",
                    "default": "",
                    "description": "The actual text response from the human",
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
                        "content": {
                            "type": "trading_confirmation",
                            "symbol": "AAPL",
                            "action": "BUY",
                            "quantity": "500 shares",
                            "price": "185.50",
                            "risk_level": "Medium",
                            "market_analysis": "Strong bullish momentum with positive earnings outlook. RSI indicates good entry point.",
                            "strategy": "momentum_trading",
                            "portfolio_impact": "2.3%",
                            "stop_loss": "175.00",
                        },
                        "user_mention": "@trader_001 @risk_manager_002",
                    },
                    "expected_outputs": {
                        "confirmed": {
                            "content": {
                                "type": "trading_confirmation",
                                "symbol": "AAPL",
                                "action": "BUY",
                                "quantity": "500 shares",
                                "price": "185.50",
                                "risk_level": "Medium",
                                "market_analysis": "Strong bullish momentum with positive earnings outlook. RSI indicates good entry point.",
                                "strategy": "momentum_trading",
                                "portfolio_impact": "2.3%",
                                "stop_loss": "175.00",
                            },
                            "ai_classification": "confirmed",
                            "user_response": "Execute - Good entry point based on technical analysis. Proceed with the trade.",
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
                        "content": {
                            "type": "maintenance_approval",
                            "system_name": "Production Database Cluster",
                            "maintenance_type": "Security Patch Update",
                            "scheduled_time": "Saturday, January 25, 2025 02:00 AM UTC",
                            "estimated_duration": "2-3 hours",
                            "service_impact": "Brief 5-minute downtime during restart",
                            "maintenance_details": "Applying critical security patches for PostgreSQL 14.10. Rolling update planned with minimal downtime.",
                        },
                        "user_mention": "@ops_team",
                    },
                    "expected_outputs": {
                        "rejected": {
                            "content": {
                                "type": "maintenance_approval",
                                "system_name": "Production Database Cluster",
                                "maintenance_type": "Security Patch Update",
                                "scheduled_time": "Saturday, January 25, 2025 02:00 AM UTC",
                                "estimated_duration": "2-3 hours",
                                "service_impact": "Brief 5-minute downtime during restart",
                                "maintenance_details": "Applying critical security patches for PostgreSQL 14.10. Rolling update planned with minimal downtime.",
                            },
                            "ai_classification": "rejected",
                            "user_response": "REJECT - This conflicts with the weekend product launch. Can we reschedule to Sunday night instead?",
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
                        "content": {
                            "type": "emergency_authorization",
                            "incident_id": "INC-2025-0120-001",
                            "severity_level": "CRITICAL",
                            "affected_systems": "Primary payment processing, User authentication",
                            "impact_assessment": "100% service outage affecting all customers",
                            "proposed_action": "Immediate failover to backup datacenter in us-west-2 region",
                        },
                        "user_mention": "@incident_commander_001",
                    },
                    "expected_outputs": {
                        "timeout": {
                            "content": {
                                "type": "emergency_authorization",
                                "incident_id": "INC-2025-0120-001",
                                "severity_level": "CRITICAL",
                                "affected_systems": "Primary payment processing, User authentication",
                                "impact_assessment": "100% service outage affecting all customers",
                                "proposed_action": "Immediate failover to backup datacenter in us-west-2 region",
                            },
                            "ai_classification": "timeout",
                            "user_response": "",
                        }
                    },
                },
            ],
        )


# Export the specification instance
TELEGRAM_INTERACTION_HIL_SPEC = TelegramInteractionSpec()
