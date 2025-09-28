"""
DISCORD_INTERACTION Human-in-the-Loop Node Specification

Discord interaction node for community-based human feedback with built-in AI response analysis.
This HIL node automatically analyzes Discord messages and routes execution based on AI classification.

Note: HIL nodes have built-in AI response analysis and multiple output ports.
Do NOT add separate AI_AGENT or IF nodes for response handling.
"""

from typing import Any, Dict, List

from ...models.node_enums import HumanLoopSubtype, NodeType
from ..base import COMMON_CONFIGS, BaseNodeSpec, create_port


class DiscordInteractionSpec(BaseNodeSpec):
    """Discord interaction specification with built-in AI response analysis."""

    def __init__(self):
        super().__init__(
            type=NodeType.HUMAN_IN_THE_LOOP,
            subtype=HumanLoopSubtype.DISCORD_INTERACTION,
            name="Discord_Interaction",
            description="Discord-based human interaction with AI-powered response analysis and classification",
            # Configuration parameters
            configurations={
                "discord_bot_token": {
                    "type": "string",
                    "default": "",
                    "description": "Discord机器人令牌",
                    "required": True,
                    "sensitive": True,
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
                    "description": "Discord频道ID",
                    "required": True,
                },
                "target_users": {
                    "type": "array",
                    "default": [],
                    "description": "目标用户ID列表（空为所有用户）",
                    "required": False,
                },
                "target_roles": {
                    "type": "array",
                    "default": [],
                    "description": "目标角色ID列表",
                    "required": False,
                },
                "message_template": {
                    "type": "string",
                    "default": "",
                    "description": "Discord消息模板",
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
                    "default": "Analyze this Discord message and classify it as: CONFIRMED (user agrees/approves), REJECTED (user declines/disapproves), or UNRELATED (unclear/off-topic response). Only respond with one word: CONFIRMED, REJECTED, or UNRELATED.",
                    "description": "AI响应分析提示词",
                    "required": False,
                    "multiline": True,
                },
                "reaction_buttons": {
                    "type": "array",
                    "default": ["✅", "❌", "❓"],
                    "description": "反应按钮表情符号",
                    "required": False,
                },
                "enable_thread_responses": {
                    "type": "boolean",
                    "default": True,
                    "description": "是否启用线程回复",
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
            # Default runtime parameters
            default_input_params={"context": {}, "variables": {}, "user_data": {}},
            default_output_params={
                "response_received": False,
                "ai_classification": "",
                "original_response": "",
                "response_timestamp": "",
                "execution_path": "",
                "timeout_occurred": False,
                "discord_message_id": "",
                "responding_user": {},
                "human_feedback": {},
            },
            # Port definitions - HIL nodes have multiple output paths based on AI analysis
            input_ports=[
                create_port(
                    port_id="main",
                    name="main",
                    data_type="dict",
                    description="Input data for human interaction request",
                    required=True,
                    max_connections=1,
                )
            ],
            output_ports=[
                create_port(
                    port_id="confirmed",
                    name="confirmed",
                    data_type="dict",
                    description="Output when AI classifies Discord response as confirmed/approved",
                    required=False,
                    max_connections=-1,
                ),
                create_port(
                    port_id="rejected",
                    name="rejected",
                    data_type="dict",
                    description="Output when AI classifies Discord response as rejected/declined",
                    required=False,
                    max_connections=-1,
                ),
                create_port(
                    port_id="unrelated",
                    name="unrelated",
                    data_type="dict",
                    description="Output when AI classifies Discord response as unclear/unrelated",
                    required=False,
                    max_connections=-1,
                ),
                create_port(
                    port_id="timeout",
                    name="timeout",
                    data_type="dict",
                    description="Output when no response received within timeout period",
                    required=False,
                    max_connections=-1,
                ),
            ],
            # Metadata
            tags=["human-in-the-loop", "discord", "gaming", "community", "approval", "ai-analysis"],
            # Examples
            examples=[
                {
                    "name": "Gaming Tournament Approval",
                    "description": "Request approval from gaming community moderators for tournament setup",
                    "configurations": {
                        "discord_bot_token": "discord_bot_token_123",
                        "server_id": "123456789012345678",
                        "channel_id": "987654321098765432",
                        "target_roles": ["moderator", "admin"],
                        "message_template": "🎮 **Tournament Approval Request** 🎮\\n\\n**Event:** {{tournament_name}}\\n**Date:** {{tournament_date}}\\n**Prize Pool:** ${{prize_amount}}\\n**Expected Participants:** {{participant_count}}\\n\\n**Details:**\\n{{tournament_details}}\\n\\n**Moderators, please react with:**\\n✅ to approve\\n❌ to reject\\n❓ for questions\\n\\n**Or reply with your decision and comments.**",
                        "response_timeout": 7200,
                        "reaction_buttons": ["✅", "❌", "❓"],
                        "enable_thread_responses": True,
                    },
                    "input_example": {
                        "context": {
                            "tournament_name": "Winter Championship 2025",
                            "tournament_date": "February 15-16, 2025",
                            "prize_amount": "5,000",
                            "participant_count": "64 players",
                            "tournament_details": "Two-day esports tournament featuring multiple game modes. Registration opens January 25th.",
                        },
                        "user_data": {
                            "organizer": "TournamentBot#1234",
                            "organizer_role": "event_coordinator",
                        },
                    },
                    "expected_outputs": {
                        "confirmed": {
                            "response_received": True,
                            "ai_classification": "CONFIRMED",
                            "original_response": "✅ Approved! This tournament looks well-organized. Make sure to coordinate with @EventTeam for venue setup. Good luck!",
                            "response_timestamp": "2025-01-20T14:30:00Z",
                            "execution_path": "confirmed",
                            "discord_message_id": "1234567890123456789",
                            "responding_user": {
                                "id": "user_mod_456",
                                "username": "ModeratorSarah",
                                "discriminator": "7890",
                                "roles": ["moderator"],
                            },
                            "human_feedback": {
                                "decision": "approved",
                                "comments": "This tournament looks well-organized. Make sure to coordinate with @EventTeam for venue setup. Good luck!",
                                "response_method": "text_reply",
                                "response_time_minutes": 25,
                            },
                        }
                    },
                },
                {
                    "name": "Server Rule Change Vote",
                    "description": "Community vote on server rule changes with reaction-based responses",
                    "configurations": {
                        "discord_bot_token": "discord_bot_token_456",
                        "server_id": "123456789012345678",
                        "channel_id": "announcements_channel_123",
                        "message_template": "📋 **Server Rule Update Proposal** 📋\\n\\n**Proposed Change:** {{rule_change}}\\n**Reason:** {{change_reason}}\\n**Effective Date:** {{effective_date}}\\n\\n**Community members, please vote:**\\n✅ **Support** this rule change\\n❌ **Oppose** this rule change\\n\\n**Voting closes in {{voting_duration}} hours.**",
                        "response_timeout": 86400,
                        "reaction_buttons": ["✅", "❌"],
                        "enable_thread_responses": False,
                        "target_roles": ["verified_member", "supporter", "moderator"],
                    },
                    "input_example": {
                        "context": {
                            "rule_change": "No NSFW content in general channels",
                            "change_reason": "To maintain a welcoming environment for all ages",
                            "effective_date": "February 1, 2025",
                            "voting_duration": "24",
                        }
                    },
                    "expected_outputs": {
                        "confirmed": {
                            "response_received": True,
                            "ai_classification": "CONFIRMED",
                            "original_response": "✅",
                            "response_timestamp": "2025-01-20T18:45:00Z",
                            "execution_path": "confirmed",
                            "discord_message_id": "9876543210987654321",
                            "responding_user": {
                                "id": "user_community_789",
                                "username": "CommunityVoice",
                                "discriminator": "1357",
                                "roles": ["verified_member"],
                            },
                            "human_feedback": {
                                "decision": "approved",
                                "response_method": "reaction",
                                "reaction_emoji": "✅",
                            },
                        }
                    },
                },
                {
                    "name": "Bot Feature Request Review",
                    "description": "Review bot feature requests from community with timeout handling",
                    "configurations": {
                        "discord_bot_token": "discord_bot_token_789",
                        "server_id": "123456789012345678",
                        "channel_id": "bot_requests_456",
                        "target_users": ["dev_lead_001", "bot_maintainer_002"],
                        "message_template": "🤖 **Bot Feature Request Review** 🤖\\n\\n**Feature:** {{feature_name}}\\n**Description:** {{feature_description}}\\n**Requested by:** <@{{requester_id}}>\\n**Priority:** {{priority_level}}\\n\\n**Development Team:**\\n<@dev_lead_001> <@bot_maintainer_002>\\n\\nPlease review this request and provide your decision.\\n\\n**Commands:**\\n• Type `APPROVE` to approve\\n• Type `REJECT` to reject\\n• Type `DISCUSS` for further discussion",
                        "response_timeout": 259200,
                        "require_specific_response": True,
                        "allowed_response_patterns": ["^(APPROVE|REJECT|DISCUSS).*$"],
                    },
                    "input_example": {
                        "context": {
                            "feature_name": "Automated Backup System",
                            "feature_description": "Daily automatic backup of server settings and user data",
                            "requester_id": "user_requester_101",
                            "priority_level": "Medium",
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
                            "discord_message_id": "5678901234567890123",
                            "human_feedback": {
                                "timeout_reason": "no_response_from_development_team",
                                "escalation_required": True,
                                "awaiting_users": ["dev_lead_001", "bot_maintainer_002"],
                            },
                        }
                    },
                },
            ],
        )


# Export the specification instance
DISCORD_INTERACTION_HIL_SPEC = DiscordInteractionSpec()
