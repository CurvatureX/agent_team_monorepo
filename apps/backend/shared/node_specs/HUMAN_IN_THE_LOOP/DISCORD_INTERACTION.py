"""
DISCORD_INTERACTION Human-in-the-Loop Node Specification

Discord interaction node for community-based human feedback with built-in AI response analysis.
This HIL node automatically analyzes Discord messages and routes execution based on AI classification.

Note: HIL nodes have built-in AI response analysis and multiple output ports.
Do NOT add separate AI_AGENT or IF nodes for response handling.
"""

from typing import Any, Dict, List

from shared.models.node_enums import HumanLoopSubtype, NodeType, OpenAIModel
from shared.node_specs.base import COMMON_CONFIGS, BaseNodeSpec


class DiscordInteractionSpec(BaseNodeSpec):
    """Discord interaction specification with built-in AI response analysis."""

    def __init__(self):
        super().__init__(
            type=NodeType.HUMAN_IN_THE_LOOP,
            subtype=HumanLoopSubtype.DISCORD_INTERACTION,
            name="Discord_Interaction",
            description="Discord-based human interaction with AI-powered response analysis and classification",
            # Configuration parameters (simplified)
            configurations={
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
                    "default": OpenAIModel.GPT_5_MINI.value,
                    "description": "AI响应分析模型",
                    "required": False,
                    "options": [OpenAIModel.GPT_5_MINI.value, OpenAIModel.GPT_5_NANO.value],
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
                        "message_template": "🎮 **Tournament Approval Request** 🎮\\n\\n**Event:** {{tournament_name}}\\n**Date:** {{tournament_date}}\\n**Prize Pool:** ${{prize_amount}}\\n**Expected Participants:** {{participant_count}}\\n\\n**Details:**\\n{{tournament_details}}\\n\\nPlease reply with ✅ to approve or ❌ to reject.",
                        "response_timeout": 7200,
                    },
                    "input_example": {
                        "content": {
                            "type": "tournament_approval",
                            "tournament_name": "Winter Championship 2025",
                            "tournament_date": "February 15-16, 2025",
                            "prize_amount": "5,000",
                            "participant_count": "64 players",
                            "tournament_details": "Two-day esports tournament featuring multiple game modes. Registration opens January 25th.",
                            "organizer": "TournamentBot#1234",
                            "organizer_role": "event_coordinator",
                        },
                        "user_mention": "@EventMod",
                    },
                    "expected_outputs": {
                        "confirmed": {
                            "content": {
                                "type": "tournament_approval",
                                "tournament_name": "Winter Championship 2025",
                                "tournament_date": "February 15-16, 2025",
                                "prize_amount": "5,000",
                                "participant_count": "64 players",
                                "tournament_details": "Two-day esports tournament featuring multiple game modes. Registration opens January 25th.",
                                "organizer": "TournamentBot#1234",
                                "organizer_role": "event_coordinator",
                            },
                            "ai_classification": "confirmed",
                            "user_response": "✅ Approved! This tournament looks well-organized. Make sure to coordinate with @EventTeam for venue setup. Good luck!",
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
                        "content": {
                            "type": "rule_vote",
                            "rule_change": "No NSFW content in general channels",
                            "change_reason": "To maintain a welcoming environment for all ages",
                            "effective_date": "February 1, 2025",
                            "voting_duration": "24",
                        },
                        "user_mention": "@everyone",
                    },
                    "expected_outputs": {
                        "confirmed": {
                            "content": {
                                "type": "rule_vote",
                                "rule_change": "No NSFW content in general channels",
                                "change_reason": "To maintain a welcoming environment for all ages",
                                "effective_date": "February 1, 2025",
                                "voting_duration": "24",
                            },
                            "ai_classification": "confirmed",
                            "user_response": "✅",
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
                        "content": {
                            "type": "feature_request",
                            "feature_name": "Automated Backup System",
                            "feature_description": "Daily automatic backup of server settings and user data",
                            "requester_id": "user_requester_101",
                            "priority_level": "Medium",
                        },
                        "user_mention": "<@dev_lead_001> <@bot_maintainer_002>",
                    },
                    "expected_outputs": {
                        "timeout": {
                            "content": {
                                "type": "feature_request",
                                "feature_name": "Automated Backup System",
                                "feature_description": "Daily automatic backup of server settings and user data",
                                "requester_id": "user_requester_101",
                                "priority_level": "Medium",
                            },
                            "ai_classification": "timeout",
                            "user_response": "",
                        }
                    },
                },
            ],
        )


# Export the specification instance
DISCORD_INTERACTION_HIL_SPEC = DiscordInteractionSpec()
