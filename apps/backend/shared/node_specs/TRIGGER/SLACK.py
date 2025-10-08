"""
SLACK Trigger Node Specification

Slack event trigger for workspace events. This trigger has no input ports
and produces execution context when Slack events occur.
"""

from typing import Any, Dict, List

from shared.models.node_enums import NodeType, TriggerSubtype
from shared.node_specs.base import COMMON_CONFIGS, BaseNodeSpec


class SlackTriggerSpec(BaseNodeSpec):
    """Slack trigger specification for workspace events and interactions."""

    def __init__(self):
        super().__init__(
            type=NodeType.TRIGGER,
            subtype=TriggerSubtype.SLACK,
            name="Slack_Trigger",
            description="Slack event trigger for workspace messages and interactions",
            # Configuration parameters
            configurations={
                "workspace_id": {
                    "type": "string",
                    "default": "",
                    "description": "Slack工作区ID",
                    "required": True,
                },
                "events": {
                    "type": "array",
                    "default": ["message", "app_mention"],
                    "description": "监听的Slack事件类型",
                    "required": True,
                    "options": [
                        "message",
                        "app_mention",
                        "reaction_added",
                        "reaction_removed",
                        "channel_created",
                        "channel_deleted",
                        "member_joined_channel",
                        "member_left_channel",
                        "user_change",
                        "team_join",
                        "file_shared",
                    ],
                },
                "channels": {
                    "type": "array",
                    "default": [],
                    "description": "监听的频道列表（空为所有频道）",
                    "required": False,
                    "api_endpoint": "/api/proxy/v1/app/integrations/slack/channels",
                    "multiple": True,
                },
                "keywords": {
                    "type": "array",
                    "default": [],
                    "description": "触发关键词列表",
                    "required": False,
                },
                "bot_token": {
                    "type": "string",
                    "default": "{{$placeholder}}",
                    "description": "Slack Bot Token",
                    "required": True,
                    "sensitive": True,
                },
                **COMMON_CONFIGS,
            },
            # Parameter schemas (preferred over legacy defaults)
            input_params={},  # Triggers have no runtime inputs
            output_params={
                "trigger_time": {
                    "type": "string",
                    "default": "",
                    "description": "ISO-8601 time when the event triggered",
                    "required": False,
                },
                "execution_id": {
                    "type": "string",
                    "default": "",
                    "description": "Execution identifier for correlation",
                    "required": False,
                },
                "event_type": {
                    "type": "string",
                    "default": "",
                    "description": "Slack event type",
                    "required": False,
                    "options": [
                        "message",
                        "app_mention",
                        "reaction_added",
                        "reaction_removed",
                        "channel_created",
                        "channel_deleted",
                        "member_joined_channel",
                        "member_left_channel",
                        "user_change",
                        "team_join",
                        "file_shared",
                    ],
                },
                "channel_id": {
                    "type": "string",
                    "default": "",
                    "description": "Channel ID where the event occurred",
                    "required": False,
                },
                "channel_name": {
                    "type": "string",
                    "default": "",
                    "description": "Channel name where the event occurred",
                    "required": False,
                },
                "user_id": {
                    "type": "string",
                    "default": "",
                    "description": "Slack user ID of the actor",
                    "required": False,
                },
                "user_name": {
                    "type": "string",
                    "default": "",
                    "description": "Slack username of the actor",
                    "required": False,
                },
                "message_text": {
                    "type": "string",
                    "default": "",
                    "description": "Message text for message-based events",
                    "required": False,
                },
                "thread_ts": {
                    "type": "string",
                    "default": "",
                    "description": "Thread timestamp if applicable",
                    "required": False,
                },
                "trigger_message": {
                    "type": "string",
                    "default": "",
                    "description": "Human-friendly trigger message",
                    "required": False,
                },
                "slack_payload": {
                    "type": "object",
                    "default": {},
                    "description": "Raw Slack event payload",
                    "required": False,
                },
            },
            # Examples
            examples=[
                {
                    "name": "Mention Trigger",
                    "description": "Trigger when bot is mentioned in channels",
                    "configurations": {
                        "workspace_id": "T1234567890",
                        "events": ["app_mention"],
                        "channels": ["general", "support"],
                        "bot_token": "xoxb-slack-bot-token-123",
                    },
                    "expected_output": {
                        "trigger_time": "2025-01-20T14:30:00Z",
                        "execution_id": "slack_exec_123",
                        "event_type": "app_mention",
                        "channel_id": "C1234567890",
                        "channel_name": "general",
                        "user_id": "U9876543210",
                        "user_name": "john.doe",
                        "message_text": "<@U0123456789> can you help me with the deployment?",
                        "thread_ts": "",
                        "trigger_message": "Bot mentioned in #general by john.doe",
                        "slack_payload": {
                            "event": {
                                "type": "app_mention",
                                "text": "<@U0123456789> can you help me with the deployment?",
                                "user": "U9876543210",
                                "channel": "C1234567890",
                                "ts": "1642681800.000100",
                            },
                            "team_id": "T1234567890",
                        },
                    },
                },
                {
                    "name": "Keyword Message Trigger",
                    "description": "Trigger on messages containing specific keywords",
                    "configurations": {
                        "workspace_id": "T1234567890",
                        "events": ["message"],
                        "channels": ["alerts", "incidents"],
                        "keywords": ["urgent", "critical", "outage"],
                        "bot_token": "xoxb-slack-bot-token-456",
                    },
                    "expected_output": {
                        "trigger_time": "2025-01-20T16:45:00Z",
                        "execution_id": "slack_exec_456",
                        "event_type": "message",
                        "channel_id": "C2345678901",
                        "channel_name": "alerts",
                        "user_id": "U1111222233",
                        "user_name": "sarah.ops",
                        "message_text": "URGENT: Database connection issues detected",
                        "thread_ts": "",
                        "trigger_message": "Urgent message detected in #alerts by sarah.ops",
                        "slack_payload": {
                            "event": {
                                "type": "message",
                                "text": "URGENT: Database connection issues detected",
                                "user": "U1111222233",
                                "channel": "C2345678901",
                                "ts": "1642689900.000200",
                            }
                        },
                    },
                },
                {
                    "name": "Reaction Trigger",
                    "description": "Trigger when specific reactions are added to messages",
                    "configurations": {
                        "workspace_id": "T1234567890",
                        "events": ["reaction_added"],
                        "channels": ["approvals"],
                        "bot_token": "xoxb-slack-bot-token-789",
                    },
                    "expected_output": {
                        "trigger_time": "2025-01-20T18:15:00Z",
                        "execution_id": "slack_exec_789",
                        "event_type": "reaction_added",
                        "channel_id": "C3456789012",
                        "channel_name": "approvals",
                        "user_id": "U2222333344",
                        "user_name": "manager.alex",
                        "message_text": "",
                        "thread_ts": "",
                        "trigger_message": "Approval reaction ✅ added by manager.alex in #approvals",
                        "slack_payload": {
                            "event": {
                                "type": "reaction_added",
                                "reaction": "white_check_mark",
                                "user": "U2222333344",
                                "item": {
                                    "type": "message",
                                    "channel": "C3456789012",
                                    "ts": "1642697700.000300",
                                },
                            }
                        },
                    },
                },
                {
                    "name": "New Channel Trigger",
                    "description": "Trigger when new channels are created",
                    "configurations": {
                        "workspace_id": "T1234567890",
                        "events": ["channel_created"],
                        "bot_token": "xoxb-slack-bot-token-101",
                    },
                    "expected_output": {
                        "trigger_time": "2025-01-20T20:00:00Z",
                        "execution_id": "slack_exec_101",
                        "event_type": "channel_created",
                        "channel_id": "C4567890123",
                        "channel_name": "project-alpha",
                        "user_id": "U3333444455",
                        "user_name": "lead.developer",
                        "message_text": "",
                        "thread_ts": "",
                        "trigger_message": "New channel #project-alpha created by lead.developer",
                        "slack_payload": {
                            "event": {
                                "type": "channel_created",
                                "channel": {
                                    "id": "C4567890123",
                                    "name": "project-alpha",
                                    "created": 1642705200,
                                    "creator": "U3333444455",
                                },
                            }
                        },
                    },
                },
            ],
        )


# Export the specification instance
SLACK_TRIGGER_SPEC = SlackTriggerSpec()
