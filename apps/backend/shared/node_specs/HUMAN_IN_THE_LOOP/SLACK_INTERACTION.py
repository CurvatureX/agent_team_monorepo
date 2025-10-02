"""
SLACK_INTERACTION Human-in-the-Loop Node Specification

Human-in-the-loop node for Slack interactions with built-in AI response analysis.
This node has integrated AI-powered response analysis capabilities that automatically
classify user responses as confirmed/rejected/unrelated, eliminating the need for
separate AI_AGENT or FLOW (IF) nodes for response handling.

Key Features:
- Sends messages to Slack channels or users
- Waits for human responses
- Built-in AI analysis of responses (confirmed/rejected/unrelated/timeout)
- Multiple output ports based on AI classification
- Automatic response messaging based on classification results
"""

from typing import Any, Dict, List

from shared.models.node_enums import HumanLoopSubtype, NodeType
from shared.node_specs.base import COMMON_CONFIGS, BaseNodeSpec


class SlackInteractionSpec(BaseNodeSpec):
    """Slack interaction HIL specification with built-in AI response analysis."""

    def __init__(self):
        super().__init__(
            type=NodeType.HUMAN_IN_THE_LOOP,
            subtype=HumanLoopSubtype.SLACK_INTERACTION,
            name="Slack_Interaction",
            description="Human-in-the-loop Slack interaction with built-in AI response analysis",
            # Configuration parameters
            configurations={
                "channel": {
                    "type": "string",
                    "default": "#general",
                    "description": "目标Slack频道或用户（#channel, @user, 或 user_id）",
                    "required": True,
                },
                "bot_token": {
                    "type": "string",
                    "default": "",
                    "description": "Slack Bot Token (xoxb-...)",
                    "required": True,
                    "sensitive": True,
                },
                "message_template": {
                    "type": "string",
                    "default": "Please review: {{content}}\\n\\nRespond with 'yes' to approve or 'no' to reject.",
                    "description": "发送给用户的消息模板，支持变量替换",
                    "required": True,
                    "multiline": True,
                },
                "timeout_minutes": {
                    "type": "integer",
                    "default": 60,
                    "min": 1,
                    "max": 1440,
                    "description": "等待响应的超时时间（分钟）",
                    "required": False,
                },
                "auto_thread": {
                    "type": "boolean",
                    "default": True,
                    "description": "自动在thread中收集响应",
                    "required": False,
                },
                "require_reaction": {
                    "type": "boolean",
                    "default": False,
                    "description": "是否接受emoji反应作为响应",
                    "required": False,
                },
                "ai_analysis_model": {
                    "type": "string",
                    "default": "gpt-4",
                    "description": "用于响应分析的AI模型",
                    "required": False,
                    "options": ["gpt-4", "gpt-3.5-turbo", "claude-3-haiku", "claude-3-sonnet"],
                },
                "custom_analysis_prompt": {
                    "type": "string",
                    "default": "",
                    "description": "自定义AI分析提示（可选，为空时使用默认分析）",
                    "required": False,
                    "multiline": True,
                },
                **COMMON_CONFIGS,
            },
            # Parameter schemas (preferred over legacy defaults)
            input_params={
                "content": {
                    "type": "string",
                    "default": "",
                    "description": "Content to include in the Slack message",
                    "required": False,
                    "multiline": True,
                },
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
                "user_mention": {
                    "type": "string",
                    "default": "",
                    "description": "User to mention (e.g., @john)",
                    "required": False,
                },
                "urgency": {
                    "type": "string",
                    "default": "normal",
                    "description": "Urgency level for the request",
                    "required": False,
                    "options": ["low", "normal", "high"],
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
                "timeout_occurred": {
                    "type": "boolean",
                    "default": False,
                    "description": "Whether the interaction timed out",
                    "required": False,
                },
                "human_feedback": {
                    "type": "object",
                    "default": {},
                    "description": "Structured feedback extracted from the response",
                    "required": False,
                },
                "user_id": {
                    "type": "string",
                    "default": "",
                    "description": "Slack user ID of the responder",
                    "required": False,
                },
            },
            # Port definitions - HIL nodes have multiple output ports based on AI analysis            # Metadata
            tags=["human-interaction", "slack", "approval", "ai-analysis", "built-in-intelligence"],
            # Examples
            examples=[
                {
                    "name": "Simple Approval Request",
                    "description": "Basic approval workflow with AI response analysis",
                    "configurations": {
                        "channel": "#approvals",
                        "message_template": "Please approve this expense: ${{amount}} for {{description}}\\n\\nReply 'yes' to approve or 'no' to reject.",
                        "timeout_minutes": 30,
                        "ai_analysis_model": "gpt-4",
                    },
                    "input_example": {
                        "content": "Expense approval needed",
                        "variables": {"amount": "250", "description": "Office supplies"},
                        "urgency": "normal",
                    },
                    "expected_outputs": {
                        "confirmed": {
                            "user_response": "yes, approved for office supplies",
                            "analysis_result": "confirmed",
                            "confidence": 0.95,
                            "response_time": 300,
                            "user_id": "U1234567890",
                        }
                    },
                },
                {
                    "name": "Complex Review with Context",
                    "description": "Detailed review request with custom AI analysis",
                    "configurations": {
                        "channel": "@manager_sarah",
                        "message_template": "Code review required for {{feature_name}}:\\n\\n{{code_summary}}\\n\\nPlease review and respond with your decision and any feedback.",
                        "timeout_minutes": 120,
                        "custom_analysis_prompt": "Analyze if the response indicates code approval, rejection, or requests changes. Look for technical feedback and decision indicators.",
                    },
                    "input_example": {
                        "content": "Code review needed",
                        "variables": {
                            "feature_name": "User Authentication",
                            "code_summary": "Added OAuth 2.0 integration with proper error handling",
                        },
                    },
                    "expected_outputs": {
                        "confirmed": {
                            "user_response": "Looks good! The OAuth implementation follows best practices. Approved for merge.",
                            "analysis_result": "confirmed",
                            "confidence": 0.92,
                            "response_time": 1800,
                            "user_id": "U9876543210",
                        }
                    },
                },
                {
                    "name": "Emergency Approval",
                    "description": "High-priority approval with short timeout",
                    "configurations": {
                        "channel": "@oncall_engineer",
                        "message_template": "🚨 URGENT: Server deployment approval needed for {{service_name}}\\n\\nIssue: {{issue_description}}\\n\\nApprove deployment? (yes/no)",
                        "timeout_minutes": 10,
                        "require_reaction": True,
                    },
                    "input_example": {
                        "content": "Emergency deployment approval",
                        "variables": {
                            "service_name": "API Gateway",
                            "issue_description": "Memory leak causing 500 errors",
                        },
                        "urgency": "high",
                    },
                    "expected_outputs": {
                        "confirmed": {
                            "user_response": "✅ (thumbs up reaction)",
                            "analysis_result": "confirmed",
                            "confidence": 1.0,
                            "response_time": 45,
                            "user_id": "U5555555555",
                        }
                    },
                },
            ],
        )


# Export the specification instance
SLACK_INTERACTION_SPEC = SlackInteractionSpec()
