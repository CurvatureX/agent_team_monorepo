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

from shared.models.node_enums import HumanLoopSubtype, NodeType, OpenAIModel
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
                    "default": "{{$placeholder}}",
                    "description": "目标Slack频道或用户（#channel, @user, 或 user_id）",
                    "required": True,
                    "api_endpoint": "/api/proxy/v1/app/integrations/slack/channels",
                },
                "bot_token": {
                    "type": "string",
                    "default": "{{$placeholder}}",
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
                "clarification_question_template": {
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
                "ai_analysis_model": {
                    "type": "string",
                    "default": OpenAIModel.GPT_5_MINI.value,
                    "description": "用于响应分析的AI模型",
                    "required": False,
                    "options": [OpenAIModel.GPT_5_MINI.value, OpenAIModel.GPT_5_NANO.value],
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
            # Examples
            examples=[
                {
                    "name": "Simple Approval Request",
                    "description": "Basic approval workflow with AI response analysis",
                    "configurations": {
                        "channel": "#approvals",
                        "clarification_question_template": "Please approve this expense: ${{amount}} for {{description}}\\n\\nReply 'yes' to approve or 'no' to reject.",
                        "timeout_minutes": 30,
                        "ai_analysis_model": OpenAIModel.GPT_5_MINI.value,
                    },
                    "input_example": {
                        "content": {
                            "type": "expense_approval",
                            "amount": 250,
                            "description": "Office supplies",
                        },
                        "user_mention": "@finance_manager",
                    },
                    "expected_outputs": {
                        "confirmed": {
                            "content": {
                                "type": "expense_approval",
                                "amount": 250,
                                "description": "Office supplies",
                            },
                            "ai_classification": "confirmed",
                            "user_response": "yes, approved for office supplies",
                            "user_id": "U1234567890",
                        }
                    },
                },
                {
                    "name": "Complex Review with Context",
                    "description": "Detailed review request with custom AI analysis",
                    "configurations": {
                        "channel": "@manager_sarah",
                        "clarification_question_template": "Code review required for {{feature_name}}:\\n\\n{{code_summary}}\\n\\nPlease review and respond with your decision and any feedback.",
                        "timeout_minutes": 120,
                        "ai_analysis_model": OpenAIModel.GPT_5_MINI.value,
                        "custom_analysis_prompt": "Analyze if the response indicates code approval, rejection, or requests changes. Look for technical feedback and decision indicators.",
                    },
                    "input_example": {
                        "content": {
                            "type": "code_review",
                            "feature_name": "User Authentication",
                            "code_summary": "Added OAuth 2.0 integration with proper error handling",
                            "pr_url": "https://github.com/org/repo/pull/123",
                        },
                        "user_mention": "@manager_sarah",
                    },
                    "expected_outputs": {
                        "confirmed": {
                            "content": {
                                "type": "code_review",
                                "feature_name": "User Authentication",
                                "code_summary": "Added OAuth 2.0 integration with proper error handling",
                                "pr_url": "https://github.com/org/repo/pull/123",
                            },
                            "ai_classification": "confirmed",
                            "user_response": "Looks good! The OAuth implementation follows best practices. Approved for merge.",
                            "user_id": "U9876543210",
                        }
                    },
                },
                {
                    "name": "Emergency Approval",
                    "description": "High-priority approval with short timeout",
                    "configurations": {
                        "channel": "@oncall_engineer",
                        "clarification_question_template": "🚨 URGENT: Server deployment approval needed for {{service_name}}\\n\\nIssue: {{issue_description}}\\n\\nApprove deployment? (yes/no)",
                        "timeout_minutes": 10,
                        "ai_analysis_model": OpenAIModel.GPT_5_NANO.value,
                    },
                    "input_example": {
                        "content": {
                            "type": "emergency_deployment",
                            "service_name": "API Gateway",
                            "issue_description": "Memory leak causing 500 errors",
                            "severity": "critical",
                            "incident_id": "INC-2025-001",
                        },
                        "user_mention": "@oncall_engineer",
                    },
                    "expected_outputs": {
                        "confirmed": {
                            "content": {
                                "type": "emergency_deployment",
                                "service_name": "API Gateway",
                                "issue_description": "Memory leak causing 500 errors",
                                "severity": "critical",
                                "incident_id": "INC-2025-001",
                            },
                            "ai_classification": "confirmed",
                            "user_response": "yes, deploy immediately",
                            "user_id": "U5555555555",
                        }
                    },
                },
            ],
        )


# Export the specification instance
SLACK_INTERACTION_SPEC = SlackInteractionSpec()
