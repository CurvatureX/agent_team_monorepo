"""
DISCORD_INTERACTION Human-in-the-Loop Node Specification

Discord interaction node for community-based human feedback with built-in AI response analysis.
This HIL node automatically analyzes Discord messages and routes execution based on AI classification.

Note: HIL nodes have built-in AI response analysis and multiple output ports.
Do NOT add separate AI_AGENT or IF nodes for response handling.
"""

from typing import Any, Dict, List

from ...models.node_enums import HumanLoopSubtype, NodeType
from ..base import COMMON_CONFIGS, BaseNodeSpec


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
                "discord_message_id": {
                    "type": "string",
                    "default": "",
                    "description": "Discord message ID of the interaction",
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
